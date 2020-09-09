"""File-related classes and functions."""

import io
import os
from array import array
from typing import List, Union, IO, Dict, Optional

from dwca.descriptors import DataFileDescriptor
from dwca.rows import CoreRow, ExtensionRow


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

        self._file_stream = io.open(
            os.path.join(work_directory, self.file_descriptor.file_location),
            mode="r",
            encoding=self.file_descriptor.file_encoding,
            newline=self.file_descriptor.lines_terminated_by,
            errors="replace",
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

    def _position_file_after_header(self) -> None:
        self._file_stream.seek(0, 0)
        if self.lines_to_ignore > 0:
            self._file_stream.readlines(self.lines_to_ignore)

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
    def coreid_index(self)  -> Dict[str, array]:
        """An index of the core rows referenced by this data file.

        It is a Python dict such as:
        ::

            {
            core_id1: [1],    # Row at position 1 references a Core Row whose ID is core_id1
            core_id2: [8, 10] # Rows at position 8 and 10 references a Core Row whose ID is core_id2
            }

        :raises: AttributeError if accessed on a core data file.

        .. warning::

            for permformance reasons, dictionary values are arrays('L') instead of regular python lists

        .. warning::

            coreid_index is only available for extension data files.

        .. warning::

            Creating this index can be time and memory consuming for large archives, so it's created on the fly
            at first access.
        """
        if self.file_descriptor.represents_corefile:
            raise AttributeError(
                "coreid_index is only available for extension data files"
            )

        if self._coreid_index is None:
            self._coreid_index = self._build_coreid_index()

        return self._coreid_index

    def _build_coreid_index(self) -> Dict[str, List[int]]:
        """Build and return an index of Core Rows IDs suitable for `CSVDataFile.coreid_index`."""
        index = {}  # type: Dict[str, array[int]]

        for position, row in enumerate(self):
            tmp = ExtensionRow(row, position, self.file_descriptor)
            index.setdefault(tmp.core_id, array('L')).append(position)

        return index

    # TODO: For ExtensionRow and a specific field only, generalize ?
    # TODO: What happens if called on a Core Row?
    def get_all_rows_by_coreid(self, core_id: int) -> List[ExtensionRow]:
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
    # didn't shown any significant slowdown.
    #
    # See mini-benchmark in minibench.py
    line_offsets = array("L")
    offset = 0
    for line in f:
        line_offsets.append(offset)
        offset += len(line.encode(encoding))

    f.seek(0, 0)
    return line_offsets
