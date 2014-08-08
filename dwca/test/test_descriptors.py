# -*- coding: utf-8 -*-
import unittest

from bs4 import Tag, BeautifulSoup

from dwca.descriptors import SectionDescriptor, ArchiveDescriptor
from dwca.darwincore.utils import qualname as qn
from dwca.read import DwCAReader

from .helpers import (BASIC_ARCHIVE_PATH, EXTENSION_ARCHIVE_PATH,
                      MULTIEXTENSIONS_ARCHIVE_PATH)


class TestSectionDescriptor(unittest.TestCase):
    """Unit tests for SectionDescriptor class."""
    
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

        as_tag = BeautifulSoup(metaxml_section, 'xml').contents[0]
        core_descriptor = SectionDescriptor(as_tag)

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

        as_tag = BeautifulSoup(metaxml_section, 'xml').contents[0]
        core_descriptor = SectionDescriptor(as_tag)

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

        as_tag = BeautifulSoup(metaxml_section, 'xml').contents[0]
        core_descriptor = SectionDescriptor(as_tag)

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

        as_tag = BeautifulSoup(metaxml_section, 'xml').contents[0]
        core_descriptor = SectionDescriptor(as_tag)

        self.assertEqual(core_descriptor.file_location, "occurrence.txt")
        self.assertEqual(core_descriptor.encoding, "utf-8")
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

        as_tag = BeautifulSoup(metaxml_section, 'xml').contents[0]
        core_descriptor = SectionDescriptor(as_tag)

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

        as_tag = BeautifulSoup(metaxml_section, 'xml').contents[0]
        core_descriptor = SectionDescriptor(as_tag)

        expected_headers_core = ['id',
                                 'http://rs.tdwg.org/dwc/terms/scientificName',
                                 'http://rs.tdwg.org/dwc/terms/basisOfRecord',
                                 'http://rs.tdwg.org/dwc/terms/family',
                                 'http://rs.tdwg.org/dwc/terms/locality']

        self.assertEqual(core_descriptor.headers, expected_headers_core)

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
        as_tag = BeautifulSoup(metaxml_section, 'xml').contents[0]
        core_descriptor = SectionDescriptor(as_tag)

        expected_headers_core = ['id',
                                 'http://rs.tdwg.org/dwc/terms/order',
                                 'http://rs.tdwg.org/dwc/terms/class',
                                 'http://rs.tdwg.org/dwc/terms/kingdom',
                                 'http://rs.tdwg.org/dwc/terms/phylum',
                                 'http://rs.tdwg.org/dwc/terms/genus',
                                 'http://rs.tdwg.org/dwc/terms/family']

        self.assertEqual(core_descriptor.headers, expected_headers_core)

    def test_exposes_raw_beautifulsoup_tag(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            self.assertIsInstance(dwca.descriptor.core.raw_beautifulsoup, Tag)

    def test_content_raw_beautifulsoup_tag(self):
        """ Test the content ofraw_beautifulsoup seems decent. """
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

        as_tag = BeautifulSoup(ext_section, 'xml').contents[0]
        ext_descriptor = SectionDescriptor(as_tag)

        self.assertEqual(ext_descriptor.raw_beautifulsoup.name, 'extension')
        self.assertEqual(ext_descriptor.raw_beautifulsoup['encoding'], 'utf-8')
        self.assertEqual(len(ext_descriptor.raw_beautifulsoup.findAll('field')), 3)

    def test_tell_if_represents_core(self):
        # 1. Test with core
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            core_descriptor = dwca.descriptor.core
            self.assertTrue(core_descriptor.represents_corefile)
            self.assertFalse(core_descriptor.represents_extensionfile)

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
        as_tag = BeautifulSoup(ext_section, 'xml').contents[0]
        ext_descriptor = SectionDescriptor(as_tag)
        self.assertFalse(ext_descriptor.represents_corefile)
        self.assertTrue(ext_descriptor.represents_extensionfile)

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

        as_tag = BeautifulSoup(ext_section, 'xml').contents[0]
        ext_descriptor = SectionDescriptor(as_tag)

        self.assertEqual(ext_descriptor.coreid_index, 0)

        # ... but it doesn't have .id_index (only for core!)
        with self.assertRaises(AttributeError):
            ext_descriptor.id_index

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

        as_tag = BeautifulSoup(metaxml_section, 'xml').contents[0]
        core_descriptor = SectionDescriptor(as_tag)

        self.assertEqual(core_descriptor.id_index, 0)

        # ... but it doesn't have .coreid_index (only for extensions!)
        with self.assertRaises(AttributeError):
            core_descriptor.coreid_index

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
            fields = set([u'http://rs.tdwg.org/dwc/terms/kingdom',
                         u'http://rs.tdwg.org/dwc/terms/order',
                         u'http://rs.tdwg.org/dwc/terms/class',
                         u'http://rs.tdwg.org/dwc/terms/genus',
                         u'http://rs.tdwg.org/dwc/terms/family',
                         u'http://rs.tdwg.org/dwc/terms/phylum'])

            self.assertEqual(fields, descriptor.core.terms)


class TestArchiveDescriptor(unittest.TestCase):
    """Unit tests for ArchiveDescriptor class."""

    def test_exposes_coredescriptor(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as basic_dwca:
            self.assertIsInstance(basic_dwca.descriptor.core, SectionDescriptor)

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

    def test_exposes_raw_beautifulsoup(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as basic_dwca:
            descriptor = basic_dwca.descriptor

            # Test that it exposes a 'raw_beautifulsoup' attribute w/ decent content
            self.assertIsInstance(descriptor.raw_beautifulsoup, BeautifulSoup)
            self.assertEqual(descriptor.raw_beautifulsoup.archive["metadata"], 'eml.xml')

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
