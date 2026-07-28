"""File-related classes and functions."""

import csv
import io
import os
from array import array
from itertools import islice
from typing import Iterator, List, Union, IO, Dict, Optional

from dwca.descriptors import DataFileDescriptor
from dwca.rows import CoreRow, ExtensionRow, Row


class CSVDataFile(object):
    """Object used to access a DwCA-enclosed CSV data file.

    :param work_directory: absolute path to the target directory (archive content, previously\
    extracted if necessary).
    :param file_descriptor: an instance of :class:`dwca.descriptors.DataFileDescriptor`\
    describing the data file.

    The file content can be accessed:

    * By iterating on this object: a str is returned, including separators.
    * With :meth:`get_row_by_position` (A :class:`dwca.rows.CoreRow` or :class:`dwca.rows.ExtensionRow` object is \
    returned)
    * For an extension data file, with :meth:`get_all_rows_by_coreid` (A :class:`dwca.rows.CoreRow` or \
    :class:`dwca.rows.ExtensionRow` object is returned)

    On initialization, an index of new lines is build. This may take time, but makes random access\
    faster.
    """

    # TODO: More tests for this class
    def __init__(
        self, work_directory: str, file_descriptor: DataFileDescriptor
    ) -> None:
        """Initialize the CSVDataFile object."""
        #: An instance of :class:`dwca.descriptors.DataFileDescriptor`, as given to the
        #: constructor.
        self.file_descriptor = file_descriptor  # type: DataFileDescriptor

        self._file_path = os.path.join(
            work_directory, self.file_descriptor.file_location
        )
        self._file_stream = self._open_stream(
            newline=self.file_descriptor.lines_terminated_by
        )

        # On init, we parse the file once to build an index of newlines (including lines to ignore)
        # that will make random access faster later on...
        self._line_offsets = _get_all_line_offsets(
            self._file_stream, self.file_descriptor.file_encoding
        )

        #: Number of lines to ignore (header lines) in the CSV file.
        self.lines_to_ignore = self.file_descriptor.lines_to_ignore  # type: int

        self._coreid_index = None  # type: Optional[Dict[str, List[int]]]

    def __str__(self) -> str:
        return self.file_descriptor.file_location

    def _open_stream(self, newline: str) -> IO:
        return io.open(
            self._file_path,
            mode="r",
            encoding=self.file_descriptor.file_encoding,
            newline=newline,
            errors="replace",
        )

    def _iter_field_lists(self) -> Iterator[List[str]]:
        """Yield each data row of the file as a list of raw field values.

        Header lines are skipped. This is a single forward pass over a dedicated stream, so
        it is safe to run several of these concurrently and alongside random access.
        """
        descriptor = self.file_descriptor
        quoted = descriptor.fields_enclosed_by != ""

        # The csv module refuses a stream that can hand it an embedded carriage return, so
        # the quoted path has to let Python handle newlines. The unquoted path keeps the
        # archive's own terminator, which is what stops U+0085 from being treated as a line
        # break (issue #20).
        stream = self._open_stream(
            newline="" if quoted else descriptor.lines_terminated_by
        )
        try:
            if quoted:
                source = csv.reader(
                    stream,
                    delimiter=descriptor.fields_terminated_by,
                    quotechar=descriptor.fields_enclosed_by,
                    quoting=csv.QUOTE_MINIMAL,
                )  # type: Iterator[List[str]]
            else:
                line_ending = descriptor.lines_terminated_by
                separator = descriptor.fields_terminated_by
                source = (line.rstrip(line_ending).split(separator) for line in stream)

            for fields in islice(source, self.lines_to_ignore, None):
                yield fields
        finally:
            stream.close()

    def iter_rows(self) -> Iterator[Union[CoreRow, ExtensionRow]]:
        """Yield every data row of the file, in order of appearance.

        Unlike repeated :meth:`get_row_by_position` calls this is a single forward pass and
        never touches the line offset index.
        """
        descriptor = self.file_descriptor
        row_class = CoreRow if descriptor.represents_corefile else ExtensionRow

        for position, fields in enumerate(self._iter_field_lists()):
            yield row_class.from_fields(fields, position, descriptor)

    def _position_file_after_header(self) -> None:
        self._file_stream.seek(0, 0)
        # NOTE: readlines() takes a byte-size hint, not a line count, so it cannot be used
        # here. With ignoreHeaderLines="2" it would read a single line.
        for _ in range(self.lines_to_ignore):
            self._file_stream.readline()

    def __iter__(self) -> "CSVDataFile":
        self._position_file_after_header()
        return self

    def __next__(self) -> str:
        return self.next()

    def next(self) -> str:  # NOQA
        for line in self._file_stream:
            return line

        raise StopIteration

    @property
    def coreid_index(self) -> Dict[str, array]:
        """An index of the core rows referenced by this data file.

        It is a Python dict such as:
        ::

            {
            core_id1: [1],    # Row at position 1 references a Core Row whose ID is core_id1
            core_id2: [8, 10] # Rows at position 8 and 10 references a Core Row whose ID is core_id2
            }

        .. warning::

            for performance reasons, dictionary values are arrays('L') instead of regular python lists

        .. warning::

            Creating this index can be time and memory consuming for large archives, so it's created on the fly
            at first access.
        """
        if self._coreid_index is None:
            self._coreid_index = self._build_coreid_index()

        return self._coreid_index

    def _build_coreid_index(self) -> Dict[str, List[int]]:
        """Build and return an index of Core Rows IDs suitable for `CSVDataFile.coreid_index`."""
        index = {}  # type: Dict[str, array[int]]

        represents_corefile = self.file_descriptor.represents_corefile
        for row in self.iter_rows():
            key = row.id if represents_corefile else row.core_id
            index.setdefault(key, array("L")).append(row.position)

        return index

    # TODO: For ExtensionRow and a specific field only, generalize ?
    # TODO: What happens if called on a Core Row?
    def get_all_rows_by_coreid(self, core_id: int) -> List[Row]:
        """Return a list of :class:`dwca.rows.ExtensionRow` whose Core Id field match `core_id`."""
        if core_id not in self.coreid_index:
            return []

        return [self.get_row_by_position(p) for p in self.coreid_index[core_id]]  # type: ignore # FIXME

    def get_row_by_position(self, position: int) -> Union[CoreRow, ExtensionRow]:
        """Return the row at `position` in the file.

        Header lines are ignored.

        :raises: IndexError if there's no line at `position`.
        """

        line = self._get_line_by_position(position)
        if self.file_descriptor.represents_corefile:
            return CoreRow(line, position, self.file_descriptor)
        else:
            return ExtensionRow(line, position, self.file_descriptor)

    # Raises IndexError if position is incorrect
    def _get_line_by_position(self, position: int) -> str:
        self._file_stream.seek(self._line_offsets[position + self.lines_to_ignore], 0)
        return self._file_stream.readline()

    def close(self) -> None:
        """Close the file.

        The content of the file will not be accessible in any way afterwards.
        """
        self._file_stream.close()


def _get_all_line_offsets(f: IO, encoding: str) -> array:
    """Parse the file whose handler is given and return an array (long) containing the start offset\
    of each line.

    The values in the array are suitable for seek() operations.

    This function can take long for large files.

    It needs to know the file encoding to properly count the bytes in a given string.
    """
    f.seek(0, 0)

    # We use an array of Longs instead of a list to store the index.
    # It's much more memory efficient, and a few tests w/ 1-4Gb uncompressed archives
    # didn't show any significant slowdown (see benchmarks/ for current measurements).
    line_offsets = array("L")
    offset = 0
    for line in f:
        line_offsets.append(offset)
        offset += len(line.encode(encoding))

    f.seek(0, 0)
    return line_offsets
