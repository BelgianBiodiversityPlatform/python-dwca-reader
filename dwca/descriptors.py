# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup


class SectionDescriptor(object):
    """Class used to encapsulate a file section (for Core or an Extension) from the Archive Descriptor"""
    def __init__(self, section_tag):
        #:
        self.raw_beautifulsoup = section_tag  # It's a Tag instance

        if self._autodetect_for_core():
            self.represents_corefile = True
            self.represents_extensionfile = False
            self.id_index = int(self.raw_beautifulsoup.id['index'])
        else:
            self.represents_corefile = False
            self.represents_extensionfile = True
            self.coreid_index = int(self.raw_beautifulsoup.coreid['index'])

        #:
        self.type = self.raw_beautifulsoup['rowType']

        #:
        self.fields = []
        for f in self.raw_beautifulsoup.findAll('field'):
            default = (f['default'] if f.has_attr('default') else None)
            
            # Default fields don't have an index attribute
            index = (f['index'] if f.has_attr('index') else None)

            self.fields.append({'term': f['term'], 'index': index, 'default': default})

        # a Set containing all the Darwin Core terms appearing in file
        #:
        self.terms = set([f['term'] for f in self.fields])

        #:
        self.file_location = self.raw_beautifulsoup.files.location.string  # TODO: Test !!!

        #:
        self.encoding = self.raw_beautifulsoup['encoding']  # TODO: test

        #:
        self.lines_terminated_by = self.raw_beautifulsoup['linesTerminatedBy'].decode("string-escape")  # TODO: test

        #:
        self.fields_terminated_by = self.raw_beautifulsoup['fieldsTerminatedBy'].decode("string-escape")  # TODO: test

    def _autodetect_for_core(self):
        """Returns True if instance represents a Core file"""
        return self.raw_beautifulsoup.name == 'core'

    @property
    def headers(self):
        """Returns a list of (ordered) column names that can be used to create a header line."""

        columns = {}
        
        for f in self.fields:
            if f['index']:  # Some (default values for example) don't have a corresponding col.
                columns[f['index']] = f['term']

        # In addition to DwC terms, we may also have id (Core) or core_id (Extensions) columns
        if hasattr(self, 'id_index'):
            columns[self.id_index] = 'id'
        if hasattr(self, 'coreid_index'):
            columns[self.coreid_index] = 'coreid'

        return [columns[f] for f in sorted(columns.iterkeys())]

    @property
    def lines_to_ignore(self):
        try:
            return int(self.raw_beautifulsoup['ignoreHeaderLines'])
        except KeyError:
            return 0


class ArchiveDescriptor(object):
    """Class used to encapsulate the Archive Descriptor"""
    def __init__(self, metaxml_content):
        #:
        self.raw_beautifulsoup = BeautifulSoup(metaxml_content, 'xml')
        
        #:
        self.metadata_filename = self.raw_beautifulsoup.archive['metadata']  # Relative to archive

        #:
        self.core = SectionDescriptor(self.raw_beautifulsoup.core)

        #:
        self.extensions = [SectionDescriptor(tag) for tag in self.raw_beautifulsoup.findAll('extension')]

        #:
        self.extensions_type = [e.type for e in self.extensions]

        
