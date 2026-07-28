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

    An index of line offsets is built on first random access (:meth:`get_row_by_position` or\
    :meth:`get_all_rows_by_coreid`). This may take time for large files, but makes further random\
    access faster.
    """

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

        # The index of line offsets is only needed for random access, so it is built on
        # first use rather than here: opening an archive stays O(1) whatever its size.
        self._line_offsets = None  # type: Optional[array]

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

    def _get_line_offsets(self) -> array:
        if self._line_offsets is None:
            self._line_offsets = _build_line_offsets(
                self._file_path,
                self.file_descriptor.file_encoding,
                self.file_descriptor.lines_terminated_by,
            )
        return self._line_offsets

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
        if self._file_stream.closed:
            raise ValueError("The data file has been closed.")

        offsets = self._get_line_offsets()
        self._file_stream.seek(offsets[position + self.lines_to_ignore], 0)
        return self._file_stream.readline()

    def close(self) -> None:
        """Close the file.

        The content of the file will not be accessible in any way afterwards.
        """
        self._file_stream.close()


def _build_line_offsets(
    path: str, encoding: str, lines_terminated_by: str, chunk_size: int = 1024 * 1024
) -> array:
    """Return an array of the byte offset of every line in the file at `path`.

    The values are suitable for seek() on a stream opened with the same encoding.

    The file is scanned as bytes rather than as decoded text: decoding with
    errors="replace" turns an undecodable byte into U+FFFD, which does not re-encode to the
    same length, so computing offsets from decoded text desynchronises the index from the
    file.

    An array of Longs is used instead of a list. It is much more memory efficient, and a few
    tests with 1-4Gb uncompressed archives didn't show any significant slowdown.
    """
    terminator = lines_terminated_by.encode(encoding)
    terminator_length = len(terminator)

    line_offsets = array("L", [0])
    buffer = b""
    base = 0  # absolute offset of buffer[0] within the file

    with io.open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break

            buffer += chunk
            consumed = 0
            while True:
                found = buffer.find(terminator, consumed)
                if found == -1:
                    break
                consumed = found + terminator_length
                line_offsets.append(base + consumed)

            # Whatever follows the last terminator stays in the buffer: it may be an
            # unfinished line, or a terminator straddling the chunk boundary.
            base += consumed
            buffer = buffer[consumed:]

    # A file ending with the terminator has no extra empty line after it, so the offset
    # pointing at EOF is spurious. This also empties the index for a zero-byte file, which
    # must report no lines at all rather than one empty one.
    if line_offsets and line_offsets[-1] == os.path.getsize(path):
        line_offsets.pop()

    return line_offsets
