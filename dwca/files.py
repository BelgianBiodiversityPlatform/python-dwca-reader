# -*- coding: utf-8 -*-

"""This module provide file-related classes and functions."""

import io
import os

from array import array

from dwca.rows import CoreRow, ExtensionRow


class CSVDataFile(object):
    """Object used to access a DwCA-enclosed CSV data file.

    :param work_directory: absolute path to the target directory (archive content, previously\
    extracted if necessary).
    :param file_descriptor: an instance of :class:`dwca.descriptors.DataFileDescriptor`\
    describing the data file.

    The file content can be accessed:

    * By iterating on this object
    * With :meth:`get_row_by_position`
    * With :meth:`get_all_rows_by_coreid` (extensions data file only)

    On initialization, an index of new lines is build. This may take time, but makes random access\
    faster.
    """

    # TODO: Test this class
    # Not done yet cause issues there will probably make DwCAReader tests fails anyway
    def __init__(self, work_directory, file_descriptor):
        """Initialize the CSVDataFile object."""
        #: An instance of :class:`dwca.descriptors.DataFileDescriptor`, as given to the
        #: constructor.
        self.file_descriptor = file_descriptor

        self._file_stream = io.open(os.path.join(work_directory,
                                                 self.file_descriptor.file_location),
                                    mode='r',
                                    encoding=self.file_descriptor.file_encoding,
                                    newline=self.file_descriptor.lines_terminated_by,
                                    errors='replace')

        # On init, we parse the file once to build an index of newlines (including lines to ignore)
        # that will make random access faster later on...
        self._line_offsets = _get_all_line_offsets(self._file_stream,
                                                   self.file_descriptor.file_encoding)

        #: Number of lines to ignore (header lines) in the CSV file.
        self.lines_to_ignore = self.file_descriptor.lines_to_ignore

    def _position_file_after_header(self):
        self._file_stream.seek(0, 0)
        if self.lines_to_ignore > 0:
            self._file_stream.readlines(self.lines_to_ignore)

    def __iter__(self):
        self._position_file_after_header()
        return self

    def __next__(self):
        return self.next()

    def next(self):  # NOQA
        for line in self._file_stream:
            return line

        raise StopIteration

    # Returns a index of the per core_id positions of Rows in the file:
    # {core_id1: []}

    # TODO: Generalize this so we can create indexes on any field ?
    def _build_coreid_index(self):
        index = {}
        pos = 0
        for l in self:
            tmp = ExtensionRow(l, self.file_descriptor)
            if tmp.core_id not in index:
                index[tmp.core_id] = [pos]
            else:
                index[tmp.core_id].append(pos)

            pos = pos + 1
        return index

    # TODO: For ExtensionRow and a specific field only, generalize ?
    # TODO: What happens if called on a Core Row?
    def get_all_rows_by_coreid(self, core_id):
        """Return a list of :class:`dwca.rows.ExtensionRow` whose Core Id field match `core_id`."""
        if not hasattr(self, '_coreid_index'):
            self._coreid_index = self._build_coreid_index()

        if core_id not in self._coreid_index:
            return []
        else:
            return [self.get_row_by_position(p) for p in self._coreid_index[core_id]]

    def get_row_by_position(self, position):
        """Return the row at `position` in the file."""
        try:
            l = self._get_line_by_position(position)
            if self.file_descriptor.represents_corefile:
                return CoreRow(l, self.file_descriptor)
            else:
                return ExtensionRow(l, self.file_descriptor)
        except IndexError:
            return None

    # Raises IndexError if position is incorrect
    def _get_line_by_position(self, position):
        self._file_stream.seek(self._line_offsets[position + self.lines_to_ignore], 0)
        return self._file_stream.readline()

    # TODO: test this method
    def close(self):
        """Close the file."""
        self._file_stream.close()


def _get_all_line_offsets(f, encoding):
    """Parse the file whose handler is given and return an array (long) containing the start offset\
    of each line.

    The values in the array are suitable for seek() operations.

    This function can take long for large files.

    It needs to know the file encoding to properly count the bytes in a given string.
    """
    f.seek(0, 0)

    # We use an array of Longs instead of a basic list to store the index.
    # It's much more memory efficient, and a few tests w/ 1-4Gb uncompressed archives
    # didn't shown any significant slowdown.
    #
    # See mini-benchmark in minibench.py
    line_offsets = array('L')
    offset = 0
    for line in f:
        line_offsets.append(offset)
        offset += len(line.encode(encoding))

    f.seek(0, 0)
    return line_offsets
