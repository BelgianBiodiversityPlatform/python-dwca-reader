# -*- coding: utf-8 -*-

import io
import os


class _EmbeddedCSV(object):
    """Internal use class used to encapsulate a DwcA-enclosed CSV file and its metadata."""
    # TODO: Test this class
    # Not done yet cause issues there will probably make DwCAReader tests fails anyway
    # In the future it could make sense to make it public
    def __init__(self, metadata_section, unzipped_folder_path):
        #metadata_section: <core> or <extension> section of metaxml concerning the file to iterate.
        #unzipped_folder_path: absolute path to the directory containing the unzipped archive.
        
        self._metadata_section = metadata_section
        self._unzipped_folder_path = unzipped_folder_path

        self._core_fhandler = io.open(self.filepath,
                                      mode='r',
                                      encoding=self.encoding,
                                      newline=self.newline_str,
                                      errors='replace')
        
    @property
    def headers(self):
        """Returns a list of (ordered) column names that can be used to create a header line."""
        field_tags = self._metadata_section.find_all('field')

        columns = {}
        
        for tag in field_tags:
            columns[int(tag['index'])] = tag['term']

        # In addition to DwC terms, we may also have id or core_id columns
        if self._metadata_section.id:
            columns[int(self._metadata_section.id['index'])] = 'id'
        if self._metadata_section.coreid:
            columns[int(self._metadata_section.id['coreindex'])] = 'coreid'

        return [columns[f] for f in sorted(columns.iterkeys())]

    @property
    def filepath(self):
        """Returns the absolute path to the 'subject' file."""
        return os.path.join(self._unzipped_folder_path,
                            self._metadata_section.files.location.string)

    @property
    def encoding(self):
        return self._metadata_section['encoding']

    @property
    def newline_str(self):
        return self._metadata_section['linesTerminatedBy'].decode("string-escape")

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

    # TODO: Optimize for large files ?
    # ideas: http://stackoverflow.com/questions/620367/python-how-to-jump-to-a-particular-line-in-a-huge-text-file
    def get_row_by_index(self, index):
        self._position_file_after_header()

        for (i, row) in enumerate(self._core_fhandler):
            if i == index:
                return row
        else:
            return None  # Reached end of file

    @property
    def lines_to_ignore(self):
        try:
            return int(self._metadata_section['ignoreHeaderLines'])
        except KeyError:
            return 0
