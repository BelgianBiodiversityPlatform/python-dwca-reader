import os
import unittest
import xml.etree.ElementTree as ET
from array import array

from dwca.descriptors import DataFileDescriptor
from dwca.files import CSVDataFile
from dwca.read import DwCAReader
from .helpers import sample_data_path
import pytest


class TestCSVDataFile(unittest.TestCase):
    def test_get_line_at_position_raises_indexerror(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            with pytest.raises(IndexError):
                dwca.core_file.get_row_by_position(10000)

    def test_string_representation(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            extension_files = dwca.extension_files

            assert "taxon.txt" == str(dwca.core_file)
            assert "description.txt" == str(extension_files[0])
            assert "vernacularname.txt" == str(extension_files[1])

        # Also check with a simple archive
        with DwCAReader(sample_data_path("dwca-simple-csv.zip")) as dwca:
            assert "0008333-160118175350007.csv" == str(dwca.core_file)

    def test_coreid_index(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            extension_files = dwca.extension_files

            core_txt = dwca.core_file
            description_txt = extension_files[0]
            vernacular_txt = extension_files[1]

            # coreid_index values are array("L") rather than lists. This is documented in the
            # property docstring and DwCAReader.orphaned_extension_rows() relies on it via
            # .tolist(), so it is part of the contract, not an implementation detail.
            expected_core = {
                "1": array("L", [0]),
                "2": array("L", [1]),
                "3": array("L", [2]),
                "4": array("L", [3]),
            }
            assert core_txt.coreid_index == expected_core

            expected_vernacular = {"1": array("L", [0, 1, 2]), "2": array("L", [3])}
            assert vernacular_txt.coreid_index == expected_vernacular

            expected_description = {"1": array("L", [0, 1]), "4": array("L", [2])}
            assert description_txt.coreid_index == expected_description

    def test_file_descriptor_attribute(self):
        """The instance of DataFileDescriptor passed to the constructor is available in .file_descriptor"""

        metaxml_section = r"""
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
        """

        descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )
        data_file = CSVDataFile(sample_data_path("dwca-simple-dir"), descriptor)

        assert data_file.file_descriptor == descriptor

    def test_lines_to_ignore_attribute(self):
        """.lines_to_ignore works as documented"""

        metaxml_section = r"""
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
        """

        descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )
        data_file = CSVDataFile(sample_data_path("dwca-simple-dir"), descriptor)

        assert data_file.lines_to_ignore == 1

        metaxml_section = r"""
                <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="3" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
                    <files>
                        <location>occurrence.txt</location>
                    </files>
                    <id index="0" />
                    <field index="1" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
                    <field index="2" term="http://rs.tdwg.org/dwc/terms/locality"/>
                    <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
                    <field index="4" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
                </core>
                """

        descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )
        data_file = CSVDataFile(sample_data_path("dwca-simple-dir"), descriptor)

        assert data_file.lines_to_ignore == 3

    def test_close(self):
        metaxml_section = r"""
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files><location>occurrence.txt</location></files>
            <id index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/locality"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
        </core>
        """

        descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )
        data_file = CSVDataFile(sample_data_path("dwca-simple-dir"), descriptor)

        data_file.close()

        with pytest.raises(ValueError):
            # It's not possible anymore to access the data because file has been closed.
            data_file.get_row_by_position(1)

    def test_iterate(self):
        metaxml_section = r"""
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files><location>occurrence.txt</location></files>
                <id index="0" />
                <field index="1" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
                <field index="2" term="http://rs.tdwg.org/dwc/terms/locality"/>
                <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
                <field index="4" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
            </core>
         """

        descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )
        data_file = CSVDataFile(sample_data_path("dwca-simple-dir"), descriptor)

        for row in data_file:
            assert isinstance(row, str)


class TestStreamingIteration(unittest.TestCase):
    def test_iter_rows_yields_every_row_in_order(self):
        with DwCAReader(sample_data_path("dwca-ids.zip")) as dwca:
            rows = list(dwca.core_file.iter_rows())

        # Row IDs appear in the core file in this order: 4-1-3-2
        assert ["4", "1", "3", "2"] == [row.id for row in rows]
        assert [0, 1, 2, 3] == [row.position for row in rows]

    def test_iter_rows_agrees_with_random_access(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            for data_file in [dwca.core_file] + dwca.extension_files:
                streamed = list(data_file.iter_rows())
                seeked = [
                    data_file.get_row_by_position(i) for i in range(len(streamed))
                ]

                assert [r.data for r in streamed] == [r.data for r in seeked]
                assert [r.raw_fields for r in streamed] == [
                    r.raw_fields for r in seeked
                ]

    def test_iter_rows_can_be_nested(self):
        """Each call gets its own stream, so concurrent passes do not interfere."""
        with DwCAReader(sample_data_path("dwca-ids.zip")) as dwca:
            pairs = [
                (outer.id, inner.id)
                for outer in dwca.core_file.iter_rows()
                for inner in dwca.core_file.iter_rows()
            ]

        assert 16 == len(pairs)

    def test_iter_rows_on_a_quoted_archive(self):
        with DwCAReader(sample_data_path("dwca-csv-quote-dir")) as dwca:
            rows = list(dwca.core_file.iter_rows())

        assert 2 == len(rows)

    def test_raw_line_iteration_skips_every_header_line(self):
        """readlines() takes a byte-size hint, not a line count, so with two header lines
        the second used to leak through as data."""
        from .archive_builder import build_archive, temp_archive_dir

        path = build_archive(
            temp_archive_dir(self),
            rows=[["1", "Borneo"], ["2", "Mumbai"]],
            ignore_header_lines=2,
            header_rows=[["idA", "locA"], ["idB", "locB"]],
        )
        with DwCAReader(path) as dwca:
            lines = list(dwca.core_file)

            assert 2 == len(lines)
            assert lines[0].startswith("1\t")
            assert lines[1].startswith("2\t")


class TestLineOffsets(unittest.TestCase):
    def test_opening_an_archive_does_not_build_the_index(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            assert dwca.core_file._line_offsets is None

            dwca.core_file.get_row_by_position(0)

            assert dwca.core_file._line_offsets is not None

    def test_offsets_survive_an_undecodable_byte(self):
        from .archive_builder import build_archive, temp_archive_dir

        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=2,
            raw_payload=b"1\tcaf\xe9\n2\tMumbai\n3\tBorneo\n",
        )
        with DwCAReader(path) as dwca:
            term = "http://rs.tdwg.org/dwc/terms/term1"

            assert "Mumbai" == dwca.core_file.get_row_by_position(1).data[term]
            assert "Borneo" == dwca.core_file.get_row_by_position(2).data[term]

    def test_offsets_with_dos_line_endings(self):
        from .archive_builder import build_archive, temp_archive_dir

        path = build_archive(
            temp_archive_dir(self),
            rows=[["1", "Borneo"], ["2", "Mumbai"]],
            lines_terminated_by="\r\n",
        )
        with DwCAReader(path) as dwca:
            term = "http://rs.tdwg.org/dwc/terms/term1"

            assert "Borneo" == dwca.core_file.get_row_by_position(0).data[term]
            assert "Mumbai" == dwca.core_file.get_row_by_position(1).data[term]

    def test_offsets_are_correct_across_a_chunk_boundary(self):
        """The scanner reads in chunks, so a terminator can straddle two reads."""
        from dwca.files import _build_line_offsets
        from .archive_builder import build_archive, temp_archive_dir

        rows = [[str(i), "locality-" + str(i)] for i in range(5000)]
        path = build_archive(temp_archive_dir(self), rows=rows)

        data_path = os.path.join(path, "occurrence.txt")
        reference = _build_line_offsets(data_path, "utf-8", "\n")
        chunked = _build_line_offsets(data_path, "utf-8", "\n", chunk_size=7)

        assert 5000 == len(reference)
        assert list(reference) == list(chunked)

    def test_a_zero_byte_core_file_has_no_rows(self):
        """A zero-byte file must report no lines at all, not one spurious empty line."""
        from .archive_builder import build_archive, temp_archive_dir

        path = build_archive(
            temp_archive_dir(self), rows=[], columns=2, raw_payload=b""
        )
        with DwCAReader(path) as dwca:
            with pytest.raises(IndexError):
                dwca.core_file.get_row_by_position(0)
