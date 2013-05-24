import unittest
import os

from BeautifulSoup import BeautifulStoneSoup

from ..dwca import DwCAReader, DwCALine
from ..darwincore.utils import qualname as qn


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
    MULTIEXTENSIONS_ARCHIVE_PATH = _sample_data_path('dwca-2extensions.zip')

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

    def test_core_rowtype(self):
        """Test that the core_rowtype property returns the Archive Core Type"""

        with DwCAReader(self.BASIC_ARCHIVE_PATH) as dwca:
            # dwca-simple-test-archive.zip should be of Occurrence type
            self.assertEqual(dwca.core_rowtype,
                             'http://rs.tdwg.org/dwc/terms/Occurrence')
            # Check that shortcuts also work
            self.assertEqual(dwca.core_rowtype, qn('Occurrence'))

    def test_extensions_rowtype(self):
        vn = 'http://rs.gbif.org/terms/1.0/VernacularName'
        td = 'http://rs.gbif.org/terms/1.0/Description'

        # This archive has no extension, we should get an empty list
        with DwCAReader(self.BASIC_ARCHIVE_PATH) as dwca:
            self.assertEqual([], dwca.extensions_rowtype)

        # This archive only contains the VernacularName extension
        with DwCAReader(self.EXTENSION_ARCHIVE_PATH) as dwca:
            self.assertEqual(dwca.extensions_rowtype[0], vn)
            self.assertEqual(1, len(dwca.extensions_rowtype))

        # TODO: test with more complex archive
        with DwCAReader(self.MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            # 2 extensions are in use : vernacular names and taxon descriptions
            self.assertEqual(2, len(dwca.extensions_rowtype))
            # USe of frozenset to lose ordering
            supposed_extensions = frozenset([vn, td])
            self.assertEqual(supposed_extensions,
                             frozenset(dwca.extensions_rowtype))

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

    def test_iterate_multiple_calls(self):
        with DwCAReader(self.MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            self.assertEqual(4, len([l for l in dwca.each_line()]))
            # The second time, we can still find 4 lines...
            self.assertEqual(4, len([l for l in dwca.each_line()]))

    def test_get_line_by_id_string(self):
        genus_qn = 'http://rs.tdwg.org/dwc/terms/genus'

        with DwCAReader(self.MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            # Number can be passed as a string....
            l = dwca.get_line('3')
            self.assertEqual('Peliperdix', l.data[genus_qn])

    def test_get_line_by_id_multiple_calls(self):
        genus_qn = 'http://rs.tdwg.org/dwc/terms/genus'

        with DwCAReader(self.MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            l = dwca.get_line('3')
            self.assertEqual('Peliperdix', l.data[genus_qn])

            # If iterator is not properly reset, None will be returned
            # the second time
            l = dwca.get_line('3')
            self.assertEqual('Peliperdix', l.data[genus_qn])

    def test_get_line_by_id_other(self):
        genus_qn = 'http://rs.tdwg.org/dwc/terms/genus'

        with DwCAReader(self.MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            # .Passed as an integer, conversion will be tried...
            l = dwca.get_line(3)
            self.assertEqual('Peliperdix', l.data[genus_qn])

    def test_get_inexistent_line(self):
        """ Ensure get_line() returns None if we ask it an unexistent line. """
        with DwCAReader(self.MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            self.assertEqual(None, dwca.get_line(8000))

    def test_read_core_value(self):
        """Retrieve a simple value from core file"""
        with DwCAReader(self.BASIC_ARCHIVE_PATH) as dwca:
            lines = list(dwca.each_line())

            # Check basic locality values from sample file
            self.assertEqual('Borneo', lines[0].data[qn('locality')])
            self.assertEqual('Mumbai', lines[1].data[qn('locality')])

    def test_read_core_value_default(self):
        """Retrieve a (default) value from core

        Test similar to test_read_core_value(), but the retrieved data
        comes from a default value (in meta.xml) instead of from the core
        text file. This is part of the standard and was produced by IPT
        prior to version 2.0.3.
        """
        with DwCAReader(self.DEFAULT_VAL_PATH) as dwca:
            for l in dwca.each_line():
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
        """Test no carriage return characters are left at end of line"""

        # We know we have no \n in our test archive, so if we fine one
        # It's probably a character that was left by error when parsin
        # line
        with DwCAReader(self.BASIC_ARCHIVE_PATH) as simple_dwca:
            for l in simple_dwca.each_line():
                for k, v in l.data.iteritems():
                    self.assertFalse(v.endswith("\n"))

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
        with DwCAReader(self.MULTIEXTENSIONS_ARCHIVE_PATH) as multi_dwca:
            lines = list(multi_dwca.each_line())

            # 3 vernacular names + 2 taxon descriptions
            self.assertEqual(5, len(lines[0].extensions))
            # 1 Vernacular name, no taxon description
            self.assertEqual(1, len(lines[1].extensions))
            # No extensions for this core line
            self.assertEqual(0, len(lines[2].extensions))
            # No vernacular name, 1 taxon description

    def test_line_rowtype(self):
        """Test the rowtype attribute of DwCALine

        (on core and extension lines)
        """

        with DwCAReader(self.EXTENSION_ARCHIVE_PATH) as star_dwca:
            taxon_qn = "http://rs.tdwg.org/dwc/terms/Taxon"
            vernacular_qn = "http://rs.gbif.org/terms/1.0/VernacularName"

            for i, line in enumerate(star_dwca.each_line()):
                # All ine instance accessed here are core:
                self.assertEqual(taxon_qn, line.rowtype)

                if i == 0:
                    # First line has an extension, and only vn are in use
                    self.assertEqual(vernacular_qn, line.extensions[0].rowtype)

    def test_line_knows_its_source(self):
        with DwCAReader(self.EXTENSION_ARCHIVE_PATH) as star_dwca:
            for line in star_dwca.each_line():
                # These first DwCALines we access comes from the Core file
                self.assertTrue(line.from_core)
                self.assertFalse(line.from_extension)

                # But the extensions are... extensions (hum)
                for an_extension in line.extensions:
                    self.assertFalse(an_extension.from_core)
                    self.assertTrue(an_extension.from_extension)

    # TODO: Also test we return an empty list on empty archive
    def test_lines_property(self):
        """Test that DwCAReader expose a list of all core lines in 'lines'

        The content of this 'lines' property is equivalent to iterating and
        storing result in a list.
        """
        with DwCAReader(self.EXTENSION_ARCHIVE_PATH) as star_dwca:
            by_iteration = []
            for l in star_dwca.each_line():
                by_iteration.append(l)

            self.assertEqual(by_iteration, star_dwca.lines)



if __name__ == "__main__":
    unittest.main()
