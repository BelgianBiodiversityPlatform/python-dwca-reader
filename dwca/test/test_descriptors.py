# -*- coding: utf-8 -*-
import os
import unittest
import zipfile

import xml.etree.ElementTree as ET

from dwca.descriptors import DataFileDescriptor, ArchiveDescriptor
from dwca.darwincore.utils import qualname as qn
from dwca.read import DwCAReader

from .helpers import (BASIC_ARCHIVE_PATH, EXTENSION_ARCHIVE_PATH,
                      MULTIEXTENSIONS_ARCHIVE_PATH, SIMPLE_CSV)


class TestDataFileDescriptor(unittest.TestCase):
    """Unit tests for DataFileDescriptor class."""

    def test_init_from_file(self):
        """ Ensure a DataFileDescriptor can be constructed directly from a CSV file.

        This is necessary for archives sans metafile.
        """
        with zipfile.ZipFile(SIMPLE_CSV, 'r') as archive:
            datafile_path = archive.extract('0008333-160118175350007.csv')

            d = DataFileDescriptor.make_from_file(datafile_path)
            # Check basic metadata with the file
            self.assertIsNone(d.raw_element)
            self.assertTrue(d.represents_corefile)
            self.assertFalse(d.represents_extension)
            self.assertIsNone(d.type)
            self.assertEqual(d.file_location, '0008333-160118175350007.csv')
            self.assertEqual(d.file_encoding, 'utf-8')
            self.assertEqual(d.lines_terminated_by, "\n")
            self.assertEqual(d.fields_terminated_by, "\t")
            self.assertEqual(d.fields_enclosed_by, '"')

            # Some checks on fields...

            # A few fields are checked
            expected_fields = ({'default': None, 'index': 0, 'term': 'gbifid'},
                               {'default': None, 'index': 3, 'term': 'kingdom'})

            for ef in expected_fields:
                self.assertTrue(ef in d.fields)

            # In total, there are 42 fields in this data file
            self.assertEqual(len(d.fields), 42)

            # No fields should have a default value (there's no metafile to set it!)
            for f in d.fields:
                self.assertIsNone(f['default'])

            # Ensure .terms is also set:
            self.assertEqual(len(d.terms), 42)

            # Cleanup extracted file
            os.remove(datafile_path)

    def test_lines_to_ignore(self):
        # With explicit "0"
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))

        self.assertEqual(core_descriptor.lines_to_ignore, 0)

        # With explicit 1
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))

        self.assertEqual(core_descriptor.lines_to_ignore, 1)

        # Implicit 0 (when nothing stated)
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))

        self.assertEqual(core_descriptor.lines_to_ignore, 0)

    def test_file_details(self):
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
            <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/locality"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))

        self.assertEqual(core_descriptor.file_location, "occurrence.txt")
        self.assertEqual(core_descriptor.file_encoding, "utf-8")
        # TODO: Also test .lines_terminated_by and .fields_terminated_by
        # (this seems a bit tricky, and it's already tested indirectly - many things would fail
        # without them)

    def test_fields(self):
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
            <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/locality"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))

        # .fields is supposed to return a list of dicts like those
        expected_fields = (
            {'term': 'http://rs.tdwg.org/dwc/terms/country',
             'index': None,
             'default': 'Belgium'},

            {'term': 'http://rs.tdwg.org/dwc/terms/scientificName',
             'index': 1,
             'default': None}
        )

        for ef in expected_fields:
            self.assertTrue(ef in core_descriptor.fields)

        self.assertEqual(len(core_descriptor.fields), 5)

    def test_headers_simplecases(self):
        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            descriptor = dwca.descriptor

            # With core file...
            expected_headers_core = ['id',
                                     'http://rs.tdwg.org/dwc/terms/order',
                                     'http://rs.tdwg.org/dwc/terms/class',
                                     'http://rs.tdwg.org/dwc/terms/kingdom',
                                     'http://rs.tdwg.org/dwc/terms/phylum',
                                     'http://rs.tdwg.org/dwc/terms/genus',
                                     'http://rs.tdwg.org/dwc/terms/family']

            self.assertEqual(descriptor.core.headers, expected_headers_core)

            # And with a first extension...
            expected_headers_description_ext = ['coreid',
                                                'http://purl.org/dc/terms/type',
                                                'http://purl.org/dc/terms/language',
                                                'http://purl.org/dc/terms/description']

            desc_ext_descriptor = next(d for d in dwca.descriptor.extensions
                                       if d.type == 'http://rs.gbif.org/terms/1.0/Description')

            self.assertEqual(desc_ext_descriptor.headers, expected_headers_description_ext)

            # And another one
            expected_headers_vernacular_ext = ['coreid',
                                               'http://rs.tdwg.org/dwc/terms/countryCode',
                                               'http://purl.org/dc/terms/language',
                                               'http://rs.tdwg.org/dwc/terms/vernacularName']

            vern_ext_descriptor = next(d for d in dwca.descriptor.extensions
                                       if d.type == 'http://rs.gbif.org/terms/1.0/VernacularName')

            self.assertEqual(vern_ext_descriptor.headers, expected_headers_vernacular_ext)

    def test_headers_defaultvalue(self):
        """ Ensure headers work properly when confronted to default values (w/o column in file)"""
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
            <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/locality"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))

        expected_headers_core = ['id',
                                 'http://rs.tdwg.org/dwc/terms/scientificName',
                                 'http://rs.tdwg.org/dwc/terms/basisOfRecord',
                                 'http://rs.tdwg.org/dwc/terms/family',
                                 'http://rs.tdwg.org/dwc/terms/locality']

        self.assertEqual(core_descriptor.headers, expected_headers_core)

    def test_short_headers(self):
        metaxml_section = """
                <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
                ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
                    <files>
                        <location>occurrence.txt</location>
                    </files>
                    <id index="0" />
                    <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
                    <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
                    <field index="2" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
                    <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
                    <field index="4" term="http://rs.tdwg.org/dwc/terms/locality"/>
                </core>
                """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))

        expected_short_headers_core = ['id', 'scientificName', 'basisOfRecord', 'family', 'locality']

        self.assertEqual(core_descriptor.short_headers, expected_short_headers_core)

    def test_headers_unordered(self):
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Taxon">
            <files>
                <location>taxon.txt</location>
            </files>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/phylum"/>
            <id index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/order"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/class"/>
            <field index="6" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/kingdom"/>
            <field index="5" term="http://rs.tdwg.org/dwc/terms/genus"/>
        </core>
        """
        core_descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))

        expected_headers_core = ['id',
                                 'http://rs.tdwg.org/dwc/terms/order',
                                 'http://rs.tdwg.org/dwc/terms/class',
                                 'http://rs.tdwg.org/dwc/terms/kingdom',
                                 'http://rs.tdwg.org/dwc/terms/phylum',
                                 'http://rs.tdwg.org/dwc/terms/genus',
                                 'http://rs.tdwg.org/dwc/terms/family']

        self.assertEqual(core_descriptor.headers, expected_headers_core)

    def test_exposes_raw_element_tag(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            self.assertIsInstance(dwca.descriptor.core.raw_element, ET.Element)

    def test_content_raw_element_tag(self):
        """ Test the content of raw_element seems decent. """
        ext_section = """
        <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n"
        fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/Description">
            <files><location>description.txt</location></files>
            <coreid index="0" />
            <field index="1" term="http://purl.org/dc/terms/type"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://purl.org/dc/terms/description"/>
        </extension>
        """

        ext_descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(ext_section))

        self.assertEqual(ext_descriptor.raw_element.tag, 'extension')
        self.assertEqual(ext_descriptor.raw_element.get('encoding'), 'utf-8')
        self.assertEqual(len(ext_descriptor.raw_element.findall('field')), 3)

    def test_tell_if_represents_core(self):
        # 1. Test with core
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            core_descriptor = dwca.descriptor.core
            self.assertTrue(core_descriptor.represents_corefile)
            self.assertFalse(core_descriptor.represents_extension)

        ext_section = """
        <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n"
        fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/Description">
            <files><location>description.txt</location></files>
            <coreid index="0" />
            <field index="1" term="http://purl.org/dc/terms/type"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://purl.org/dc/terms/description"/>
        </extension>
        """

        # 2. And with extension
        ext_descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(ext_section))
        self.assertFalse(ext_descriptor.represents_corefile)
        self.assertTrue(ext_descriptor.represents_extension)

    def test_exposes_coreid_index_of_extensions(self):
        ext_section = """
        <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/Description">
            <files><location>description.txt</location></files>
            <coreid index="0" />
            <field index="1" term="http://purl.org/dc/terms/type"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://purl.org/dc/terms/description"/>
        </extension>
        """

        ext_descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(ext_section))

        self.assertEqual(ext_descriptor.coreid_index, 0)

        # ... but it doesn't have .id_index (only for core!)
        self.assertIsNone(ext_descriptor.id_index)

    def test_exposes_id_index_of_core(self):
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
            <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/locality"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))

        self.assertEqual(core_descriptor.id_index, 0)

        # ... but it doesn't have .coreid_index (only for extensions!)
        self.assertIsNone(core_descriptor.coreid_index)

    def test_exposes_core_type(self):
        """Test that it exposes the Archive Core Type as type"""

        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            coredescriptor = dwca.descriptor.core
            # dwca-simple-test-archive.zip should be of Occurrence type
            self.assertEqual(coredescriptor.type, 'http://rs.tdwg.org/dwc/terms/Occurrence')
            # Check that shortcuts also work
            self.assertEqual(coredescriptor.type, qn('Occurrence'))

    def test_exposes_core_terms(self):
        with DwCAReader(EXTENSION_ARCHIVE_PATH) as star_dwca:
            # The Core file contains the following rows
            # <field index="1" term="http://rs.tdwg.org/dwc/terms/family"/>
            # <field index="2" term="http://rs.tdwg.org/dwc/terms/phylum"/>
            # <field index="3" term="http://rs.tdwg.org/dwc/terms/order"/>
            # <field index="4" term="http://rs.tdwg.org/dwc/terms/genus"/>
            # <field index="5" term="http://rs.tdwg.org/dwc/terms/kingdom"/>
            # <field index="6" term="http://rs.tdwg.org/dwc/terms/class"/>

            # It also contains an id column (should not appear here)
            # There's an extension with 3 fields, should not appear here.

            # Assert correct size
            descriptor = star_dwca.descriptor
            self.assertEqual(6, len(descriptor.core.terms))

            # Assert correct content (should be a set, so unordered)
            fields = set(['http://rs.tdwg.org/dwc/terms/kingdom',
                          'http://rs.tdwg.org/dwc/terms/order',
                          'http://rs.tdwg.org/dwc/terms/class',
                          'http://rs.tdwg.org/dwc/terms/genus',
                          'http://rs.tdwg.org/dwc/terms/family',
                          'http://rs.tdwg.org/dwc/terms/phylum'])

            self.assertEqual(fields, descriptor.core.terms)


class TestArchiveDescriptor(unittest.TestCase):
    """Unit tests for ArchiveDescriptor class."""

    def test_exposes_coredescriptor(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as basic_dwca:
            self.assertIsInstance(basic_dwca.descriptor.core, DataFileDescriptor)

    def test_exposes_extensions_2ext(self):
        all_metaxml = """
        <archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="eml.xml">
          <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Taxon">
            <files>
              <location>taxon.txt</location>
            </files>
            <id index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/order"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/class"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/kingdom"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/phylum"/>
            <field index="5" term="http://rs.tdwg.org/dwc/terms/genus"/>
            <field index="6" term="http://rs.tdwg.org/dwc/terms/family"/>
          </core>
          <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/Description">
            <files>
              <location>description.txt</location>
            </files>
            <coreid index="0" />
            <field index="1" term="http://purl.org/dc/terms/type"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://purl.org/dc/terms/description"/>
          </extension>
          <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/VernacularName">
            <files>
              <location>vernacularname.txt</location>
            </files>
            <coreid index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/countryCode"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/vernacularName"/>
          </extension>
        </archive>
        """

        d = ArchiveDescriptor(all_metaxml)
        expected_extensions_files = ('description.txt', 'vernacularname.txt')
        for ext in d.extensions:
            self.assertTrue(ext.file_location in expected_extensions_files)

        self.assertEqual(len(d.extensions), 2)

    # Test the files_to_ignore optional argument work as expected
    def test_exposes_extensions_2ext_ignore(self):
        all_metaxml = """
        <archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="eml.xml">
          <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Taxon">
            <files>
              <location>taxon.txt</location>
            </files>
            <id index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/order"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/class"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/kingdom"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/phylum"/>
            <field index="5" term="http://rs.tdwg.org/dwc/terms/genus"/>
            <field index="6" term="http://rs.tdwg.org/dwc/terms/family"/>
          </core>
          <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/Description">
            <files>
              <location>description.txt</location>
            </files>
            <coreid index="0" />
            <field index="1" term="http://purl.org/dc/terms/type"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://purl.org/dc/terms/description"/>
          </extension>
          <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/VernacularName">
            <files>
              <location>vernacularname.txt</location>
            </files>
            <coreid index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/countryCode"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/vernacularName"/>
          </extension>
        </archive>
        """

        d = ArchiveDescriptor(all_metaxml, files_to_ignore="description.txt")

        self.assertEqual(len(d.extensions), 1)
        self.assertEqual(d.extensions[0].file_location, 'vernacularname.txt')

    def test_exposes_extensions_none(self):
        all_metaxml = """
        <archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="eml.xml">
          <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
              <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/locality"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
          </core>
        </archive>
        """
        d = ArchiveDescriptor(all_metaxml)
        self.assertEqual(len(d.extensions), 0)

    def test_exposes_extensions_type(self):
        vn = 'http://rs.gbif.org/terms/1.0/VernacularName'
        td = 'http://rs.gbif.org/terms/1.0/Description'

        # This archive has no extension, we should get an empty list
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            descriptor = dwca.descriptor
            self.assertEqual([], descriptor.extensions_type)

        # This archive only contains the VernacularName extension
        with DwCAReader(EXTENSION_ARCHIVE_PATH) as dwca:
            descriptor = dwca.descriptor
            self.assertEqual(descriptor.extensions_type[0], vn)
            self.assertEqual(1, len(descriptor.extensions_type))

        # TODO: test with more complex archive
        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            descriptor = dwca.descriptor
            # 2 extensions are in use : vernacular names and taxon descriptions
            self.assertEqual(2, len(descriptor.extensions_type))
            # USe of frozenset to lose ordering
            supposed_extensions = frozenset([vn, td])
            self.assertEqual(supposed_extensions,
                             frozenset(descriptor.extensions_type))

    def test_exposes_metadata_filename(self):
        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            descriptor = dwca.descriptor

            self.assertEqual(descriptor.metadata_filename, "eml.xml")
