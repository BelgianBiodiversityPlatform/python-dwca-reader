# -*- coding: utf-8 -*-

import sys
import unittest
import os
import tempfile
import warnings

import xml.etree.ElementTree as ET

from mock import patch

import pandas as pd

from dwca.read import DwCAReader, GBIFResultsReader
from dwca.rows import CoreRow, ExtensionRow
from dwca.darwincore.utils import qualname as qn
from dwca.exceptions import RowNotFound, InvalidArchive, NotADataFile
from dwca.descriptors import ArchiveDescriptor, DataFileDescriptor

from .helpers import (GBIF_RESULTS_PATH, BASIC_ARCHIVE_PATH, EXTENSION_ARCHIVE_PATH,
                      MULTIEXTENSIONS_ARCHIVE_PATH, NOHEADERS1_PATH, NOHEADERS2_PATH,
                      IDS_ARCHIVE_PATH, DEFAULT_VAL_PATH, UTF8EOL_ARCHIVE_PATH,
                      DIRECTORY_ARCHIVE_PATH, DIRECTORY_CSV_QUOTE_ARCHIVE_PATH, DEFAULT_META_VALUES,
                      INVALID_LACKS_METADATA, SUBDIR_ARCHIVE_PATH, SIMPLE_CSV, SIMPLE_CSV_EML,
                      SIMPLE_CSV_DOS, BASIC_ENCLOSED_ARCHIVE_PATH, INVALID_SIMPLE_TOOMUCH,
                      INVALID_SIMPLE_TWO, SIMPLE_CSV_NOTENCLOSED, NOMETADATA_PATH,
                      DEFAULT_METADATA_FILENAME, BASIC_ARCHIVE_TGZ_PATH, INVALID_DESCRIPTOR,
                      DWCA_ORPHANED_ROWS)


class TestPandasIntegration(unittest.TestCase):
    """Tests of Pandas integration features."""
    # TODO: test weirder archives (encoding, lime termination, ...)

    @patch('dwca.vendor._has_pandas', False)
    def test_pd_read_pandas_unavailable(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            with self.assertRaises(ImportError):
                dwca.pd_read('occurrence.txt')

    def test_pd_read_simple_case(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            df = dwca.pd_read('occurrence.txt')

            # check types, headers and dimensions
            self.assertIsInstance(df, pd.DataFrame)
            cols = df.columns.values.tolist()
            self.assertEqual(cols, ['id', 'basisOfRecord', 'locality', 'family', 'scientificName'])
            self.assertEqual(df.shape, (2, 5))  # Row/col counts are correct

            # check content
            self.assertEqual(df['basisOfRecord'].values.tolist(), ['Observation', 'Observation'])
            self.assertEqual(df['family'].values.tolist(), ['Tetraodontidae', 'Osphronemidae'])
            self.assertEqual(df['locality'].values.tolist(), ['Borneo', 'Mumbai'])
            self.assertEqual(df['scientificName'].values.tolist(), ['tetraodon fluviatilis', 'betta splendens'])

    def test_pd_read_no_data_files(self):
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            with self.assertRaises(NotADataFile):
                dwca.pd_read('imaginary_file.txt')

            with self.assertRaises(NotADataFile):
                dwca.pd_read('eml.xml')

    def test_pd_read_extensions(self):
        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            desc_df = dwca.pd_read('description.txt')
            self.assertIsInstance(desc_df, pd.DataFrame)
            self.assertEqual(desc_df.shape, (3, 4))
            self.assertEqual(desc_df['language'].values.tolist(), ['EN', 'FR', 'EN'])

            vern_df = dwca.pd_read('vernacularname.txt')
            self.assertIsInstance(vern_df, pd.DataFrame)
            self.assertEqual(vern_df.shape, (4, 4))
            self.assertEqual(vern_df['countryCode'].values.tolist(), ['US', 'ZA', 'FI', 'ZA'])

    def test_pd_read_quotedir(self):
        with DwCAReader(DIRECTORY_CSV_QUOTE_ARCHIVE_PATH) as dwca:
            df = dwca.pd_read('occurrence.txt')
            # The field separator is found in a quoted field, don't break
            self.assertEqual(df.shape, (2, 5))
            self.assertEqual(df['basisOfRecord'].values.tolist()[0], 'Observation, something')

    def test_pd_read_default_values(self):
        with DwCAReader(DEFAULT_VAL_PATH) as dwca:
            df = dwca.pd_read('occurrence.txt')

            self.assertIn('country', df.columns.values.tolist())
            for country in df['country'].values.tolist():
                self.assertEqual(country, 'Belgium')

    def test_pd_read_utf8_eol_ignored(self):
        """Ensure we don't split lines based on the x85 utf8 EOL char.

        (only the EOL string specified in meta.xml should be used).
         """
        with DwCAReader(UTF8EOL_ARCHIVE_PATH) as dwca:
            df = dwca.pd_read('occurrence.txt')
            # If line properly split => 64 columns.
            # (61 - and probably an IndexError - if errors)
            self.assertEqual(64, df.shape[1])

    def test_pd_read_simple_csv(self):
        with DwCAReader(SIMPLE_CSV) as dwca:

            df = dwca.pd_read('0008333-160118175350007.csv')
            # Ensure we get the correct number of rows
            self.assertEqual(3, df.shape[0])
            # Ensure we can access arbitrary data

            self.assertEqual(df['decimallatitude'].values.tolist()[1], -31.98333)

class TestDwCAReader(unittest.TestCase):
    # TODO: Move row-oriented tests to another test class
    """Unit tests for DwCAReader class."""
    def test_get_descriptor_for(self):
        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            # We can get a DataFileDescriptor for each data file
            self.assertIsInstance(dwca.get_descriptor_for('taxon.txt'), DataFileDescriptor)
            self.assertIsInstance(dwca.get_descriptor_for('description.txt'), DataFileDescriptor)
            self.assertIsInstance(dwca.get_descriptor_for('vernacularname.txt'), DataFileDescriptor)

            # But None for non-data files
            self.assertIsNone(dwca.get_descriptor_for('eml.xml'))
            self.assertIsNone(dwca.get_descriptor_for('meta.xml'))

            # Also None for files that don't actually exists
            self.assertIsNone(dwca.get_descriptor_for('imaginary_file.txt'))

            # Basic content checks of the descriptors
            taxon_descriptor = dwca.get_descriptor_for('taxon.txt')
            self.assertEqual(dwca.descriptor.core, taxon_descriptor)
            self.assertEqual(taxon_descriptor.file_location, 'taxon.txt')
            self.assertEqual(taxon_descriptor.file_encoding, 'utf-8')
            self.assertEqual(taxon_descriptor.type, 'http://rs.tdwg.org/dwc/terms/Taxon')

            description_descriptor = dwca.get_descriptor_for('description.txt')
            self.assertEqual(description_descriptor.file_location, 'description.txt')
            self.assertEqual(description_descriptor.file_encoding, 'utf-8')
            self.assertEqual(description_descriptor.type, 'http://rs.gbif.org/terms/1.0/Description')

            vernacular_descriptor = dwca.get_descriptor_for('vernacularname.txt')
            self.assertEqual(vernacular_descriptor.file_location, 'vernacularname.txt')
            self.assertEqual(vernacular_descriptor.file_encoding, 'utf-8')
            self.assertEqual(vernacular_descriptor.type, 'http://rs.gbif.org/terms/1.0/VernacularName')

        # Also check we can get a DataFileDescriptor for a simple Archive (without metafile)
        with DwCAReader(SIMPLE_CSV) as dwca:
            self.assertIsInstance(dwca.get_descriptor_for('0008333-160118175350007.csv'), DataFileDescriptor)

    def test_open_included_file(self):
        """Ensure DwCAReader.open_included_file work as expected."""
        # Let's use it to read the raw core data file:
        with DwCAReader(DIRECTORY_ARCHIVE_PATH) as dwca:
            f = dwca.open_included_file('occurrence.txt')

            raw_occ = f.read()
            self.assertTrue(raw_occ.endswith("'betta' splendens\n"))

        # TODO: test more cases: opening mode, exceptions raised, ...

    def test_descriptor_references_non_existent_data_field(self):
        """Ensure InvalidArchive is raised when a file descriptor references non-existent field.

        This ensure cases like http://dev.gbif.org/issues/browse/PF-2470 (descriptor contains
        <field index="234" term="http://rs.gbif.org/terms/1.0/lastCrawled"/>, but has only 234
        fields in data file) fail in a visible way (previously, archive just appeard empty).
        """
        with DwCAReader(INVALID_DESCRIPTOR) as dwca:
            with self.assertRaises(InvalidArchive):
                for _ in dwca:
                    pass

    def test_use_extensions(self):
        """Ensure the .use_extensions attribute of DwCAReader works as intended."""
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            self.assertFalse(dwca.use_extensions)  # Basic archive without extensions

        with DwCAReader(SIMPLE_CSV) as dwca:  # Just a CSV file, so no extensions
            self.assertFalse(dwca.use_extensions)

        with DwCAReader(EXTENSION_ARCHIVE_PATH) as dwca:
            self.assertTrue(dwca.use_extensions)

        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            self.assertTrue(dwca.use_extensions)

        with DwCAReader(EXTENSION_ARCHIVE_PATH, extensions_to_ignore="vernacularname.txt") as dwca:
            # We ignore the extension, so archive appears without
            self.assertFalse(dwca.use_extensions)

    def test_default_metadata_filename(self):
        """Ensure that metadata is found by it's default name.

        Metadata is named "EML.xml", but no metadata attribute in Metafile.
        """
        with DwCAReader(DEFAULT_METADATA_FILENAME) as dwca:
            self.assertIsInstance(dwca.metadata, ET.Element)

            v = (dwca.metadata.find('dataset')
                              .find('creator')
                              .find('individualName')
                              .find('givenName').text)
            self.assertEqual(v, 'Nicolas')

    def test_subdirectory_archive(self):
        """Ensure we support Archives where all the content is under a single directory."""
        tmp_dir = tempfile.gettempdir()

        num_files_before = len(os.listdir(tmp_dir))
        with DwCAReader(SUBDIR_ARCHIVE_PATH) as dwca:
            # Ensure we have access to metadata
            self.assertIsInstance(dwca.metadata, ET.Element)

            # And to the rows themselves
            for row in dwca:
                self.assertIsInstance(row, CoreRow)

            rows = list(dwca)
            self.assertEqual('Borneo', rows[0].data[qn('locality')])

            num_files_during = len(os.listdir(tmp_dir))

        num_files_after = len(os.listdir(tmp_dir))

        # Let's also check temporary dir is correctly created and removed.
        self.assertEqual(num_files_before + 1, num_files_during)
        self.assertEqual(num_files_before, num_files_after)

    def test_exception_invalid_archives_missing_metadata(self):
        """An exception is raised when referencing a missing metadata file."""
        # Sometimes, the archive metafile references a metadata file that's not present in the
        # archive. See for example http://dev.gbif.org/issues/browse/PF-2125
        with self.assertRaises(InvalidArchive) as cm:
            a = DwCAReader(INVALID_LACKS_METADATA)
            a.close()

        the_exception = cm.exception

        expected_message = "eml.xml is referenced in the archive descriptor but missing."
        self.assertEqual(str(the_exception), expected_message)

    def test_exception_invalid_simple_archives(self):
        """Ensure an exception is raised when simple archives can't be interpreted.

        When there's no metafile in an archive, this one consists of a single data core file,
        and possibly some metadata in EML.xml. If the archive doesn't follow this structure,
        python-dwca-reader can't detect the data file and should throw an InvalidArchive exception.
        """
        # There's a random file (in addition to data and EML.xml) in this one, so we can't choose
        # which file is the datafile.
        with self.assertRaises(InvalidArchive):
            a = DwCAReader(INVALID_SIMPLE_TOOMUCH)
            a.close()

        with self.assertRaises(InvalidArchive):
            a = DwCAReader(INVALID_SIMPLE_TWO)
            a.close()

    def test_default_values_metafile(self):
        """
        Ensure default values are used when optional attributes are absent in metafile.

        Optional attributes tested here: linesTerminatedBy, fieldsTerminatedBy.
        """
        with DwCAReader(DEFAULT_META_VALUES) as dwca:
            # Test iterating on rows...
            for row in dwca:
                self.assertIsInstance(row, CoreRow)

            # And verify the values themselves:
            # Test also "fieldsenclosedBy"?

    def test_simplecsv_archive(self):
        """Ensure the reader works with archives consiting of a single CSV file.

        As described in page #2 of http://www.gbif.org/resource/80639, those archives consists
        of a single core data file where the first line provides the names of the Darwin Core terms
        represented in the published data. That also seems to match quite well the definition of
        Simple Darwin Core expressed as text: http://rs.tdwg.org/dwc/terms/simple/index.htm.
        """
        with DwCAReader(SIMPLE_CSV) as dwca:
            # Ensure we get the correct number of rows
            self.assertEqual(len(dwca.rows), 3)
            # Ensure we can access arbitrary data
            self.assertEqual(dwca.get_corerow_by_position(1).data['decimallatitude'], '-31.98333')
            # Archive descriptor should be None
            self.assertIsNone(dwca.descriptor)
            # (scientific) metadata should be None
            self.assertIsNone(dwca.metadata)

        # Let's do the same tests again but with DOS line endings in the data file
        with DwCAReader(SIMPLE_CSV_DOS) as dwca:
            # Ensure we get the correct number of rows
            self.assertEqual(len(dwca.rows), 3)
            # Ensure we can access arbitrary data
            self.assertEqual(dwca.get_corerow_by_position(1).data['decimallatitude'], '-31.98333')
            # Archive descriptor should be None
            self.assertIsNone(dwca.descriptor)
            # (scientific) metadata should be None
            self.assertIsNone(dwca.metadata)

        # And with a file where fields are not double quotes-enclosed:
        with DwCAReader(SIMPLE_CSV_NOTENCLOSED) as dwca:
            # Ensure we get the correct number of rows
            self.assertEqual(len(dwca.rows), 3)
            # Ensure we can access arbitrary data
            self.assertEqual(dwca.get_corerow_by_position(1).data['decimallatitude'], '-31.98333')
            # Archive descriptor should be None
            self.assertIsNone(dwca.descriptor)
            # (scientific) metadata should be None
            self.assertIsNone(dwca.metadata)

    def test_simplecsv_archive_eml(self):
        """Test Archive witthout metafile, but containing metadata.

        Similar to test_simplecsv_archive, except the archive also contains a Metadata file named
        EML.xml. This correspond to the second case on page #2 of
        http://www.gbif.org/resource/80639. The metadata file having the "standard name", it should
        properly handled.
        """
        with DwCAReader(SIMPLE_CSV_EML) as dwca:
            # Ensure we get the correct number of rows
            self.assertEqual(len(dwca.rows), 3)
            # Ensure we can access arbitrary data
            self.assertEqual(dwca.get_corerow_by_position(1).data['decimallatitude'], '-31.98333')
            # Archive descriptor should be None
            self.assertIsNone(dwca.descriptor)
            # (scientific) metadata is found
            self.assertIsInstance(dwca.metadata, ET.Element)
            # TODO: also access a metadata element to ensure this really works?
            v = (dwca.metadata.find('dataset').find('language').text)
            self.assertEqual(v, 'en')

    def test_unzipped_archive(self):
        """Ensure it works with non-zipped (directory) archives."""
        with DwCAReader(DIRECTORY_ARCHIVE_PATH) as dwca:
            # See metadata access works...
            self.assertIsInstance(dwca.metadata, ET.Element)

            # And iterating...
            for row in dwca:
                self.assertIsInstance(row, CoreRow)

    def test_csv_quote_dir_archive(self):
        """If the field separator is in a quoted field, don't break on it."""
        with DwCAReader(DIRECTORY_CSV_QUOTE_ARCHIVE_PATH) as dwca:
            rows = list(dwca)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].data[qn('basisOfRecord')], 'Observation, something')

    def test_dont_enclose_unenclosed(self):
        """If fields_enclosed_by is set to an empty string, don't enclose (even if quotes are present)"""
        with DwCAReader(DIRECTORY_ARCHIVE_PATH) as dwca:
            rows = list(dwca)

            self.assertEqual('"betta" splendens', rows[2].data[qn('scientificName')])
            self.assertEqual("'betta' splendens", rows[3].data[qn('scientificName')])

    def test_tgz_archives(self):
        """Ensure the reader (basic features) works with a .tgz Archive."""
        with DwCAReader(BASIC_ARCHIVE_TGZ_PATH) as dwca:
            self.assertIsInstance(dwca.metadata, ET.Element)

            for row in dwca:
                self.assertIsInstance(row, CoreRow)

            rows = list(dwca)
            self.assertEqual(len(rows), 2)
            self.assertEqual('Borneo', rows[0].data[qn('locality')])
            self.assertEqual('Mumbai', rows[1].data[qn('locality')])

    def test_classic_opening(self):
        """Ensure it also works w/o the 'with' statement."""
        dwca = DwCAReader(BASIC_ARCHIVE_PATH)
        self.assertIsInstance(dwca.metadata, ET.Element)
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

            if sys.version_info[0] == 2:  # Python 2
                self.assertIn("http://rs.tdwg.org/dwc/terms/scientificName': u'tetraodon fluviatilis'",
                              l_repr)
            else:
                self.assertIn("http://rs.tdwg.org/dwc/terms/scientificName': 'tetraodon fluviatilis'",
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
            f.close()

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
        """If archive is a directory, it should not be deleted after use.

        (check that the cleanup routine for zipped file is not called by accident)
        """
        r = DwCAReader(DIRECTORY_ARCHIVE_PATH)
        r.close()

        # If previously destroyed, this will fail...
        r = DwCAReader(DIRECTORY_ARCHIVE_PATH)
        self.assertIsInstance(r.metadata, ET.Element)
        r.close()

    def test_temporary_dir_zipped(self):
        """Test a temporary directory is created during execution.

        (complementary to test_cleanup())
        """
        tmp_dir = tempfile.gettempdir()

        num_files_before = len(os.listdir(tmp_dir))
        with DwCAReader(BASIC_ARCHIVE_PATH):
            num_files_during = len(os.listdir(tmp_dir))

        self.assertEqual(num_files_before, num_files_during - 1)

    def test_no_temporary_dir_directory(self):
        """If archive is a directory, no need to create temporary files."""
        num_files_before = len(os.listdir('.'))
        with DwCAReader(DIRECTORY_ARCHIVE_PATH):
            num_files_during = len(os.listdir('.'))

        self.assertEqual(num_files_before, num_files_during)

    def test_archives_without_metadata(self):
        """Ensure we can deal with an archive containing a metafile, but no metadata."""
        with DwCAReader(NOMETADATA_PATH) as dwca:
            self.assertIsNone(dwca.metadata)

            # But the data is nevertheless accessible
            rows = list(dwca)
            self.assertEqual(len(rows), 2)
            self.assertEqual('Borneo', rows[0].data[qn('locality')])
            self.assertEqual('Mumbai', rows[1].data[qn('locality')])

    def test_metadata(self):
        """A few basic tests on the metadata attribute

        TODO: split
        """
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            # Assert metadata is an instance of ElementTree.Element
            self.assertIsInstance(dwca.metadata, ET.Element)

            # Assert we can read basic fields from EML:
            v = (dwca.metadata.find('dataset').find('creator').find('individualName')
                     .find('givenName').text)
            self.assertEqual(v, 'Nicolas')

    def test_core_contains_term(self):
        """Test the core_contains_term method."""
        # Example file contains locality but no country
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            self.assertTrue(dwca.core_contains_term(qn('locality')))
            self.assertFalse(dwca.core_contains_term(qn('country')))

        # Also test it with a simple (= no metafile) archive
        with DwCAReader(SIMPLE_CSV) as dwca:
            self.assertTrue(dwca.core_contains_term('datasetkey'))
            self.assertFalse(dwca.core_contains_term('trucmachin'))

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
        """Test that the order of appearance in Core file is respected when iterating."""
        # This is also probably tested indirectly elsewhere, but this is the right place :)
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

    def test_deprecated_get_row_by_id(self):
        """get_row_by_id() has been renamed get_corerow_by_id(). Make sure it still works, w/ warning."""

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)

            with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
                # Passed as an integer, conversion will be tried...
                r = dwca.get_row_by_id(3)
                self.assertEqual('Peliperdix', r.data['http://rs.tdwg.org/dwc/terms/genus'])

                self.assertEqual(1, len(w))  # Warning was issued
                the_warning = w[0]
                assert issubclass(the_warning.category, DeprecationWarning)
                self.assertEqual("This method has been renamed to get_corerow_by_id().", str(the_warning.message))

    def test_deprecated_row_by_position(self):
        """get_row_by_index() has been renamed get_corerow_by_position(). Make sure it still works, w/ warning."""

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)

            # Copy-pasted code from the long term test_get_corerow_by_position()
            with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
                # Row IDs are ordered like this in core: id 4-1-3-2
                first_row = dwca.get_row_by_index(0)
                self.assertEqual(4, int(first_row.id))

                self.assertEqual(1, len(w))  # Warning was issued
                the_warning = w[0]
                assert issubclass(the_warning.category, DeprecationWarning)
                self.assertEqual("This method has been renamed to get_corerow_by_position().", str(the_warning.message))

                last_row = dwca.get_row_by_index(3)
                self.assertEqual(2, int(last_row.id))

                # Exception raised if bigger than archive (last index: 3)
                with self.assertRaises(RowNotFound):
                    dwca.get_row_by_index(4)

                with self.assertRaises(RowNotFound):
                    dwca.get_row_by_index(1000)

    def test_get_corerow_by_position(self):
        """Test the get_corerow_by_position() method work as expected"""
        with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
            # Row IDs are ordered like this in core: id 4-1-3-2
            first_row = dwca.get_corerow_by_position(0)
            self.assertEqual(4, int(first_row.id))

            last_row = dwca.get_corerow_by_position(3)
            self.assertEqual(2, int(last_row.id))

            # Exception raised if bigger than archive (last index: 3)
            with self.assertRaises(RowNotFound):
                dwca.get_corerow_by_position(4)

            with self.assertRaises(RowNotFound):
                dwca.get_corerow_by_position(1000)

    def test_get_corerow_by_id_string(self):
        genus_qn = 'http://rs.tdwg.org/dwc/terms/genus'

        with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
            # Number can be passed as a string....
            r = dwca.get_corerow_by_id('3')
            self.assertEqual('Peliperdix', r.data[genus_qn])

    def test_get_corerow_by_id_multiple_calls(self):
        genus_qn = 'http://rs.tdwg.org/dwc/terms/genus'

        with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
            r = dwca.get_corerow_by_id('3')
            self.assertEqual('Peliperdix', r.data[genus_qn])

            # If iterator is not properly reset, None will be returned
            # the second time
            r = dwca.get_corerow_by_id('3')
            self.assertEqual('Peliperdix', r.data[genus_qn])

    def test_get_corerow_by_id_other(self):
        genus_qn = 'http://rs.tdwg.org/dwc/terms/genus'

        with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
            # Passed as an integer, conversion will be tried...
            r = dwca.get_corerow_by_id(3)
            self.assertEqual('Peliperdix', r.data[genus_qn])

    def test_get_inexistent_row(self):
        """ Ensure get_corerow_by_id() raises RowNotFound if we ask it an unexistent row. """
        with DwCAReader(IDS_ARCHIVE_PATH) as dwca:
            with self.assertRaises(RowNotFound):
                dwca.get_corerow_by_id(8000)

    def test_read_core_value(self):
        """Retrieve a simple value from core file"""
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            rows = list(dwca)

            # Check basic locality values from sample file
            self.assertEqual('Borneo', rows[0].data[qn('locality')])
            self.assertEqual('Mumbai', rows[1].data[qn('locality')])

    def test_enclosed_data(self):
        """Ensure data is properly trimmed when fieldsEnclosedBy is in use."""
        with DwCAReader(BASIC_ENCLOSED_ARCHIVE_PATH) as dwca:
            rows = list(dwca)

            # Locality is enclosed in "'" chars, they should be trimmed...
            self.assertEqual('Borneo', rows[0].data[qn('locality')])
            self.assertEqual('Mumbai', rows[1].data[qn('locality')])

            # But family isn't, so it shouldn't be altered
            self.assertEqual('Tetraodontidae', rows[0].data[qn('family')])
            self.assertEqual('Osphronemidae', rows[1].data[qn('family')])

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
                for k, v in l.data.items():
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

    def test_ignore_extension(self):
        """Ensure the extensions_to_ignore argument work as expected."""

        # This archive has two extensions, but we ask to ignore one...
        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH,
                        extensions_to_ignore="description.txt") as multi_dwca:

            rows = list(multi_dwca)

            # 3 vernacular names
            self.assertEqual(3, len(rows[0].extensions))
            # 1 Vernacular name
            self.assertEqual(1, len(rows[1].extensions))
            # No extensions for this core line
            self.assertEqual(0, len(rows[2].extensions))

        # Here, we ignore the only extension of an archive
        with DwCAReader(EXTENSION_ARCHIVE_PATH,
                        extensions_to_ignore="vernacularname.txt") as star_dwca:
                rows = list(star_dwca)

                self.assertEqual(0, len(rows[0].extensions))
                self.assertEqual(0, len(rows[1].extensions))
                self.assertEqual(0, len(rows[2].extensions))
                self.assertEqual(0, len(rows[3].extensions))

        # And here, we check it is silently ignored and everything works in case we ask to
        # ignore an unexisting extension
        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH,
                        extensions_to_ignore="helloworld.txt") as multi_dwca:

            rows = list(multi_dwca)

            # 3 vernacular names + 2 taxon descriptions
            self.assertEqual(5, len(rows[0].extensions))
            # 1 Vernacular name, no taxon description
            self.assertEqual(1, len(rows[1].extensions))
            # No extensions for this core row
            self.assertEqual(0, len(rows[2].extensions))

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
            # If line properly split => 64 columns.
            # (61 - and probably an IndexError - if errors)
            self.assertEqual(64, len(rows[0].data))

    def test_source_metadata(self):
        # Standard archive: no source metadata
        with DwCAReader(EXTENSION_ARCHIVE_PATH) as star_dwca:
            self.assertEqual(star_dwca.source_metadata, {})

        # GBIF download: source metadata present
        with DwCAReader(GBIF_RESULTS_PATH) as results:
            # We have 23 EML files in the dataset directory
            self.assertEqual(23, len(results.source_metadata))
            # Assert a key is present
            self.assertTrue('eccf4b09-f0c8-462d-a48c-41a7ce36815a' in
                            results.source_metadata)

            self.assertFalse('incorrect-UUID' in results.source_metadata)

            # Assert it's the correct EML file (content!)
            sm = results.source_metadata
            metadata = sm['eccf4b09-f0c8-462d-a48c-41a7ce36815a']

            self.assertIsInstance(metadata, ET.Element)

            # Assert we can read basic fields from EML:
            self.assertEqual(metadata.find('dataset')
                                     .find('creator').find('individualName')
                                     .find('givenName').text,
                             'Rob')

    def test_row_source_metadata(self):
        # For normal DwC-A, it should always be None (NO source data
        # available in archive.)
        with DwCAReader(EXTENSION_ARCHIVE_PATH) as star_dwca:
            self.assertIsNone(star_dwca.rows[0].source_metadata)

        # But it should be supported for GBIF-originating archives
        # (was previously supported with GBIFResultsReader)
        with DwCAReader(GBIF_RESULTS_PATH) as results:
            first_row = results.get_corerow_by_id('607759330')
            m = first_row.source_metadata

            self.assertIsInstance(m, ET.Element)

            v = (m.find('dataset').find('creator').find('individualName')
                  .find('givenName').text)

            self.assertEqual(v, 'Stanley')

            last_row = results.get_corerow_by_id('782700656')
            m = last_row.source_metadata

            self.assertIsInstance(m, ET.Element)
            v = m.find('dataset').find('language').text
            self.assertEqual(v, 'en')

    def test_unknown_archive_format(self):
        """ Ensure InvalidArchive is raised when passed file is not a .zip nor .tgz."""
        invalid_origin_file = tempfile.NamedTemporaryFile(delete=False)

        with self.assertRaises(InvalidArchive):
            with DwCAReader(invalid_origin_file.name):
                pass

        invalid_origin_file.close()

    def test_orphaned_extension_rows_noext(self):
        """ orphaned_extension_rows returns {} when there's no extensions."""
        # Archive without extensions: we expect {}
        with DwCAReader(BASIC_ARCHIVE_PATH) as dwca:
            self.assertEqual({}, dwca.orphaned_extension_rows())

    def test_orphaned_extension_rows_no_orphans(self):
        # Archive with extensions, but no orphaned extension rows

        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            expected = {'description.txt': {}, 'vernacularname.txt': {}}
            self.assertEqual(expected, dwca.orphaned_extension_rows())

    def test_orphaned_extension_rows(self):
        # Archive with extensions and orphaned rows
        with DwCAReader(DWCA_ORPHANED_ROWS) as dwca:
            expected = {
                'description.txt': {u'5': [3, 4], u'6': [5]},
                'vernacularname.txt': {u'7': [4]}
            }
            self.assertEqual(expected, dwca.orphaned_extension_rows())


if __name__ == "__main__":
    unittest.main()
