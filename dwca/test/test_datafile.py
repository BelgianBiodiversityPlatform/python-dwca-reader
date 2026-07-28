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

    def test_multibyte_utf8_and_an_embedded_newline_in_the_same_file(self):
        """_read_record() must use a byte-accurate read.

        offsets are byte offsets, but a text stream's read(n) counts characters, so a
        naive `self._file_stream.read(next_offset - start)` would desync as soon as the
        file contains a character that takes more than one byte in UTF-8 - truncating or
        over-reading the record. This archive puts multi-byte characters (which make
        byte count and character count diverge) and a quoted embedded newline (which
        makes a record span more than one physical line) in the same file, so both
        failure modes would have to hold simultaneously to pass.
        """
        from .archive_builder import build_archive, temp_archive_dir

        # ACCENTED_E is a 2-byte UTF-8 character, SNOWMAN a 3-byte one: both make byte
        # count and character count diverge. Row 2's third field is quoted and contains
        # an embedded newline, so that record spans two physical lines.
        ACCENTED_E = "\xe9"
        SNOWMAN = "\u2603"
        payload = (
            "1,caf" + ACCENTED_E + "," + SNOWMAN + "\n"
            '2,"multi\nline",' + SNOWMAN + ACCENTED_E + "\n"
            "3," + ACCENTED_E * 3 + ",end\n"
        ).encode("utf-8")
        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=3,
            raw_payload=payload,
            fields_terminated_by=",",
            fields_enclosed_by='"',
        )

        with DwCAReader(path) as dwca:
            streamed = [row.raw_fields for row in dwca]
            seeked = [
                dwca.core_file.get_row_by_position(i).raw_fields
                for i in range(len(streamed))
            ]

        assert [
            ["1", "caf" + ACCENTED_E, SNOWMAN],
            ["2", "multi\nline", SNOWMAN + ACCENTED_E],
            ["3", ACCENTED_E * 3, "end"],
        ] == streamed
        assert streamed == seeked


class TestIterTerms(unittest.TestCase):
    def test_matches_the_row_api(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            terms = sorted(dwca.core_file.file_descriptor.terms)

            via_rows = [tuple(row.data[t] for t in terms) for row in dwca]
            via_terms = list(dwca.core_file.iter_terms(terms))

        assert via_rows == via_terms

    def test_works_on_an_extension_file(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            extension = dwca.extension_files[0]
            terms = sorted(extension.file_descriptor.terms)

            via_rows = [tuple(r.data[t] for t in terms) for r in extension.iter_rows()]
            via_terms = list(extension.iter_terms(terms))

        assert via_rows == via_terms

    def test_subset_of_columns(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            values = list(
                dwca.core_file.iter_terms(["http://rs.tdwg.org/dwc/terms/locality"])
            )

        assert [("Borneo",), ("Mumbai",)] == values

    def test_unknown_term_raises_before_reading_anything(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            with pytest.raises(ValueError):
                dwca.core_file.iter_terms(["http://rs.tdwg.org/dwc/terms/nope"])

    def test_default_only_term(self):
        with DwCAReader(sample_data_path("dwca-test-default.zip")) as dwca:
            values = list(
                dwca.core_file.iter_terms(["http://rs.tdwg.org/dwc/terms/country"])
            )

        assert [("Belgium",), ("Belgium",)] == values

    def test_can_be_nested(self):
        with DwCAReader(sample_data_path("dwca-ids.zip")) as dwca:
            term = ["http://rs.tdwg.org/dwc/terms/family"]
            pairs = [
                (a, b)
                for a in dwca.core_file.iter_terms(term)
                for b in dwca.core_file.iter_terms(term)
            ]

        assert 16 == len(pairs)


class TestIterTermsKeyColumns(unittest.TestCase):
    def test_core_id_is_reachable(self):
        """dwca-ids.zip declares no <field> for its id column."""
        with DwCAReader(sample_data_path("dwca-ids.zip")) as dwca:
            from_rows = [row.id for row in dwca]
            from_terms = [values[0] for values in dwca.iter_terms(["id"])]

        assert ["4", "1", "3", "2"] == from_rows
        assert from_rows == from_terms

    def test_extension_coreid_is_reachable(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            extension = dwca.extension_files[0]

            from_rows = [row.core_id for row in extension.iter_rows()]
            from_terms = [values[0] for values in extension.iter_terms(["coreid"])]

        assert from_rows == from_terms

    def test_key_column_mixes_with_real_terms_in_the_requested_order(self):
        order = "http://rs.tdwg.org/dwc/terms/order"
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            got = list(dwca.iter_terms([order, "id"]))
            expected = [(row.data[order], row.id) for row in dwca]

        assert expected == got

    def test_id_is_still_unknown_when_the_file_has_no_id_column(self):
        """A metafile-less archive has no id column, so the name must not resolve."""
        with DwCAReader(sample_data_path("dwca-simple-csv.zip")) as dwca:
            with pytest.raises(ValueError):
                dwca.iter_terms(["id"])

    def test_coreid_is_unknown_on_a_core_file(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            with pytest.raises(ValueError):
                dwca.iter_terms(["coreid"])


class TestClosedFileGuarantee(unittest.TestCase):
    def test_iteration_after_close_raises(self):
        """close() documents that content is not accessible in any way afterwards."""
        with DwCAReader(sample_data_path("dwca-simple-dir")) as dwca:
            data_file = dwca.core_file

            assert list(data_file.iter_rows())  # works while open
            data_file.close()

            with pytest.raises(ValueError):
                list(data_file.iter_rows())

    def test_reader_iteration_after_close_raises(self):
        dwca = DwCAReader(sample_data_path("dwca-simple-dir"))
        assert list(dwca)
        dwca.close()

        with pytest.raises(ValueError):
            list(dwca)
