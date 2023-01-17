import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

import pandas as pd
from unittest.mock import patch

from dwca.darwincore.utils import qualname as qn
from dwca.descriptors import ArchiveDescriptor, DataFileDescriptor
from dwca.exceptions import RowNotFound, InvalidArchive, NotADataFile
from dwca.files import CSVDataFile
from dwca.read import DwCAReader
from dwca.rows import CoreRow, ExtensionRow
from .helpers import sample_data_path
import pytest


class TestPandasIntegration(unittest.TestCase):
    """Tests of Pandas integration features."""

    # TODO: test weirder archives (encoding, lime termination, ...)

    def test_missing_extension_path(self):
        with pytest.raises(InvalidArchive):
            DwCAReader(sample_data_path("dwca-missing-extension-details"))

    @patch("dwca.vendor._has_pandas", False)
    def test_pd_read_pandas_unavailable(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            with pytest.raises(ImportError):
                dwca.pd_read("occurrence.txt")

    def test_pd_read_simple_case(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            df = dwca.pd_read("occurrence.txt")

            # check types, headers and dimensions
            assert isinstance(df, pd.DataFrame)
            cols = df.columns.values.tolist()
            assert cols == ["id", "basisOfRecord", "locality", "family", "scientificName"]
            assert df.shape == (2, 5)  # Row/col counts are correct

            # check content
            assert df["basisOfRecord"].values.tolist() == ["Observation", "Observation"]
            assert df["family"].values.tolist() == ["Tetraodontidae", "Osphronemidae"]
            assert df["locality"].values.tolist() == ["Borneo", "Mumbai"]
            assert df["scientificName"].values.tolist() == \
                ["tetraodon fluviatilis", "betta splendens"]

    def test_pd_read_no_data_files(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            with pytest.raises(NotADataFile):
                dwca.pd_read("imaginary_file.txt")

            with pytest.raises(NotADataFile):
                dwca.pd_read("eml.xml")

    def test_pd_read_extensions(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            desc_df = dwca.pd_read("description.txt")
            assert isinstance(desc_df, pd.DataFrame)
            assert desc_df.shape == (3, 4)
            assert desc_df["language"].values.tolist() == ["EN", "FR", "EN"]

            vern_df = dwca.pd_read("vernacularname.txt")
            assert isinstance(vern_df, pd.DataFrame)
            assert vern_df.shape == (4, 4)
            assert vern_df["countryCode"].values.tolist() == ["US", "ZA", "FI", "ZA"]

    def test_pd_read_quotedir(self):
        with DwCAReader(sample_data_path("dwca-csv-quote-dir")) as dwca:
            df = dwca.pd_read("occurrence.txt")
            # The field separator is found in a quoted field, don't break
            assert df.shape == (2, 5)
            assert df["basisOfRecord"].values.tolist()[0] == "Observation, something"

    def test_pd_read_default_values(self):
        with DwCAReader(sample_data_path("dwca-test-default.zip")) as dwca:
            df = dwca.pd_read("occurrence.txt")

            assert "country" in df.columns.values.tolist()
            for country in df["country"].values.tolist():
                assert country == "Belgium"

    def test_pd_read_utf8_eol_ignored(self):
        """Ensure we don't split lines based on the x85 utf8 EOL char.

        (only the EOL string specified in meta.xml should be used).
         """
        with DwCAReader(sample_data_path("dwca-utf8-eol-test.zip")) as dwca:
            df = dwca.pd_read("occurrence.txt")
            # If line properly split => 64 columns.
            # (61 - and probably an IndexError - if errors)
            assert 64 == df.shape[1]

    def test_pd_read_simple_csv(self):
        with DwCAReader(sample_data_path("dwca-simple-csv.zip")) as dwca:

            df = dwca.pd_read("0008333-160118175350007.csv")
            # Ensure we get the correct number of rows
            assert 3 == df.shape[0]
            # Ensure we can access arbitrary data

            assert df["decimallatitude"].values.tolist()[1] == -31.98333


class TestDwCAReader(unittest.TestCase):
    # TODO: Move row-oriented tests to another test class
    """Unit tests for DwCAReader class."""

    def test_partial_default(self):
        with DwCAReader(sample_data_path("dwca-partial-default.zip")) as dwca:
            assert dwca.rows[0].data[qn("country")] == "France"  # Value comes from data file
            assert dwca.rows[1].data[qn("country")] == "Belgium"  # Value is field default

    def test_core_file_location(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            assert dwca.core_file_location == "occurrence.txt"

        with DwCAReader(sample_data_path("dwca-simple-csv.zip")) as dwca:
            assert dwca.core_file_location == "0008333-160118175350007.csv"

    def test_core_file(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            assert isinstance(dwca.core_file, CSVDataFile)

            # Quick content check just to be sure
            assert dwca.core_file.lines_to_ignore == 1

    def test_extension_file_noext(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            assert dwca.extension_files == []

    def test_extension_files(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            # Check extension_files is iterable and contains the right type
            for ext in dwca.extension_files:
                assert isinstance(ext, CSVDataFile)

            # Check the length is correct
            assert len(dwca.extension_files) == 2

            # Check the order of the metafile is respected + quick content check
            assert dwca.extension_files[0].file_descriptor.file_location == "description.txt"
            assert dwca.extension_files[1].file_descriptor.file_location == \
                "vernacularname.txt"

    def test_get_descriptor_for(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            # We can get a DataFileDescriptor for each data file
            assert isinstance(dwca.get_descriptor_for("taxon.txt"), DataFileDescriptor)
            assert isinstance(dwca.get_descriptor_for("description.txt"), DataFileDescriptor)
            assert isinstance(dwca.get_descriptor_for("vernacularname.txt"), DataFileDescriptor)

            # But NotADataFile exception for non-data files
            with pytest.raises(NotADataFile):
                dwca.get_descriptor_for("eml.xml")

            with pytest.raises(NotADataFile):
                dwca.get_descriptor_for("meta.xml")

            # Also NotADataFile for files that don't actually exists
            with pytest.raises(NotADataFile):
                dwca.get_descriptor_for("imaginary_file.txt")

            # Basic content checks of the descriptors
            taxon_descriptor = dwca.get_descriptor_for("taxon.txt")
            assert dwca.descriptor.core == taxon_descriptor
            assert taxon_descriptor.file_location == "taxon.txt"
            assert taxon_descriptor.file_encoding == "utf-8"
            assert taxon_descriptor.type == "http://rs.tdwg.org/dwc/terms/Taxon"

            description_descriptor = dwca.get_descriptor_for("description.txt")
            assert description_descriptor.file_location == "description.txt"
            assert description_descriptor.file_encoding == "utf-8"
            assert description_descriptor.type == "http://rs.gbif.org/terms/1.0/Description"

            vernacular_descriptor = dwca.get_descriptor_for("vernacularname.txt")
            assert vernacular_descriptor.file_location == "vernacularname.txt"
            assert vernacular_descriptor.file_encoding == "utf-8"
            assert vernacular_descriptor.type == \
                "http://rs.gbif.org/terms/1.0/VernacularName"

        # Also check we can get a DataFileDescriptor for a simple Archive (without metafile)
        with DwCAReader(sample_data_path("dwca-simple-csv.zip")) as dwca:
            assert isinstance(dwca.get_descriptor_for("0008333-160118175350007.csv"), DataFileDescriptor)

    def test_open_included_file(self):
        """Ensure DwCAReader.open_included_file work as expected."""
        # Let's use it to read the raw core data file:
        with DwCAReader(sample_data_path("dwca-simple-dir")) as dwca:
            f = dwca.open_included_file("occurrence.txt")

            raw_occ = f.read()
            assert raw_occ.endswith("'betta' splendens\n")

        # TODO: test more cases: opening mode, exceptions raised, ...

    def test_descriptor_references_non_existent_data_field(self):
        """Ensure InvalidArchive is raised when a file descriptor references non-existent field.

        This ensure cases like http://dev.gbif.org/issues/browse/PF-2470 (descriptor contains
        <field index="234" term="http://rs.gbif.org/terms/1.0/lastCrawled"/>, but has only 234
        fields in data file) fail in a visible way (previously, archive just appeared empty).
        """
        with DwCAReader(sample_data_path("dwca-malformed-descriptor")) as dwca:
            with pytest.raises(InvalidArchive):
                for _ in dwca:
                    pass

    def test_custom_tempdir(self):
        tmp_dir = os.path.abspath(".tmp")
        with DwCAReader(
            sample_data_path("dwca-simple-test-archive.zip"), tmp_dir=tmp_dir
        ) as dwca:
            assert dwca.absolute_temporary_path("occurrence.txt").startswith(tmp_dir)

    def test_use_extensions(self):
        """Ensure the .use_extensions attribute of DwCAReader works as intended."""
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            assert not dwca.use_extensions  # Basic archive without extensions

        with DwCAReader(
            sample_data_path("dwca-simple-csv.zip")
        ) as dwca:  # Just a CSV file, so no extensions
            assert not dwca.use_extensions

        with DwCAReader(sample_data_path("dwca-star-test-archive.zip")) as dwca:
            assert dwca.use_extensions

        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            assert dwca.use_extensions

        with DwCAReader(
            sample_data_path("dwca-star-test-archive.zip"),
            extensions_to_ignore="vernacularname.txt",
        ) as dwca:
            # We ignore the extension, so archive appears without
            assert not dwca.use_extensions

    def test_default_metadata_filename(self):
        """Ensure that metadata is found by it's default name.

        Metadata is named "EML.xml", but no metadata attribute in Metafile.
        """
        with DwCAReader(sample_data_path("dwca-default-metadata-filename.zip")) as dwca:
            assert isinstance(dwca.metadata, ET.Element)

            v = (
                dwca.metadata.find("dataset")
                .find("creator")
                .find("individualName")
                .find("givenName")
                .text
            )
            assert v == "Nicolas"

    def test_subdirectory_archive(self):
        """Ensure we support Archives where all the content is under a single directory."""
        tmp_dir = tempfile.gettempdir()

        num_files_before = len(os.listdir(tmp_dir))
        with DwCAReader(sample_data_path("dwca-simple-subdir.zip")) as dwca:
            # Ensure we have access to metadata
            assert isinstance(dwca.metadata, ET.Element)

            # And to the rows themselves
            for row in dwca:
                assert isinstance(row, CoreRow)

            rows = list(dwca)
            assert "Borneo" == rows[0].data[qn("locality")]

            num_files_during = len(os.listdir(tmp_dir))

        num_files_after = len(os.listdir(tmp_dir))

        # Let's also check temporary dir is correctly created and removed.
        assert num_files_before + 1 == num_files_during
        assert num_files_before == num_files_after

    def test_exception_invalid_archives_missing_metadata(self):
        """An exception is raised when referencing a missing metadata file."""
        # Sometimes, the archive metafile references a metadata file that's not present in the
        # archive. See for example http://dev.gbif.org/issues/browse/PF-2125
        with pytest.raises(InvalidArchive) as cm:
            a = DwCAReader(sample_data_path("dwca-invalid-lacks-metadata"))
            a.close()

        expected_message = (
            "eml.xml is referenced in the archive descriptor but missing."
        )
        assert str(cm.value) == expected_message

    def test_implicit_encoding_metadata(self):
        """If the metadata file doesn't specifies encoding, use UTF-8."""
        with DwCAReader(sample_data_path("dwca-simple-dir")) as dwca:
            v = (
                dwca.metadata.find("dataset")
                .find("creator")
                .find("individualName")
                .find("surName")
                .text
            )
            assert v == u"Noé"

    def test_explicit_encoding_metadata(self):
        """If the metadata file explicitly specifies encoding (<xml ...>), make sure it is used."""

        with DwCAReader(sample_data_path("dwca-metadata-windows1252-encoding")) as dwca:
            v = (
                dwca.metadata.find("dataset")
                .find("creator")
                .find("individualName")
                .find("surName")
                .text
            )
            assert v == u"Noé"  # Is the accent properly interpreted?

    def test_exception_invalid_simple_archives(self):
        """Ensure an exception is raised when simple archives can't be interpreted.

        When there's no metafile in an archive, this one consists of a single data core file,
        and possibly some metadata in EML.xml. If the archive doesn't follow this structure,
        python-dwca-reader can't detect the data file and should throw an InvalidArchive exception.
        """
        # There's a random file (in addition to data and EML.xml) in this one, so we can't choose
        # which file is the datafile.
        with pytest.raises(InvalidArchive):
            a = DwCAReader(sample_data_path("dwca-invalid-simple-toomuch.zip"))
            a.close()

        with pytest.raises(InvalidArchive):
            a = DwCAReader(sample_data_path("dwca-invalid-simple-two.zip"))
            a.close()

    def test_default_values_metafile(self):
        """
        Ensure default values are used when optional attributes are absent in metafile.

        Optional attributes tested here: linesTerminatedBy, fieldsTerminatedBy.
        """
        with DwCAReader(sample_data_path("dwca-meta-default-values")) as dwca:
            # Test iterating on rows...
            for row in dwca:
                assert isinstance(row, CoreRow)

            # And verify the values themselves:
            # Test also "fieldsenclosedBy"?

    def test_simplecsv_archive(self):
        """Ensure the reader works with archives consiting of a single CSV file.

        As described in page #2 of http://www.gbif.org/resource/80639, those archives consists
        of a single core data file where the first line provides the names of the Darwin Core terms
        represented in the published data. That also seems to match quite well the definition of
        Simple Darwin Core expressed as text: http://rs.tdwg.org/dwc/terms/simple/index.htm.
        """
        with DwCAReader(sample_data_path("dwca-simple-csv.zip")) as dwca:
            # Ensure we get the correct number of rows
            assert len(dwca.rows) == 3
            # Ensure we can access arbitrary data
            assert dwca.get_corerow_by_position(1).data["decimallatitude"] == "-31.98333"
            # Archive descriptor should be None
            assert dwca.descriptor is None
            # (scientific) metadata should be None
            assert dwca.metadata is None

        # Let's do the same tests again but with DOS line endings in the data file
        with DwCAReader(sample_data_path("dwca-simple-csv-dos.zip")) as dwca:
            # Ensure we get the correct number of rows
            assert len(dwca.rows) == 3
            # Ensure we can access arbitrary data
            assert dwca.get_corerow_by_position(1).data["decimallatitude"] == "-31.98333"
            # Archive descriptor should be None
            assert dwca.descriptor is None
            # (scientific) metadata should be None
            assert dwca.metadata is None

        # And with a file where fields are not double quotes-enclosed:
        with DwCAReader(sample_data_path("dwca-simple-csv-notenclosed.zip")) as dwca:
            # Ensure we get the correct number of rows
            assert len(dwca.rows) == 3
            # Ensure we can access arbitrary data
            assert dwca.get_corerow_by_position(1).data["decimallatitude"] == "-31.98333"
            # Archive descriptor should be None
            assert dwca.descriptor is None
            # (scientific) metadata should be None
            assert dwca.metadata is None

    def test_simplecsv_archive_eml(self):
        """Test Archive without metafile, but containing metadata.

        Similar to test_simplecsv_archive, except the archive also contains a Metadata file named
        EML.xml. This correspond to the second case on page #2 of
        http://www.gbif.org/resource/80639. The metadata file having the "standard name", it should
        properly handled.
        """
        with DwCAReader(sample_data_path("dwca-simple-csv-eml.zip")) as dwca:
            # Ensure we get the correct number of rows
            assert len(dwca.rows) == 3
            # Ensure we can access arbitrary data
            assert dwca.get_corerow_by_position(1).data["decimallatitude"] == "-31.98333"
            # Archive descriptor should be None
            assert dwca.descriptor is None
            # (scientific) metadata is found
            assert isinstance(dwca.metadata, ET.Element)
            # Quick content check
            assert dwca.metadata.find("dataset").find("language").text == "en"

    def test_unzipped_archive(self):
        """Ensure it works with non-zipped (directory) archives."""
        with DwCAReader(sample_data_path("dwca-simple-dir")) as dwca:
            # See metadata access works...
            assert isinstance(dwca.metadata, ET.Element)

            # And iterating...
            for row in dwca:
                assert isinstance(row, CoreRow)

    def test_csv_quote_dir_archive(self):
        """If the field separator is in a quoted field, don't break on it."""
        with DwCAReader(sample_data_path("dwca-csv-quote-dir")) as dwca:
            rows = list(dwca)
            assert len(rows) == 2
            assert rows[0].data[qn("basisOfRecord")] == "Observation, something"

    def test_dont_enclose_unenclosed(self):
        """If fields_enclosed_by is set to an empty string, don't enclose (even if quotes are present)"""
        with DwCAReader(sample_data_path("dwca-simple-dir")) as dwca:
            rows = list(dwca)

            assert '"betta" splendens' == rows[2].data[qn("scientificName")]
            assert "'betta' splendens" == rows[3].data[qn("scientificName")]

    def test_tgz_archives(self):
        """Ensure the reader (basic features) works with a .tgz Archive."""
        with DwCAReader(sample_data_path("dwca-simple-test-archive.tgz")) as dwca:
            assert isinstance(dwca.metadata, ET.Element)

            for row in dwca:
                assert isinstance(row, CoreRow)

            rows = list(dwca)
            assert len(rows) == 2
            assert "Borneo" == rows[0].data[qn("locality")]
            assert "Mumbai" == rows[1].data[qn("locality")]

    def test_classic_opening(self):
        """Ensure it also works w/o the 'with' statement."""
        dwca = DwCAReader(sample_data_path("dwca-simple-test-archive.zip"))
        assert isinstance(dwca.metadata, ET.Element)
        dwca.close()

    def test_descriptor(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as basic_dwca:
            assert isinstance(basic_dwca.descriptor, ArchiveDescriptor)

    def test_row_human_representation(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as basic_dwca:
            l = basic_dwca.rows[0]
            l_repr = str(l)
            assert "Rowtype: http://rs.tdwg.org/dwc/terms/Occurrence" in l_repr
            assert "Source: Core file" in l_repr
            assert "Row id:" in l_repr
            assert "Reference extension rows: No" in l_repr
            assert "Reference source metadata: No" in l_repr
            assert "http://rs.tdwg.org/dwc/terms/scientificName': 'tetraodon fluviatilis'" in \
                l_repr

        with DwCAReader(sample_data_path("dwca-star-test-archive.zip")) as star_dwca:
            l = star_dwca.rows[0]
            l_repr = str(l)
            assert "Rowtype: http://rs.tdwg.org/dwc/terms/Taxon" in l_repr
            assert "Source: Core file" in l_repr
            assert "Row id: 1" in l_repr
            assert "Reference extension rows: Yes" in l_repr
            assert "Reference source metadata: No" in l_repr

            extension_l_repr = str(l.extensions[0])
            assert "Rowtype: http://rs.gbif.org/terms/1.0/VernacularName" in extension_l_repr
            assert "Source: Extension file" in extension_l_repr
            assert "Core row id: 1" in extension_l_repr
            assert "ostrich" in extension_l_repr
            assert "Reference extension rows: No" in extension_l_repr
            assert "Reference source metadata: No" in extension_l_repr

    def test_absolute_temporary_path(self):
        """Test the absolute_temporary_path() method."""
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            path_to_occ = dwca.absolute_temporary_path("occurrence.txt")

            # Is it absolute ?
            assert os.path.isabs(path_to_occ)
            # Does file exists ?
            assert os.path.isfile(path_to_occ)
            # IS it the correct content ?
            f = open(path_to_occ)
            content = f.read()
            assert content.startswith("id")
            f.close()

        with DwCAReader(sample_data_path("dwca-simple-dir")) as dwca:
            # Also check if the archive is a directory
            path_to_occ = dwca.absolute_temporary_path("occurrence.txt")

            # Is it absolute ?
            assert os.path.isabs(path_to_occ)
            # Does file exists ?
            assert os.path.isfile(path_to_occ)
            # IS it the correct content ?
            f = open(path_to_occ)
            content = f.read()
            assert content.startswith("id")

    def test_auto_cleanup_zipped(self):
        """Test no temporary files are left after execution (using 'with' statement)."""
        num_files_before = len(os.listdir("."))

        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")):
            pass

        num_files_after = len(os.listdir("."))

        assert num_files_before == num_files_after

    def test_auto_cleanup_directory(self):
        """If the source is already a directory, there's nothing to create nor cleanup."""
        num_files_before = len(os.listdir("."))

        with DwCAReader(sample_data_path("dwca-simple-dir")):
            pass

        num_files_after = len(os.listdir("."))
        assert num_files_before == num_files_after

    def test_manual_cleanup_zipped(self):
        """Test no temporary files are left after execution (calling close() manually)."""
        num_files_before = len(os.listdir("."))

        r = DwCAReader(sample_data_path("dwca-simple-test-archive.zip"))
        r.close()

        num_files_after = len(os.listdir("."))

        assert num_files_before == num_files_after

    def test_source_data_not_destroyed_directory(self):
        """If archive is a directory, it should not be deleted after use.

        (check that the cleanup routine for zipped file is not called by accident)
        """
        r = DwCAReader(sample_data_path("dwca-simple-dir"))
        r.close()

        # If previously destroyed, this will fail...
        r = DwCAReader(sample_data_path("dwca-simple-dir"))
        assert isinstance(r.metadata, ET.Element)
        r.close()

    def test_temporary_dir_zipped(self):
        """Test a temporary directory is created during execution.

        (complementary to test_cleanup())
        """
        tmp_dir = tempfile.gettempdir()

        num_files_before = len(os.listdir(tmp_dir))
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")):
            num_files_during = len(os.listdir(tmp_dir))

        assert num_files_before == num_files_during - 1

    def test_no_temporary_dir_directory(self):
        """If archive is a directory, no need to create temporary files."""
        num_files_before = len(os.listdir("."))
        with DwCAReader(sample_data_path("dwca-simple-dir")):
            num_files_during = len(os.listdir("."))

        assert num_files_before == num_files_during

    def test_archives_without_metadata(self):
        """Ensure we can deal with an archive containing a metafile, but no metadata."""
        with DwCAReader(sample_data_path("dwca-nometadata.zip")) as dwca:
            assert dwca.metadata is None

            # But the data is nevertheless accessible
            rows = list(dwca)
            assert len(rows) == 2
            assert "Borneo" == rows[0].data[qn("locality")]
            assert "Mumbai" == rows[1].data[qn("locality")]

    def test_metadata(self):
        """A few basic tests on the metadata attribute."""
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            # Assert metadata is an instance of ElementTree.Element
            assert isinstance(dwca.metadata, ET.Element)

            # Assert we can read basic fields from EML:
            v = (
                dwca.metadata.find("dataset")
                .find("creator")
                .find("individualName")
                .find("givenName")
                .text
            )
            assert v == "Nicolas"

    def test_core_contains_term(self):
        """Test the core_contains_term method."""
        # Example file contains locality but no country
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            assert dwca.core_contains_term(qn("locality"))
            assert not dwca.core_contains_term(qn("country"))

        # Also test it with a simple (= no metafile) archive
        with DwCAReader(sample_data_path("dwca-simple-csv.zip")) as dwca:
            assert dwca.core_contains_term("datasetkey")
            assert not dwca.core_contains_term("trucmachin")

    def test_ignore_header_lines(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            # The sample file has two real rows + 1 header line
            assert 2 == len([l for l in dwca])

        with DwCAReader(sample_data_path("dwca-noheaders-1.zip")) as dwca:
            # This file has two real rows, without headers
            # (specified in meta.xml)
            assert 2 == len([l for l in dwca])

        with DwCAReader(sample_data_path("dwca-noheaders-2.zip")) as dwca:
            # This file has two real rows, without headers
            # (nothing specified in meta.xml)
            assert 2 == len([l for l in dwca])

    def test_iterate_rows(self):
        """Test the iterating over CoreRow(s)"""
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            for row in dwca:
                assert isinstance(row, CoreRow)

    def test_iterate_order(self):
        """Test that the order of appearance in Core file is respected when iterating."""
        # This is also probably tested indirectly elsewhere, but this is the right place :)
        with DwCAReader(sample_data_path("dwca-ids.zip")) as dwca:
            l = list(dwca)
            # Row IDs are ordered like this in core file: id 4-1-3-2
            assert int(l[0].id) == 4
            assert int(l[1].id) == 1
            assert int(l[2].id) == 3
            assert int(l[3].id) == 2

    def test_iterate_multiple_calls(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            assert 4 == len([l for l in dwca])
            # The second time, we can still find 4 rows...
            assert 4 == len([l for l in dwca])

    def test_get_corerow_by_position(self):
        """Test the get_corerow_by_position() method work as expected"""
        with DwCAReader(sample_data_path("dwca-ids.zip")) as dwca:
            # Row IDs are ordered like this in core: id 4-1-3-2
            first_row = dwca.get_corerow_by_position(0)
            assert 4 == int(first_row.id)

            last_row = dwca.get_corerow_by_position(3)
            assert 2 == int(last_row.id)

            # Exception raised if bigger than archive (last index: 3)
            with pytest.raises(RowNotFound):
                dwca.get_corerow_by_position(4)

            with pytest.raises(RowNotFound):
                dwca.get_corerow_by_position(1000)

    def test_get_corerow_by_id_string(self):
        genus_qn = "http://rs.tdwg.org/dwc/terms/genus"

        with DwCAReader(sample_data_path("dwca-ids.zip")) as dwca:
            # Number can be passed as a string....
            r = dwca.get_corerow_by_id("3")
            assert "Peliperdix" == r.data[genus_qn]

    def test_get_corerow_by_id_multiple_calls(self):
        genus_qn = "http://rs.tdwg.org/dwc/terms/genus"

        with DwCAReader(sample_data_path("dwca-ids.zip")) as dwca:
            r = dwca.get_corerow_by_id("3")
            assert "Peliperdix" == r.data[genus_qn]

            # If iterator is not properly reset, None will be returned
            # the second time
            r = dwca.get_corerow_by_id("3")
            assert "Peliperdix" == r.data[genus_qn]

    def test_get_corerow_by_id_other(self):
        genus_qn = "http://rs.tdwg.org/dwc/terms/genus"

        with DwCAReader(sample_data_path("dwca-ids.zip")) as dwca:
            # Passed as an integer, conversion will be tried...
            r = dwca.get_corerow_by_id(3)
            assert "Peliperdix" == r.data[genus_qn]

    def test_get_inexistent_row(self):
        """ Ensure get_corerow_by_id() raises RowNotFound if we ask it an unexistent row. """
        with DwCAReader(sample_data_path("dwca-ids.zip")) as dwca:
            with pytest.raises(RowNotFound):
                dwca.get_corerow_by_id(8000)

    def test_read_core_value(self):
        """Retrieve a simple value from core file"""
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            rows = list(dwca)

            # Check basic locality values from sample file
            assert "Borneo" == rows[0].data[qn("locality")]
            assert "Mumbai" == rows[1].data[qn("locality")]

    def test_enclosed_data(self):
        """Ensure data is properly trimmed when fieldsEnclosedBy is in use."""
        with DwCAReader(
            sample_data_path("dwca-simple-test-archive-enclosed.zip")
        ) as dwca:
            rows = list(dwca)

            # Locality is enclosed in "'" chars, they should be trimmed...
            assert "Borneo" == rows[0].data[qn("locality")]
            assert "Mumbai" == rows[1].data[qn("locality")]

            # But family isn't, so it shouldn't be altered
            assert "Tetraodontidae" == rows[0].data[qn("family")]
            assert "Osphronemidae" == rows[1].data[qn("family")]

    def test_read_core_value_default(self):
        """Retrieve a (default) value from core

        Test similar to test_read_core_value(), but the retrieved data
        comes from a default value (in meta.xml) instead of from the core
        text file. This is part of the standard and was produced by IPT
        prior to version 2.0.3.
        """
        with DwCAReader(sample_data_path("dwca-test-default.zip")) as dwca:
            for l in dwca:
                assert "Belgium" == l.data[qn("country")]

    def test_qn(self):
        """Test the qn (shortcut generator) helper"""

        # Test success
        assert "http://rs.tdwg.org/dwc/terms/Occurrence" == qn("Occurrence")

        # Test failure
        with pytest.raises(StopIteration):
            qn("dsfsdfsdfsdfsdfsd")

    def test_no_cr_left(self):
        """Test no carriage return characters are left at end of line."""

        # We know we have no \n in our test archive, so if we fine one
        # it's probably a character that was left by error when parsing
        # line
        with DwCAReader(
            sample_data_path("dwca-simple-test-archive.zip")
        ) as simple_dwca:
            for l in simple_dwca:
                for k, v in l.data.items():
                    assert not v.endswith("\n")

    def test_correct_extension_rows_per_core_row(self):
        """Test we have the correct number of extensions rows."""

        # This one has no extension, so row.extensions should be an empty list
        with DwCAReader(
            sample_data_path("dwca-simple-test-archive.zip")
        ) as simple_dwca:
            for r in simple_dwca:
                assert 0 == len(r.extensions)

        with DwCAReader(sample_data_path("dwca-star-test-archive.zip")) as star_dwca:
            rows = list(star_dwca)

            # 3 vernacular names are given for Struthio Camelus...
            assert 3 == len(rows[0].extensions)
            # ... 1 vernacular name for Alectoris chukar ...
            assert 1 == len(rows[1].extensions)
            # ... and none for the last two rows
            assert 0 == len(rows[2].extensions)
            assert 0 == len(rows[3].extensions)

        # TODO: test the same thing with 2 different extensions reffering to the row
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as multi_dwca:
            rows = list(multi_dwca)

            # 3 vernacular names + 2 taxon descriptions
            assert 5 == len(rows[0].extensions)
            # 1 Vernacular name, no taxon description
            assert 1 == len(rows[1].extensions)
            # No extensions for this core line
            assert 0 == len(rows[2].extensions)
            # No vernacular name, 1 taxon description

    def test_ignore_extension(self):
        """Ensure the extensions_to_ignore argument work as expected."""

        # This archive has two extensions, but we ask to ignore one...
        with DwCAReader(
            sample_data_path("dwca-2extensions.zip"),
            extensions_to_ignore="description.txt",
        ) as multi_dwca:

            rows = list(multi_dwca)

            # 3 vernacular names
            assert 3 == len(rows[0].extensions)
            # 1 Vernacular name
            assert 1 == len(rows[1].extensions)
            # No extensions for this core line
            assert 0 == len(rows[2].extensions)

        # Here, we ignore the only extension of an archive
        with DwCAReader(
            sample_data_path("dwca-star-test-archive.zip"),
            extensions_to_ignore="vernacularname.txt",
        ) as star_dwca:
            rows = list(star_dwca)

            assert 0 == len(rows[0].extensions)
            assert 0 == len(rows[1].extensions)
            assert 0 == len(rows[2].extensions)
            assert 0 == len(rows[3].extensions)

        # And here, we check it is silently ignored and everything works in case we ask to
        # ignore an unexisting extension
        with DwCAReader(
            sample_data_path("dwca-2extensions.zip"),
            extensions_to_ignore="helloworld.txt",
        ) as multi_dwca:

            rows = list(multi_dwca)

            # 3 vernacular names + 2 taxon descriptions
            assert 5 == len(rows[0].extensions)
            # 1 Vernacular name, no taxon description
            assert 1 == len(rows[1].extensions)
            # No extensions for this core row
            assert 0 == len(rows[2].extensions)

    def test_row_rowtype(self):
        """Test the rowtype attribute of rows (for Core and extensions)."""
        with DwCAReader(sample_data_path("dwca-star-test-archive.zip")) as star_dwca:
            taxon_qn = "http://rs.tdwg.org/dwc/terms/Taxon"
            vernacular_qn = "http://rs.gbif.org/terms/1.0/VernacularName"

            for i, row in enumerate(star_dwca):
                # All ine instance accessed here are core:
                assert taxon_qn == row.rowtype

                if i == 0:
                    # First row has an extension, and only vn are in use
                    assert vernacular_qn == row.extensions[0].rowtype

    def test_row_class(self):
        with DwCAReader(sample_data_path("dwca-star-test-archive.zip")) as star_dwca:
            for row in star_dwca:
                assert isinstance(row, CoreRow)

                # But the extensions are... extensions (hum)
                for an_extension in row.extensions:
                    assert isinstance(an_extension, ExtensionRow)

    # TODO: Also test we return an empty list on empty archive
    def test_rows_property(self):
        """Test that DwCAReader expose a list of all core rows in 'rows'

        The content of this 'rows' property is equivalent to iterating and
        storing result in a list.
        """
        with DwCAReader(sample_data_path("dwca-star-test-archive.zip")) as star_dwca:
            by_iteration = []
            for r in star_dwca:
                by_iteration.append(r)

            assert by_iteration == star_dwca.rows

    # TODO: Add more test to ensure that the specified EOL sequence
    # (and ONLY this sequence!) is used to split lines.

    # Code should be already fine, but tests lacking
    def test_utf8_eol_ignored(self):
        """Ensure we don't split lines based on the x85 utf8 EOL char.

        (only the EOL string specified in meta.xml should be used).
         """

        with DwCAReader(sample_data_path("dwca-utf8-eol-test.zip")) as dwca:
            rows = dwca.rows
            # If line properly split => 64 columns.
            # (61 - and probably an IndexError - if errors)
            assert 64 == len(rows[0].data)

    def test_source_metadata(self):
        # Standard archive: no source metadata
        with DwCAReader(sample_data_path("dwca-star-test-archive.zip")) as star_dwca:
            assert star_dwca.source_metadata == {}

        # GBIF download: source metadata present
        with DwCAReader(sample_data_path("gbif-results.zip")) as results:
            # We have 23 EML files in the dataset directory
            assert 23 == len(results.source_metadata)
            # Assert a key is present
            assert "eccf4b09-f0c8-462d-a48c-41a7ce36815a" in results.source_metadata

            assert not ("incorrect-UUID" in results.source_metadata)

            # Assert it's the correct EML file (content!)
            sm = results.source_metadata
            metadata = sm["eccf4b09-f0c8-462d-a48c-41a7ce36815a"]

            assert isinstance(metadata, ET.Element)

            # Assert we can read basic fields from EML:
            assert metadata.find("dataset") \
                .find("creator") \
                .find("individualName") \
                .find("givenName") \
                .text == \
                "Rob"

    def test_row_source_metadata(self):
        # For normal DwC-A, it should always be None (NO source data
        # available in archive.)
        with DwCAReader(sample_data_path("dwca-star-test-archive.zip")) as star_dwca:
            assert star_dwca.rows[0].source_metadata is None

        # But it should be supported for GBIF-originating archives
        # (was previously supported with GBIFResultsReader)
        with DwCAReader(sample_data_path("gbif-results.zip")) as results:
            first_row = results.get_corerow_by_id("607759330")
            m = first_row.source_metadata

            assert isinstance(m, ET.Element)

            v = (
                m.find("dataset")
                .find("creator")
                .find("individualName")
                .find("givenName")
                .text
            )

            assert v == "Stanley"

            last_row = results.get_corerow_by_id("782700656")
            m = last_row.source_metadata

            assert isinstance(m, ET.Element)
            v = m.find("dataset").find("language").text
            assert v == "en"

    def test_unknown_archive_format(self):
        """ Ensure InvalidArchive is raised when passed file is not a .zip nor .tgz."""
        invalid_origin_file = tempfile.NamedTemporaryFile(delete=False)

        with pytest.raises(InvalidArchive):
            with DwCAReader(invalid_origin_file.name):
                pass

        invalid_origin_file.close()

    def test_orphaned_extension_rows_noext(self):
        """ orphaned_extension_rows returns {} when there's no extensions."""
        # Archive without extensions: we expect {}
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            assert {} == dwca.orphaned_extension_rows()

    def test_orphaned_extension_rows_no_orphans(self):
        # Archive with extensions, but no orphaned extension rows

        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            expected = {"description.txt": {}, "vernacularname.txt": {}}
            assert expected == dwca.orphaned_extension_rows()

    def test_orphaned_extension_rows(self):
        # Archive with extensions and orphaned rows
        with DwCAReader(sample_data_path("dwca-orphaned-rows.zip")) as dwca:
            expected = {
                "description.txt": {u"5": [3, 4], u"6": [5]},
                "vernacularname.txt": {u"7": [4]},
            }
            assert expected == dwca.orphaned_extension_rows()

    def test_whitespace_before_xml_tag(self):
        """Ensure we can parse archives with whitespace before XML tag."""

        # The next line will throw an exception if metadata.xml can't be parsed
        DwCAReader(sample_data_path("gbif-results-whitespace-in-xml.zip"))


if __name__ == "__main__":
    unittest.main()
