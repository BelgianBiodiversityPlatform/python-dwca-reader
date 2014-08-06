# -*- coding: utf-8 -*-
import unittest

from bs4 import Tag, BeautifulSoup

from dwca.descriptors import _CoreDescriptor
from dwca.darwincore.utils import qualname as qn
from dwca.read import DwCAReader

from .helpers import (BASIC_ARCHIVE_PATH, EXTENSION_ARCHIVE_PATH,
                      MULTIEXTENSIONS_ARCHIVE_PATH)


class TestCoreDescriptor(unittest.TestCase):
    """Unit tests for _CoreDescriptor class."""

    def test_exposes_raw_beautifulsoup_tag(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            self.assertIsInstance(dwca.descriptor.core.raw_beautifulsoup, Tag)

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
            # The Core file contains tjhe following rows
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
    """Unit tests for _ArchiveDescriptor class."""

    def test_exposes_coredescriptor(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as basic_dwca:
            self.assertIsInstance(basic_dwca.descriptor.core, _CoreDescriptor)

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
