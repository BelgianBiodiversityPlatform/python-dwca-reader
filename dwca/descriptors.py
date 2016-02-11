# -*- coding: utf-8 -*-

"""This module provides classes to represents the descriptor (meta.xml) file of a DwC-A.

"""

import sys
import re
import xml.etree.ElementTree as ET


class SectionDescriptor(object):
    """Class used to encapsulate a file section (Core or Extension) from the Archive Descriptor."""
    def __init__(self, section_tag):
        #: A :class:`xml.etree.ElementTree.Element` instance containing the whole XML for this
        #: section.
        self.raw_element = section_tag

        if self._autodetect_for_core():
            #: True if this section is used to represent the core file/section of an archive.
            self.represents_corefile = True
            #: True if this section is used to represent an extension file/section in an archive.
            self.represents_extensionfile = False
            #: If the section represents a core data file, the index/position of the id column in
            #: that file.
            self.id_index = int(self.raw_element.find('id').get('index'))
        else:
            self.represents_corefile = False
            self.represents_extensionfile = True
            #: If the section represents an extension data file, the index/position of the core_id
            #: column in that file. The `core_id` in an extension is the foreign key to the
            #: "extended" core row.
            self.coreid_index = int(self.raw_element.find('coreid').get('index'))

        #:
        self.type = self.raw_element.get('rowType')

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

        for f in self.raw_element.findall('field'):
            default = f.get('default', None)

            # Default fields don't have an index attribute
            index = (int(f.get('index')) if f.get('index') else None)

            self.fields.append({'term': f.get('term'), 'index': index, 'default': default})

        #: A set containing all the Darwin Core terms appearing in file
        self.terms = set([f['term'] for f in self.fields])

        #: The data file location, relative to the archive root.
        self.file_location = self.raw_element.find('files').find('location').text

        #: The file encoding, as specified in the archive descriptor. Example: "utf-8".
        self.encoding = self.raw_element.get('encoding')

        #: The string or character used as a line separator in the data file. Example: "\\n".
        raw_ltb = self.raw_element.get('linesTerminatedBy')
        if raw_ltb:
            if sys.version_info[0] == 2:  # Python 2
                self.lines_terminated_by = raw_ltb.decode("string-escape")
            else:
                self.lines_terminated_by = bytes(raw_ltb, self.encoding).decode("unicode-escape")
        else:
            self.lines_terminated_by = '\n'  # Default value according to the standard

        #: The string or character used as a field separator in the data file. Example: "\\t".
        raw_ftb = self.raw_element.get('fieldsTerminatedBy')
        if raw_ftb:
            if sys.version_info[0] == 2:  # Python 2
                self.fields_terminated_by = raw_ftb.decode("string-escape")
            else:
                self.fields_terminated_by = bytes(raw_ftb, self.encoding).decode("unicode-escape")
        else:
            self.fields_terminated_by = '\t'

    def _autodetect_for_core(self):
        """Returns True if instance represents a Core file."""
        return self.raw_element.tag == 'core'

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

        return [columns[f] for f in sorted(columns.keys())]

    @property
    def lines_to_ignore(self):
        return int(self.raw_element.get('ignoreHeaderLines', 0))


class ArchiveDescriptor(object):
    """Class used to encapsulate the whole Archive Descriptor (`meta.xml`)."""
    def __init__(self, metaxml_content, files_to_ignore=None):
        if files_to_ignore is None:
            files_to_ignore = []

        # Let's drop the XML namespace to avoid prefixes
        metaxml_content = re.sub(' xmlns="[^"]+"', '', metaxml_content, count=1)

        #: A :class:`xml.etree.ElementTree.Element` instance containing the complete Archive
        #: Descriptor.
        self.raw_element = ET.fromstring(metaxml_content)

        #: The (relative to archive root) path to the (scientific) metadata of the archive.
        self.metadata_filename = self.raw_element.attrib['metadata']

        #: An instance of :class:`dwca.descriptors.SectionDescriptor` describing the data core file
        #: of the archive
        self.core = SectionDescriptor(self.raw_element.find('core'))

        #: A list of :class:`dwca.descriptors.SectionDescriptor` instances describing each of the
        #: archive's extension files
        self.extensions = []
        for tag in self.raw_element.findall('extension'):
            if tag.find('files').find('location').text not in files_to_ignore:
                self.extensions.append(SectionDescriptor(tag))

        #: A list of extension types in use in the archive.
        #:
        #: Example::
        #:
        #:     ["http://rs.gbif.org/terms/1.0/VernacularName",
        #:      "http://rs.gbif.org/terms/1.0/Description"]
        self.extensions_type = [e.type for e in self.extensions]
