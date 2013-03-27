import unittest
import os

from ..dwca import DwCAReader
from ..dwterms import terms

class Test(unittest.TestCase):
    """Unit tests for python-dwca-reader."""

    SOURCE_PATH = os.path.join(os.path.dirname(__file__),
                           './sample_files/dwca-simple-test-archive.zip')

    def test_cleanup(self):
        """Test no temporary files are left after execution"""
        num_files_before = len(os.listdir('.'))

        with DwCAReader(self.SOURCE_PATH) as dwca:
            pass

        num_files_after = len(os.listdir('.'))    

        self.assertEqual(num_files_before, num_files_after)

    def test_temporary_folder(self):
        """Test a temporary folder is created during execution
        
        (complementay to test_cleanup()
        """

        num_files_before = len(os.listdir('.'))
        with DwCAReader(self.SOURCE_PATH) as dwca:
            num_files_during = len(os.listdir('.'))

        self.assertEqual(num_files_before, num_files_during-1)

    def test_core_type(self):
        """Test that the core_type returns the Archive Core Type"""

        with DwCAReader(self.SOURCE_PATH) as dwca:
            # dwca-simple-test-archive.zip should be of Occurrence type
            self.assertEqual(dwca.core_type, 'http://rs.tdwg.org/dwc/terms/Occurrence')
            # Check that shortcuts also work
            self.assertEqual(dwca.core_type, terms['OCCURRENCE'])


if __name__ == "__main__":
    unittest.main()