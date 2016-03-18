# -*- coding: utf-8 -*-

"""This module provides classes to represents descriptors of a DwC-A.

- :class:`ArchiveDescriptor` represents the full archive descriptor, initialized from the metafile.
- :class:`DataFileDescriptor describes characteristics of a given data file in the archive. It's
generally initialized from a subsection of the ArchiveDescriptor, but in case the Archives contains
no metafile, it can also be created by introspecting the CSV data file.
"""

import csv
import os
import sys
import re
import io
import xml.etree.ElementTree as ET


class DataFileDescriptor(object):
    """Class used to encapsulate a file section (Core or Extension) from the Archive Descriptor."""

    def __init__(self, section_tag=None, datafile_path=None):
        # Args:
        # - section_tag :class:`xml.etree.ElementTree.Element` instance containing the whole
        #   XML for this section (in case we want to build a descriptor based on the metafile).
        # - datafile: the data file (in case we want to build a descriptor based on file analysis-
        #   needed for archive without metafile)

        if section_tag is not None:
            self._init_from_metafile_section(section_tag)
            self.created_from_file = False
        else:
            self._init_from_file(datafile_path)
            self.created_from_file = True

        #: A Python set containing all the Darwin Core terms appearing in file
        self.terms = set([f['term'] for f in self.fields])

    def _init_from_file(self, datafile_path):
        self.raw_element = None  # No metafile, so no XML session to store
        self.represents_corefile = True  # In archives without metafiles, there's only core data
        self.represents_extension = False
        self.type = None  # No metafile => no rowType information
        self.file_location = os.path.basename(datafile_path)  # datafile_path also contains the dir
        self.file_encoding = "utf-8"
        self.id_index = None

        with io.open(datafile_path, 'rU', encoding=self.file_encoding) as datafile:
            # Autodetect fields/lines termination
            dialect = csv.Sniffer().sniff(datafile.readline())

            # Normally, EOL characters should be available in dialect.lineterminator, but it
            # seems it always returns \r\n. The workaround therefore consists to open the file
            # in universal-newline mode, which adds a newlines attribute.
            self.lines_terminated_by = datafile.newlines

            self.fields_terminated_by = dialect.delimiter
            self.fields_enclosed_by = dialect.quotechar

            datafile.seek(0)

            dialect.delimiter = str(dialect.delimiter)  # Python 2 fix
            dialect.quotechar = str(dialect.quotechar)  # Python 2 fix

            dr = csv.reader(datafile, dialect)
            columns = next(dr)

            self.fields = []
            for i, c in enumerate(columns):
                self.fields.append({'index': i, 'term': c, 'default': None})

    def _init_from_metafile_section(self, section_tag):
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

        #: The data file location, relative to the archive root.
        self.file_location = self.raw_element.find('files').find('location').text

        #: The file encoding, as specified in the archive descriptor. Example: "utf-8".
        self.file_encoding = self.raw_element.get('encoding')

        #: The string or character used as a line separator in the data file. Example: "\\n".
        self.lines_terminated_by = _decode_xml_attribute(raw_element=self.raw_element,
                                                         attribute_name='linesTerminatedBy',
                                                         default_value='\n',
                                                         encoding=self.file_encoding)

        #: The string or character used as a field separator in the data file. Example: "\\t".
        self.fields_terminated_by = _decode_xml_attribute(raw_element=self.raw_element,
                                                          attribute_name='fieldsTerminatedBy',
                                                          default_value='\t',
                                                          encoding=self.file_encoding)

        #: The string or character used to enclose fields in the data file.
        self.fields_enclosed_by = _decode_xml_attribute(raw_element=self.raw_element,
                                                        attribute_name='fieldsEnclosedBy',
                                                        default_value='',
                                                        encoding=self.file_encoding)

    def _autodetect_for_core(self):
        """Return True if instance represents a Core file."""
        return self.raw_element.tag == 'core'

    @property
    def headers(self):
        """Return a list of (ordered) column names that can be used to create a header line."""
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
        if self.created_from_file:
            # Single-file archives also have a header line with DwC terms
            return 1
        else:
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
        self.metadata_filename = self.raw_element.get('metadata', None)

        #: An instance of :class:`dwca.descriptors.DataFileDescriptor` describing the data core
        # file of the archive
        self.core = DataFileDescriptor(self.raw_element.find('core'))

        #: A list of :class:`dwca.descriptors.DataFileDescriptor` instances describing each of the
        #: archive's extension files
        self.extensions = []
        for tag in self.raw_element.findall('extension'):
            if tag.find('files').find('location').text not in files_to_ignore:
                self.extensions.append(DataFileDescriptor(tag))

        #: A list of extension types in use in the archive.
        #:
        #: Example::
        #:
        #:     ["http://rs.gbif.org/terms/1.0/VernacularName",
        #:      "http://rs.gbif.org/terms/1.0/Description"]
        self.extensions_type = [e.type for e in self.extensions]


def _decode_xml_attribute(raw_element, attribute_name, default_value, encoding):
    # Gets XML attribute and decode it to make it usable. If it doesn't exists, it returns
    # default_value.

    raw_attribute = raw_element.get(attribute_name)
    if raw_attribute:
        if sys.version_info[0] == 2:  # Python 2
            return raw_attribute.decode("string_escape")
        else:
            return bytes(raw_attribute, encoding).decode("unicode-escape")
    else:
            return default_value
