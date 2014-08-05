# -*- coding: utf-8 -*-

import io
import os

from bs4 import BeautifulSoup


# TODO: Make _ArchiveDescriptor better structured (.core, .extension w/ child objects, ...)
class _ArchiveDescriptor(object):
    """Class used to encapsulate the Archive Descriptor"""
    def __init__(self, metaxml_content):
        #:
        self.raw_beautifulsoup = BeautifulSoup(metaxml_content, 'xml')

        #:
        self.core_type = self.raw_beautifulsoup.core['rowType']
        
        #:
        self.extensions_type = [e['rowType'] for e in self.raw_beautifulsoup.findAll('extension')]

        #:
        self.metadata_filename = self.raw_beautifulsoup.archive['metadata']  # Relative to archive

        # a Set containing all the Darwin Core terms appearing in Core file
        term_names = [f['term'] for f in self.raw_beautifulsoup.core.findAll('field')]
        #:
        self.core_terms = set(term_names)


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

        # On init, we parse the file once to build an index of newlines (including lines to ignore)
        # that will make random access faster later on...
        self._line_offsets = get_all_line_offsets(self._core_fhandler, self.encoding)

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
    
    def get_row_by_index(self, index):
        if index < 0:
            return None
        try:
            self._core_fhandler.seek(self._line_offsets[index + self.lines_to_ignore], 0)
            return self._core_fhandler.readline()
        except IndexError:
            return None

    @property
    def lines_to_ignore(self):
        try:
            return int(self._metadata_section['ignoreHeaderLines'])
        except KeyError:
            return 0


def get_all_line_offsets(f, encoding):
    """ Parse the file whose handler is given and return a list of each line beginning positions.

        The value returned is suitable for seek() operations.
        This can take long for large files.

        It needs to know the encoding to properly count the bytes in a given string.
    """

    f.seek(0, 0)
    line_offsets = []
    offset = 0
    for line in f:
        line_offsets.append(offset)
        offset += len(line.encode(encoding))
    
    f.seek(0, 0)
    return line_offsets
