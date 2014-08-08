# -*- coding: utf-8 -*-
import unittest

from bs4 import Tag, BeautifulSoup

from dwca.descriptors import SectionDescriptor
from dwca.darwincore.utils import qualname as qn
from dwca.read import DwCAReader

from .helpers import (BASIC_ARCHIVE_PATH, EXTENSION_ARCHIVE_PATH,
                      MULTIEXTENSIONS_ARCHIVE_PATH)


class TestSectionDescriptor(unittest.TestCase):
    """Unit tests for SectionDescriptor class."""

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

    def test_tell_if_represents_core(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            core_descriptor = dwca.descriptor.core
            self.assertTrue(core_descriptor.represents_corefile)
            self.assertFalse(core_descriptor.represents_extensionfile)

            # TODO: Same thing with an extension

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


class TestDescriptor(unittest.TestCase):
    """Unit tests for ArchiveDescriptor class."""

    def test_exposes_coredescriptor(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as basic_dwca:
            self.assertIsInstance(basic_dwca.descriptor.core, SectionDescriptor)

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
