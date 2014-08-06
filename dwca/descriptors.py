# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup


class _CoreDescriptor(object):
    """Class used to encapsulate the Core section of the Descriptor"""
    def __init__(self, coresection_xml):
        #:
        self.raw_beautifulsoup = coresection_xml  # It's a Tag instance

        #:
        self.type = self.raw_beautifulsoup['rowType']

        # a Set containing all the Darwin Core terms appearing in Core file
        term_names = [f['term'] for f in self.raw_beautifulsoup.findAll('field')]
        #:
        self.terms = set(term_names)


# TODO: Make _ArchiveDescriptor better structured (.core, .extension w/ child objects, ...)
class _ArchiveDescriptor(object):
    """Class used to encapsulate the Archive Descriptor"""
    def __init__(self, metaxml_content):
        #:
        self.raw_beautifulsoup = BeautifulSoup(metaxml_content, 'xml')
        
        #:
        self.extensions_type = [e['rowType'] for e in self.raw_beautifulsoup.findAll('extension')]

        #:
        self.metadata_filename = self.raw_beautifulsoup.archive['metadata']  # Relative to archive

        self.core = _CoreDescriptor(self.raw_beautifulsoup.core)

        
