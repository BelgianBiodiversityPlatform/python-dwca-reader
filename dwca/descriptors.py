# -*- coding: utf-8 -*-

"""This module provides classes to represents descriptors of a DwC-A.

- :class:`ArchiveDescriptor` represents the full archive descriptor, initialized from the \
metafile content.
- :class:`DataFileDescriptor` describes characteristics of a given data file in the archive. It's \
either created from a subsection of the ArchiveDescriptor describing the data file, either by \
introspecting the CSV data file (useful for Archives without metafile).

"""

import csv
import os
import sys
import re
import io
import xml.etree.ElementTree as ET


class DataFileDescriptor(object):
    """Those objects describe a data file fom the archive.

    They're generally not instanciated manually, but rather by calling:

        * :meth:`.make_from_metafile_section` (if the archive contains a metafile)
        * :meth:`make_from_file` (created by analyzing the data file)
    """

    def __init__(self, created_from_file, raw_element, represents_corefile, datafile_type,
                 file_location, file_encoding, id_index, coreid_index, fields,
                 lines_terminated_by, fields_enclosed_by, fields_terminated_by):
        #: True if this descriptor was created by analyzing the data file.
        self.created_from_file = created_from_file
        #: The <section> element describing the data file, from the metafile. None if the
        #: archive contains no metafile.
        self.raw_element = raw_element
        #: True if this descriptor is used to represent the core file an archive.
        self.represents_corefile = represents_corefile
        #: True if this descriptor is used to represent an extension file in an archive.
        self.represents_extension = not represents_corefile
        #:
        self.type = datafile_type
        #: The data file location, relative to the archive root.
        self.file_location = file_location
        #: The encoding of the data file. Example: "utf-8".
        self.file_encoding = file_encoding
        #: If the section represents a core data file, the index/position of the id column in
        #: that file.
        self.id_index = id_index
        #: If the section represents an extension data file, the index/position of the core_id
        #: column in that file. The `core_id` in an extension is the foreign key to the
        #: "extended" core row.
        self.coreid_index = coreid_index
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
        self.fields = fields

        #: The string or character used as a line separator in the data file. Example: "\\n".
        self.lines_terminated_by = lines_terminated_by
        #: The string or character used to enclose fields in the data file.
        self.fields_enclosed_by = fields_enclosed_by
        #: The string or character used as a field separator in the data file. Example: "\\t".
        self.fields_terminated_by = fields_terminated_by

    @classmethod
    def make_from_file(cls, datafile_path):
        """Create and return a DataFileDescriptor by analyzing the file at datafile_path.

        :param datafile_path: Relative path to a data file to analyze in order to instantiate the\
        descriptor.
        :type datafile_path: str
        """
        file_encoding = "utf-8"

        with io.open(datafile_path, 'rU', encoding=file_encoding) as datafile:
            # Autodetect fields/lines termination
            dialect = csv.Sniffer().sniff(datafile.readline())

            # Normally, EOL characters should be available in dialect.lineterminator, but it
            # seems it always returns \r\n. The workaround therefore consists to open the file
            # in universal-newline mode, which adds a newlines attribute.
            lines_terminated_by = datafile.newlines

            fields_terminated_by = dialect.delimiter
            fields_enclosed_by = dialect.quotechar

            datafile.seek(0)

            dialect.delimiter = str(dialect.delimiter)  # Python 2 fix
            dialect.quotechar = str(dialect.quotechar)  # Python 2 fix

            dr = csv.reader(datafile, dialect)
            columns = next(dr)

            fields = []
            for i, c in enumerate(columns):
                fields.append({'index': i, 'term': c, 'default': None})

        return cls(created_from_file=True,
                   raw_element=None,  # No metafile, so no XML section to store
                   represents_corefile=True,  # In archives w/o metafiles, there's only core data
                   datafile_type=None,  # No metafile => no rowType information
                   file_location=os.path.basename(datafile_path),  # datafile_path also has the dir
                   file_encoding=file_encoding,
                   id_index=None,
                   coreid_index=None,
                   fields=fields,
                   lines_terminated_by=lines_terminated_by,
                   fields_enclosed_by=fields_enclosed_by,
                   fields_terminated_by=fields_terminated_by
                   )

    @classmethod
    def make_from_metafile_section(cls, section_tag):
        """Create and return a DataFileDescriptor from a metafile <section> tag.

        :param section_tag: The XML Element section containing details about the data file.
        :type section_tag: :class:`xml.etree.ElementTree.Element`
        """
        if section_tag.tag == 'core':
            id_index = int(section_tag.find('id').get('index'))
            coreid_index = None
        else:
            id_index = None
            coreid_index = int(section_tag.find('coreid').get('index'))

        fields = []
        for f in section_tag.findall('field'):
            default = f.get('default', None)

            # Default fields don't have an index attribute
            index = (int(f.get('index')) if f.get('index') else None)

            fields.append({'term': f.get('term'), 'index': index, 'default': default})

        file_encoding = section_tag.get('encoding')

        lines_terminated_by = _decode_xml_attribute(raw_element=section_tag,
                                                    attribute_name='linesTerminatedBy',
                                                    default_value='\n',
                                                    encoding=file_encoding)

        fields_terminated_by = _decode_xml_attribute(raw_element=section_tag,
                                                     attribute_name='fieldsTerminatedBy',
                                                     default_value='\t',
                                                     encoding=file_encoding)

        fields_enclosed_by = _decode_xml_attribute(raw_element=section_tag,
                                                   attribute_name='fieldsEnclosedBy',
                                                   default_value='',
                                                   encoding=file_encoding)

        return cls(created_from_file=False,
                   raw_element=section_tag,
                   represents_corefile=(section_tag.tag == 'core'),
                   datafile_type=section_tag.get('rowType'),
                   file_location=section_tag.find('files').find('location').text,
                   file_encoding=file_encoding,
                   id_index=id_index,
                   coreid_index=coreid_index,
                   fields=fields,
                   lines_terminated_by=lines_terminated_by,
                   fields_enclosed_by=fields_enclosed_by,
                   fields_terminated_by=fields_terminated_by)

    @property
    def terms(self):
        """Return a Python set containing all the Darwin Core terms appearing in file."""
        return set([f['term'] for f in self.fields])

    @property
    def headers(self):
        """Return a list of (ordered) column names that can be used to create a header line."""
        columns = {}

        for f in self.fields:
            if f['index']:  # Some (default values for example) don't have a corresponding col.
                columns[f['index']] = f['term']

        # In addition to DwC terms, we may also have id (Core) or core_id (Extensions) columns
        if self.id_index is not None:
            columns[self.id_index] = 'id'
        if self.coreid_index is not None:
            columns[self.coreid_index] = 'coreid'

        return [columns[f] for f in sorted(columns.keys())]

    @property
    def lines_to_ignore(self):
        """Return the number of header lines/lines to ignore in the data file."""
        if self.created_from_file:
            # Single-file archives also have a header line with DwC terms
            return 1
        else:
            return int(self.raw_element.get('ignoreHeaderLines', 0))


class ArchiveDescriptor(object):
    """Class used to encapsulate the whole Metafile (`meta.xml`)."""

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
        self.core = DataFileDescriptor.make_from_metafile_section(self.raw_element.find('core'))

        #: A list of :class:`dwca.descriptors.DataFileDescriptor` instances describing each of the
        #: archive's extension files
        self.extensions = []
        for tag in self.raw_element.findall('extension'):
            if tag.find('files').find('location').text not in files_to_ignore:
                self.extensions.append(DataFileDescriptor.make_from_metafile_section(tag))

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
