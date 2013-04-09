import unittest
import os

from BeautifulSoup import BeautifulStoneSoup

from ..dwca import DwCAReader, DwCALine
from ..darwincore import qualname as qn


# Helpers
def _sample_data_path(filename):
    return os.path.join(os.path.dirname(__file__), 'sample_files', filename)


class Test(unittest.TestCase):
    """Unit tests for python-dwca-reader."""

    BASIC_ARCHIVE_PATH = _sample_data_path('dwca-simple-test-archive.zip')
    NOHEADERS1_PATH = _sample_data_path('dwca-noheaders-1.zip')
    NOHEADERS2_PATH = _sample_data_path('dwca-noheaders-2.zip')
    DEFAULT_VAL_PATH = _sample_data_path('dwca-test-default.zip')
    EXTENSION_ARCHIVE_PATH = _sample_data_path('dwca-star-test-archive.zip')

    def test_cleanup(self):
        """Test no temporary files are left after execution"""
        num_files_before = len(os.listdir('.'))

        with DwCAReader(self.BASIC_ARCHIVE_PATH):
            pass

        num_files_after = len(os.listdir('.'))

        self.assertEqual(num_files_before, num_files_after)

    def test_temporary_folder(self):
        """Test a temporary folder is created during execution

        (complementay to test_cleanup()
        """

        num_files_before = len(os.listdir('.'))
        with DwCAReader(self.BASIC_ARCHIVE_PATH):
            num_files_during = len(os.listdir('.'))

        self.assertEqual(num_files_before, num_files_during-1)

    def test_core_type(self):
        """Test that the core_type returns the Archive Core Type"""

        with DwCAReader(self.BASIC_ARCHIVE_PATH) as dwca:
            # dwca-simple-test-archive.zip should be of Occurrence type
            self.assertEqual(dwca.core_type,
                             'http://rs.tdwg.org/dwc/terms/Occurrence')
            # Check that shortcuts also work
            self.assertEqual(dwca.core_type, qn('Occurrence'))

    def test_metadata(self):
        """A few basic tests on the metadata attribute

        TODO: split
        """

        with DwCAReader(self.BASIC_ARCHIVE_PATH) as dwca:
            # Assert metadata is an instance of BeautifulStoneSoup
            self.assertIsInstance(dwca.metadata, BeautifulStoneSoup)

            # Assert we can read basic fields from EML:
            self.assertEqual(dwca.metadata.dataset.creator.
                             individualname.givenname.contents[0],
                             'Nicolas')

    def test_core_contains_term(self):
        """Test the core_contains_term method."""

        # Example file contains locality but no country
        with DwCAReader(self.BASIC_ARCHIVE_PATH) as dwca:
            self.assertTrue(dwca.core_contains_term(qn('locality')))
            self.assertFalse(dwca.core_contains_term(qn('country')))

    def test_ignore_header_lines(self):
        with DwCAReader(self.BASIC_ARCHIVE_PATH) as dwca:
            # The sample file has two real lines + 1 header file
            self.assertEqual(2, len([l for l in dwca.each_line()]))

        with DwCAReader(self.NOHEADERS1_PATH) as dwca:
            # This file has two real lines, without headers
            # (specified in meta.xml)
            self.assertEqual(2, len([l for l in dwca.each_line()]))

        with DwCAReader(self.NOHEADERS2_PATH) as dwca:
            # This file has two real lines, without headers
            # (nothing specified in meta.xml)
            self.assertEqual(2, len([l for l in dwca.each_line()]))

    def test_iterate_dwcalines(self):
        """Test the each_line() method allows iterating over DwCALines"""
        with DwCAReader(self.BASIC_ARCHIVE_PATH) as dwca:
            for line in dwca.each_line():
                self.assertIsInstance(line, DwCALine)

    def test_read_core_value(self):
        """Retrieve a simple value from core file"""
        with DwCAReader(self.BASIC_ARCHIVE_PATH) as dwca:
            lines = list(dwca.each_line())

            # Check basic locality values from sample file
            self.assertEqual('Borneo', lines[0].get(qn('locality')))
            self.assertEqual('Mumbai', lines[1].get(qn('locality')))

    def test_read_core_value_default(self):
        """Retrieve a (default) value from core

        Test similar to test_read_core_value(), but the retrieved data
        comes from a default value (in meta.xml) instead of from the core
        text file. This is part of the standard and was produced by IPT
        prior to version 2.0.3.
        """
        with DwCAReader(self.DEFAULT_VAL_PATH) as dwca:
            for l in dwca.each_line():
                self.assertEqual('Belgium', l.get(qn('country')))

    def test_qn(self):
        """Test the qn (shortcut generator) helper"""

        # Test success
        self.assertEqual("http://rs.tdwg.org/dwc/terms/Occurrence",
                         qn("Occurrence"))

        # Test failure
        with self.assertRaises(StopIteration):
            qn('dsfsdfsdfsdfsdfsd')

    # Testing of DwcA extension features
    def test_correct_extension_lines_per_core_line(self):
        """Test we have correct number of extensions l. per core line"""

        # This one has no extension, so line.extensions should be an empty list
        with DwCAReader(self.BASIC_ARCHIVE_PATH) as simple_dwca:
            for l in simple_dwca.each_line():
                self.assertEqual(0, len(l.extensions))

        with DwCAReader(self.EXTENSION_ARCHIVE_PATH) as star_dwca:
            lines = list(star_dwca.each_line())

            # 3 vernacular names are given for Struthio Camelus...
            self.assertEqual(3, len(lines[0].extensions))
            # ... 1 vernacular name for Alectoris chukar ...
            self.assertEqual(1, len(lines[1].extensions))
            # ... and none for the last two lines
            self.assertEqual(0, len(lines[2].extensions))
            self.assertEqual(0, len(lines[3].extensions))

        # TODO: test the same thing with 2 different extensions reffering to
        # the line

    def test_line_knows_its_source(self):
        with DwCAReader(self.EXTENSION_ARCHIVE_PATH) as star_dwca:
            for line in star_dwca.each_line():
                # These first DwCALines we access comes from the Core file
                self.assertTrue(line.from_core())
                self.assertFalse(line.from_extension())

                # But the extensions are... extensions (hum)
                for an_extension in line.extensions:
                    self.assertFalse(an_extension.from_core())
                    self.assertTrue(an_extension.from_extension())


if __name__ == "__main__":
    unittest.main()
