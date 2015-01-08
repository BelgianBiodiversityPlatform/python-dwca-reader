# -*- coding: utf-8 -*-

import unittest
import os
import tempfile

from zipfile import BadZipfile
from bs4 import BeautifulSoup

from dwca.read import DwCAReader, GBIFResultsReader
from dwca.rows import CoreRow, ExtensionRow
from dwca.darwincore.utils import qualname as qn
from dwca.exceptions import RowNotFound
from dwca.descriptors import ArchiveDescriptor

from .helpers import (GBIF_RESULTS_PATH, BASIC_ARCHIVE_PATH, EXTENSION_ARCHIVE_PATH,
                      MULTIEXTENSIONS_ARCHIVE_PATH, NOHEADERS1_PATH, NOHEADERS2_PATH,
                      IDS_ARCHIVE_PATH, DEFAULT_VAL_PATH, UTF8EOL_ARCHIVE_PATH,
                      DIRECTORY_ARCHIVE_PATH, DEFAULT_META_VALUES)


class TestDwCAReader(unittest.TestCase):
    # TODO: Move row-oriented tests to another test class
    """Unit tests for DwCAReader class."""

    def test_default_values_metafile(self):
        """Ensure default values are used when optional attributes are absent in metafile.

        Optional attributes tested here: linesTerminatedBy, fieldsTerminatedBy."""
        with DwCAReader(DEFAULT_META_VALUES) as dwca:
            # Test iterating on rows...
            for row in dwca:
                self.assertIsInstance(row, CoreRow)

            # And verify the values themselves:

    def test_unzipped_archive(self):
        """Ensure it works with non-zipped (directory) archives."""
        with DwCAReader(DIRECTORY_ARCHIVE_PATH) as dwca:
            # See metadata access works...
            self.assertIsInstance(dwca.metadata, BeautifulSoup)

            # And iterating...
            for row in dwca:
                self.assertIsInstance(row, CoreRow)

    def test_classic_opening(self):
        """Ensure it also works w/o the 'with' statement."""
        dwca = DwCAReader(BASIC_ARCHIVE_PATH)
        self.assertIsInstance(dwca.metadata, BeautifulSoup)
        dwca.close()

    def test_descriptor(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as basic_dwca:
            self.assertIsInstance(basic_dwca.descriptor, ArchiveDescriptor)

    def test_row_human_representation(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as basic_dwca:
            l = basic_dwca.rows[0]
            l_repr = str(l)
            self.assertIn("Rowtype: http://rs.tdwg.org/dwc/terms/Occurrence", l_repr)
            self.assertIn("Source: Core file", l_repr)
            self.assertIn("Row id:", l_repr)
            self.assertIn("Reference extension rows: No", l_repr)
            self.assertIn("Reference source metadata: No", l_repr)
            self.assertIn("http://rs.tdwg.org/dwc/terms/scientificName': u'tetraodon fluviatilis'",
                          l_repr)

        with DwCAReader(EXTENSION_ARCHIVE_PATH) as star_dwca:
            l = star_dwca.rows[0]
            l_repr = str(l)
            self.assertIn("Rowtype: http://rs.tdwg.org/dwc/terms/Taxon", l_repr)
            self.assertIn("Source: Core file", l_repr)
            self.assertIn("Row id: 1", l_repr)
            self.assertIn("Reference extension rows: Yes", l_repr)
            self.assertIn("Reference source metadata: No", l_repr)

            extension_l_repr = str(l.extensions[0])
            self.assertIn("Rowtype: http://rs.gbif.org/terms/1.0/VernacularName", extension_l_repr)
            self.assertIn("Source: Extension file", extension_l_repr)
            self.assertIn("Core row id: 1", extension_l_repr)
            self.assertIn("ostrich", extension_l_repr)
            self.assertIn("Reference extension rows: No", extension_l_repr)
            self.assertIn("Reference source metadata: No", extension_l_repr)

        with GBIFResultsReader(GBIF_RESULTS_PATH) as gbif_dwca:
            l = gbif_dwca.rows[0]
            l_repr = str(l)

            self.assertIn("Rowtype: http://rs.tdwg.org/dwc/terms/Occurrence", l_repr)
            self.assertIn("Source: Core file", l_repr)
            self.assertIn("Reference source metadata: Yes", l_repr)

    def test_absolute_temporary_path(self):
        """Test the absolute_temporary_path() method."""
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            path_to_occ = dwca.absolute_temporary_path('occurrence.txt')
            
            # Is it absolute ?
            self.assertTrue(os.path.isabs(path_to_occ))
            # Does file exists ?
            self.assertTrue(os.path.isfile(path_to_occ))
            # IS it the correct content ?
            f = open(path_to_occ)
            content = f.read()
            self.assertTrue(content.startswith("id"))

        with DwCAReader(DIRECTORY_ARCHIVE_PATH) as dwca:
            # Also check if the archive is a directory
            path_to_occ = dwca.absolute_temporary_path('occurrence.txt')
            
            # Is it absolute ?
            self.assertTrue(os.path.isabs(path_to_occ))
            # Does file exists ?
            self.assertTrue(os.path.isfile(path_to_occ))
            # IS it the correct content ?
            f = open(path_to_occ)
            content = f.read()
            self.assertTrue(content.startswith("id"))

    def test_auto_cleanup_zipped(self):
        """Test no temporary files are left after execution (using 'with' statement)."""
        num_files_before = len(os.listdir('.'))

        with DwCAReader(BASIC_ARCHIVE_PATH):
            pass

        num_files_after = len(os.listdir('.'))

        self.assertEqual(num_files_before, num_files_after)

    def test_auto_cleanup_directory(self):
        """If the source is already a directory, there's nothing to create nor cleanup."""

        num_files_before = len(os.listdir('.'))

        with DwCAReader(DIRECTORY_ARCHIVE_PATH):
            pass

        num_files_after = len(os.listdir('.'))
        self.assertEqual(num_files_before, num_files_after)

    def test_manual_cleanup_zipped(self):
        """Test no temporary files are left after execution (calling close() manually)."""

        num_files_before = len(os.listdir('.'))

        r = DwCAReader(BASIC_ARCHIVE_PATH)
        r.close()

        num_files_after = len(os.listdir('.'))

        self.assertEqual(num_files_before, num_files_after)

    def test_source_data_not_destroyed_directory(self):
        """In archive=directory, it should not be destroyed after use.

        (check that the cleanup routine for zipped file is not accidentaly called)
        """

        r = DwCAReader(DIRECTORY_ARCHIVE_PATH)
        r.close()

        # If previously destroyed, this will fail...
        r = DwCAReader(DIRECTORY_ARCHIVE_PATH)
        self.assertIsInstance(r.metadata, BeautifulSoup)
        r.close()

    def test_temporary_folder_zipped(self):
        """Test a temporary folder is created during execution

        (complementay to test_cleanup()
        """

        num_files_before = len(os.listdir('.'))
        with DwCAReader(BASIC_ARCHIVE_PATH):
            num_files_during = len(os.listdir('.'))

        self.assertEqual(num_files_before, num_files_during - 1)

    def test_no_temporary_folder_directory(self):
        """If archive is a directory, no need to create temporary files."""
        num_files_before = len(os.listdir('.'))
        with DwCAReader(DIRECTORY_ARCHIVE_PATH):
            num_files_during = len(os.listdir('.'))

        self.assertEqual(num_files_before, num_files_during)

    def test_metadata(self):
        """A few basic tests on the metadata attribute

        TODO: split
        """

        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            # Assert metadata is an instance of BeautifulSoup
            self.assertIsInstance(dwca.metadata, BeautifulSoup)

            # Assert we can read basic fields from EML:
            self.assertEqual(dwca.metadata.dataset.creator.
                             individualName.givenName.contents[0],
                             'Nicolas')

    def test_core_contains_term(self):
        """Test the core_contains_term method."""

        # Example file contains locality but no country
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            self.assertTrue(dwca.core_contains_term(qn('locality')))
            self.assertFalse(dwca.core_contains_term(qn('country')))

    def test_ignore_header_lines(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            # The sample file has two real rows + 1 header line
            self.assertEqual(2, len([l for l in dwca]))

        with DwCAReader(NOHEADERS1_PATH) as dwca:
            # This file has two real rows, without headers
            # (specified in meta.xml)
            self.assertEqual(2, len([l for l in dwca]))

        with DwCAReader(NOHEADERS2_PATH) as dwca:
            # This file has two real rows, without headers
            # (nothing specified in meta.xml)
            self.assertEqual(2, len([l for l in dwca]))

    def test_iterate_rows(self):
        """Test the iterating over CoreRow(s)"""
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            for row in dwca:
                self.assertIsInstance(row, CoreRow)

    def test_iterate_order(self):
        """Test that the order of appaearance in Core file is respected when iterating."""
        # This is also probably tested inderectly elsewhere, but this is the right place :)
        with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
            l = list(dwca)
            # Row IDs are ordered like this in core file: id 4-1-3-2
            self.assertEqual(int(l[0].id), 4)
            self.assertEqual(int(l[1].id), 1)
            self.assertEqual(int(l[2].id), 3)
            self.assertEqual(int(l[3].id), 2)

    def test_iterate_multiple_calls(self):
        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            self.assertEqual(4, len([l for l in dwca]))
            # The second time, we can still find 4 rows...
            self.assertEqual(4, len([l for l in dwca]))

    def test_get_row_by_index(self):
        """Test the get_row_by_index() method work as expected"""
        with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
            # Row IDs are ordered like this in core: id 4-1-3-2
            first_row = dwca.get_row_by_index(0)
            self.assertEqual(4, int(first_row.id))

            last_row = dwca.get_row_by_index(3)
            self.assertEqual(2, int(last_row.id))

            # Exception raised if bigger than archive (last index: 3)
            with self.assertRaises(RowNotFound):
                dwca.get_row_by_index(4)

            with self.assertRaises(RowNotFound):
                dwca.get_row_by_index(1000)

    def test_get_row_by_id_string(self):
        genus_qn = 'http://rs.tdwg.org/dwc/terms/genus'

        with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
            # Number can be passed as a string....
            r = dwca.get_row_by_id('3')
            self.assertEqual('Peliperdix', r.data[genus_qn])

    def test_get_row_by_id_multiple_calls(self):
        genus_qn = 'http://rs.tdwg.org/dwc/terms/genus'

        with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
            r = dwca.get_row_by_id('3')
            self.assertEqual('Peliperdix', r.data[genus_qn])

            # If iterator is not properly reset, None will be returned
            # the second time
            r = dwca.get_row_by_id('3')
            self.assertEqual('Peliperdix', r.data[genus_qn])

    def test_get_row_by_id_other(self):
        genus_qn = 'http://rs.tdwg.org/dwc/terms/genus'

        with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
            # Passed as an integer, conversion will be tried...
            r = dwca.get_row_by_id(3)
            self.assertEqual('Peliperdix', r.data[genus_qn])

    def test_get_inexistent_row(self):
        """ Ensure get_row_by_id() raises RowNotFound if we ask it an unexistent row. """
        with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
            with self.assertRaises(RowNotFound):
                dwca.get_row_by_id(8000)

    def test_read_core_value(self):
        """Retrieve a simple value from core file"""
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            rows = list(dwca)

            # Check basic locality values from sample file
            self.assertEqual('Borneo', rows[0].data[qn('locality')])
            self.assertEqual('Mumbai', rows[1].data[qn('locality')])

    def test_read_core_value_default(self):
        """Retrieve a (default) value from core

        Test similar to test_read_core_value(), but the retrieved data
        comes from a default value (in meta.xml) instead of from the core
        text file. This is part of the standard and was produced by IPT
        prior to version 2.0.3.
        """
        with DwCAReader(DEFAULT_VAL_PATH) as dwca:
            for l in dwca:
                self.assertEqual('Belgium', l.data[qn('country')])

    def test_qn(self):
        """Test the qn (shortcut generator) helper"""

        # Test success
        self.assertEqual("http://rs.tdwg.org/dwc/terms/Occurrence",
                         qn("Occurrence"))

        # Test failure
        with self.assertRaises(StopIteration):
            qn('dsfsdfsdfsdfsdfsd')

    def test_no_cr_left(self):
        """Test no carriage return characters are left at end of line."""

        # We know we have no \n in our test archive, so if we fine one
        # it's probably a character that was left by error when parsing
        # line
        with DwCAReader(BASIC_ARCHIVE_PATH) as simple_dwca:
            for l in simple_dwca:
                for k, v in l.data.iteritems():
                    self.assertFalse(v.endswith("\n"))

    def test_correct_extension_rows_per_core_row(self):
        """Test we have the correct number of extensions rows."""

        # This one has no extension, so row.extensions should be an empty list
        with DwCAReader(BASIC_ARCHIVE_PATH) as simple_dwca:
            for r in simple_dwca:
                self.assertEqual(0, len(r.extensions))

        with DwCAReader(EXTENSION_ARCHIVE_PATH) as star_dwca:
            rows = list(star_dwca)

            # 3 vernacular names are given for Struthio Camelus...
            self.assertEqual(3, len(rows[0].extensions))
            # ... 1 vernacular name for Alectoris chukar ...
            self.assertEqual(1, len(rows[1].extensions))
            # ... and none for the last two rows
            self.assertEqual(0, len(rows[2].extensions))
            self.assertEqual(0, len(rows[3].extensions))

        # TODO: test the same thing with 2 different extensions reffering to the row
        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH) as multi_dwca:
            rows = list(multi_dwca)

            # 3 vernacular names + 2 taxon descriptions
            self.assertEqual(5, len(rows[0].extensions))
            # 1 Vernacular name, no taxon description
            self.assertEqual(1, len(rows[1].extensions))
            # No extensions for this core line
            self.assertEqual(0, len(rows[2].extensions))
            # No vernacular name, 1 taxon description

    def test_row_rowtype(self):
        """Test the rowtype attribute of rows (for Core and extensions)."""

        with DwCAReader(EXTENSION_ARCHIVE_PATH) as star_dwca:
            taxon_qn = "http://rs.tdwg.org/dwc/terms/Taxon"
            vernacular_qn = "http://rs.gbif.org/terms/1.0/VernacularName"

            for i, row in enumerate(star_dwca):
                # All ine instance accessed here are core:
                self.assertEqual(taxon_qn, row.rowtype)

                if i == 0:
                    # First row has an extension, and only vn are in use
                    self.assertEqual(vernacular_qn, row.extensions[0].rowtype)

    def test_row_class(self):
        with DwCAReader(EXTENSION_ARCHIVE_PATH) as star_dwca:
            for row in star_dwca:
                self.assertIsInstance(row, CoreRow)

                # But the extensions are... extensions (hum)
                for an_extension in row.extensions:
                    self.assertIsInstance(an_extension, ExtensionRow)

    # TODO: Also test we return an empty list on empty archive
    def test_rows_property(self):
        """Test that DwCAReader expose a list of all core rows in 'rows'

        The content of this 'rows' property is equivalent to iterating and
        storing result in a list.
        """
        with DwCAReader(EXTENSION_ARCHIVE_PATH) as star_dwca:
            by_iteration = []
            for r in star_dwca:
                by_iteration.append(r)

            self.assertEqual(by_iteration, star_dwca.rows)

    # TODO: Add more test to ensure that the specified EOL sequence
    # (and ONLY this sequence!) is used to split lines.

    # Code should be already fine, but tests lacking
    def test_utf8_eol_ignored(self):
        """Ensure we don't split lines based on the x85 utf8 EOL char.

        (only the EOL string specified in meta.xml should be used).
         """

        with DwCAReader(UTF8EOL_ARCHIVE_PATH) as dwca:
            rows = dwca.rows
            # If line properly splitted => 64 rows.
            # (61 - and probably an IndexError - if errrors)
            self.assertEqual(64, len(rows[0].data))

    def test_row_source_metadata(self):
        # For normal DwC-A, it should always be none (NO source data
        # available in archive.)
        with DwCAReader(EXTENSION_ARCHIVE_PATH) as star_dwca:
            self.assertEqual(None, star_dwca.rows[0].source_metadata)

    def test_not_zipfile(self):
        """ Ensure BadZipfile is raised when passed archive is not a zip file."""
        invalid_origin_file = tempfile.NamedTemporaryFile()

        with self.assertRaises(BadZipfile):
            with DwCAReader(invalid_origin_file.name):
                pass


if __name__ == "__main__":
    unittest.main()
