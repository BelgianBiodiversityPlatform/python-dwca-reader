# -*- coding: utf-8 -*-

"""This module provides classes that represents the descriptor (meta.xml) file in a DarwinCore Archive.

"""

from bs4 import BeautifulSoup


class SectionDescriptor(object):
    """Class used to encapsulate a file section (Core or Extension) from the Archive Descriptor."""
    def __init__(self, section_tag):
        #: A :class:`BeautifulSoup.Tag` instance containing the whole XML for this section.
        self.raw_beautifulsoup = section_tag

        if self._autodetect_for_core():
            #: True if this section is used to represent the core file/section of an archive.
            self.represents_corefile = True
            #: True if this section is used to represent an extension file/section in an archive.
            self.represents_extensionfile = False
            #: If the section represents a core data file, the index/position of the id column in
            #: that file.
            self.id_index = int(self.raw_beautifulsoup.id['index'])
        else:
            self.represents_corefile = False
            self.represents_extensionfile = True
            #: If the section represents an extension data file, the index/position of the core_id
            #: column in that file. The `core_id` in an extension is the foreign key to the
            #: "extended" core row.
            self.coreid_index = int(self.raw_beautifulsoup.coreid['index'])

        #:
        self.type = self.raw_beautifulsoup['rowType']

        #: A list of dicts where each entry represent a data field in use.
        #:
        #: Each dict contains:
        #:      - The term identifier
        #:      - (Possibly) a default value
        #:      - The column index/position in the CSV file (except if we use a default value
        #:        instead)
        #:
        #: Example::
        #:
        #:      [{'term': 'http://rs.tdwg.org/dwc/terms/scientificName',
        #:        'index': '1',
        #:        'default': None},
        #:
        #:       {'term': 'http://rs.tdwg.org/dwc/terms/locality',
        #:        'index': '2',
        #:        'default': ''},
        #:
        #:       # The data for `country` is a the default value 'Belgium' for all rows, so there's
        #:       # no column in CSV file.
        #:
        #:       {'term': 'http://rs.tdwg.org/dwc/terms/country',
        #:        'index': None,
        #:        'default': 'Belgium'}]
        self.fields = []
        for f in self.raw_beautifulsoup.findAll('field'):
            default = (f['default'] if f.has_attr('default') else None)
            
            # Default fields don't have an index attribute
            index = (int(f['index']) if f.has_attr('index') else None)

            self.fields.append({'term': f['term'], 'index': index, 'default': default})

        #: A set containing all the Darwin Core terms appearing in file
        self.terms = set([f['term'] for f in self.fields])

        #: The data file location, relative to the archive root.
        self.file_location = self.raw_beautifulsoup.files.location.string

        #: The file encoding, as specified in the archive descriptor. Example: "utf-8".
        self.encoding = self.raw_beautifulsoup['encoding']

        #: The string or character used as a line separator in the data file. Example: "\\n".
        try:
            self.lines_terminated_by = (self.raw_beautifulsoup['linesTerminatedBy']
                                            .decode("string-escape"))
        except KeyError:
            self.lines_terminated_by = '\n'  # Default value according to the standard

        #: The string or character used as a field separator in the data file. Example: "\\t".
        try:
            self.fields_terminated_by = (self.raw_beautifulsoup['fieldsTerminatedBy']
                                             .decode("string-escape"))
        except KeyError:
            self.fields_terminated_by = '\t'

    def _autodetect_for_core(self):
        """Returns True if instance represents a Core file."""
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
            return 0  # Default value according to the standard


class ArchiveDescriptor(object):
    """Class used to encapsulate the whole Archive Descriptor (`meta.xml`)."""
    def __init__(self, metaxml_content):
        #: A :class:`BeautifulSoup` instance containing the whole Archive Descriptor.
        self.raw_beautifulsoup = BeautifulSoup(metaxml_content, 'xml')
        
        #: The (relative to archive root) path to the (scientific) metadata of the archive.
        self.metadata_filename = self.raw_beautifulsoup.archive['metadata']

        #: An instance of :class:`dwca.descriptors.SectionDescriptor` describing the data core file
        #: of the archive
        self.core = SectionDescriptor(self.raw_beautifulsoup.core)

        #: A list of :class:`dwca.descriptors.SectionDescriptor` instances describing each of the
        #: archive's extension files
        self.extensions = [SectionDescriptor(tag) for tag in self.raw_beautifulsoup.findAll('extension')]

        #: A list of extension types in use in the archive.
        #:
        #: Example::
        #:
        #:     ["http://rs.gbif.org/terms/1.0/VernacularName",
        #:      "http://rs.gbif.org/terms/1.0/Description"]
        self.extensions_type = [e.type for e in self.extensions]
