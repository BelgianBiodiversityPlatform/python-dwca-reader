# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup


class _SectionDescriptor(object):
    """Class used to encapsulate the file section (for Core or an Extension) of the Descriptor"""
    def __init__(self, section_tag, is_core):
        #:
        self.raw_beautifulsoup = section_tag  # It's a Tag instance

        #:
        self.represents_corefile = is_core

        #:
        self.represents_extensionfile = not self.represents_corefile

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
        self.metadata_filename = self.raw_beautifulsoup.archive['metadata']  # Relative to archive

        #:
        self.core = _SectionDescriptor(self.raw_beautifulsoup.core, is_core=True)

        self.extensions = [_SectionDescriptor(tag, False) for tag in self.raw_beautifulsoup.findAll('extension')]

        #:
        self.extensions_type = [e.type for e in self.extensions]

        
