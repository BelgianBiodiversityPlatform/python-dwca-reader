# -*- coding: utf-8 -*-

import io
import os

from array import array


class _EmbeddedCSV(object):
    """Internal use class used to encapsulate a DwcA-enclosed CSV file and its metadata."""
    # TODO: Test this class
    # Not done yet cause issues there will probably make DwCAReader tests fails anyway
    # In the future it could make sense to make it public
    def __init__(self, file_descriptor, unzipped_folder_path):
        #unzipped_folder_path: absolute path to the directory containing the unzipped archive.
        
        self._file_descriptor = file_descriptor
        self._unzipped_folder_path = unzipped_folder_path

        self._core_fhandler = io.open(self.filepath,
                                      mode='r',
                                      encoding=self._file_descriptor.encoding,
                                      newline=self._file_descriptor.lines_terminated_by,
                                      errors='replace')

        # On init, we parse the file once to build an index of newlines (including lines to ignore)
        # that will make random access faster later on...
        self._line_offsets = get_all_line_offsets(self._core_fhandler, self._file_descriptor.encoding)

        self.lines_to_ignore = self._file_descriptor.lines_to_ignore

    @property
    def filepath(self):
        """Returns the absolute path to the 'subject' file."""
        return os.path.join(self._unzipped_folder_path,
                            self._file_descriptor.file_location)

    def _position_file_after_header(self):
        self._core_fhandler.seek(0, 0)
        if self.lines_to_ignore > 0:
            self._core_fhandler.readlines(self.lines_to_ignore)

    def __iter__(self):
        self._position_file_after_header()
        return self

    def next(self):
        for line in self._core_fhandler:
            return line
        
        raise StopIteration
    
    def get_row_by_index(self, index):
        try:
            self._core_fhandler.seek(self._line_offsets[index + self.lines_to_ignore], 0)
            return self._core_fhandler.readline()
        except IndexError:
            return None

    
def get_all_line_offsets(f, encoding):
    """ Parse the file whose handler is given and return a list of each line beginning positions.

        The value returned is suitable for seek() operations.
        This can take long for large files.

        It needs to know the encoding to properly count the bytes in a given string.
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
