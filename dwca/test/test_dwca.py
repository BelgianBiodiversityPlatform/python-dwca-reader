import unittest
import os

from BeautifulSoup import BeautifulStoneSoup

from ..dwca import DwCAReader
from ..dwterms import terms


# Helpers
def _sample_data_path(filename):
    return os.path.join(os.path.dirname(__file__), 'sample_files', filename)


class Test(unittest.TestCase):
    """Unit tests for python-dwca-reader."""

    BASIC_ARCHIVE_PATH = _sample_data_path('dwca-simple-test-archive.zip')
    NOHEADERS1_PATH = _sample_data_path('dwca-noheaders-1.zip')
    NOHEADERS2_PATH = _sample_data_path('dwca-noheaders-2.zip')

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
            self.assertEqual(dwca.core_type, terms['OCCURRENCE'])

    def test_metadata(self):
        """A few basic tests on the metadata attribute

        TODO: split
        """

        with DwCAReader(self.BASIC_ARCHIVE_PATH) as dwca:
            # Assert metadata is an instance of BeautifulStoneSoup
            self.assertIsInstance(dwca.metadata, BeautifulStoneSoup)

            # Assert we can read basic fields from EML:
            self.assertEqual(dwca.metadata.dataset.creator.individualname.givenname.contents[0],
                            'Nicolas')

    def test_core_contains_term(self):
        """Test the core_contains_term method."""

        # Example file contains locality but no country
        with DwCAReader(self.BASIC_ARCHIVE_PATH) as dwca:
            self.assertTrue(dwca.core_contains_term(terms['LOCALITY']))
            self.assertFalse(dwca.core_contains_term(terms['COUNTRY']))

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

if __name__ == "__main__":
    unittest.main()
