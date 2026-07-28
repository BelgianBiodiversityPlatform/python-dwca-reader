import unittest

from dwca.read import DwCAReader
from dwca.rows import csv_line_to_fields
from .helpers import sample_data_path


class TestUtils(unittest.TestCase):
    def test_csv_line_to_fields(self):
        raw_fields = csv_line_to_fields(
            'field 1,"field 2, with comma",field 3', "\n", ",", '"'
        )
        assert raw_fields[0] == "field 1"
        assert raw_fields[1] == "field 2, with comma"
        assert raw_fields[2] == "field 3"


class TestCoreRow(unittest.TestCase):
    def test_position(self):
        # Test with archives with and without headers:
        archives_to_test = (
            sample_data_path("dwca-simple-test-archive.zip"),
            sample_data_path("dwca-noheaders-1.zip"),
        )

        for archive_path in archives_to_test:
            with DwCAReader(archive_path) as dwca:
                for i, row in enumerate(dwca):
                    assert i == row.position


class TestExtensionRow(unittest.TestCase):
    def test_position(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            ostrich = dwca.rows[0]

            description_first_line = ostrich.extensions[0]
            description_second_line = ostrich.extensions[1]

            vernacular_first_line = ostrich.extensions[2]
            vernacular_second_line = ostrich.extensions[3]
            vernacular_third_line = ostrich.extensions[4]

            assert 0 == description_first_line.position
            assert 1 == description_second_line.position

            assert 0 == vernacular_first_line.position
            assert 1 == vernacular_second_line.position
            assert 2 == vernacular_third_line.position


class TestRowHashing(unittest.TestCase):
    def test_core_rows_are_hashable(self):
        """CHANGES.txt has claimed rows are hashable since 0.3.3, but __key() embedded a
        dict and a list, so hash() raised TypeError for every row."""
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            rows = dwca.rows

            assert len(set(rows)) == len(rows)

    def test_extension_rows_are_hashable(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            extension_rows = dwca.rows[0].extensions

            assert len(set(extension_rows)) == len(extension_rows)

    def test_unlinked_core_rows_are_comparable(self):
        """A CoreRow obtained directly from CSVDataFile.get_row_by_position() (rather than by
        iterating the DwCAReader) is never linked to extension files or source metadata, so
        self.extension_data_files and self.source_metadata don't exist on it. __key() used to
        access self.extensions and self.source_metadata unconditionally, so hash()/__eq__ on
        such a row raised AttributeError - which set() and put in a set both trigger."""
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            one = dwca.core_file.get_row_by_position(0)
            two = dwca.core_file.get_row_by_position(0)

            assert one is not two
            assert one == two
            assert hash(one) == hash(two)
            assert len({one, two}) == 1

    def test_equal_rows_hash_equally(self):
        # Two distinct objects that compare equal must hash equal.
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            one = dwca.rows[0]
            two = dwca.rows[0]

            assert one is not two
            assert one == two
            assert hash(one) == hash(two)


class TestRowEquality(unittest.TestCase):
    """Rows compare by value, including across readers.

    Row equality used to embed the DataFileDescriptor, which compared by object identity: rows
    read from two DwCAReader instances over the same archive never compared equal, even with
    identical data, raw_fields, id, position and rowtype.
    """

    def test_core_rows_from_two_readers_over_the_same_archive_are_equal(self):
        path = sample_data_path("dwca-2extensions.zip")

        with DwCAReader(path) as one, DwCAReader(path) as two:
            row_one = one.rows[0]
            row_two = two.rows[0]

            assert row_one.descriptor is not row_two.descriptor
            assert row_one == row_two
            assert not (row_one != row_two)
            assert hash(row_one) == hash(row_two)
            assert len({row_one, row_two}) == 1

    def test_extension_rows_from_two_readers_over_the_same_archive_are_equal(self):
        path = sample_data_path("dwca-2extensions.zip")

        with DwCAReader(path) as one, DwCAReader(path) as two:
            row_one = one.rows[0].extensions[0]
            row_two = two.rows[0].extensions[0]

            assert row_one.descriptor is not row_two.descriptor
            assert row_one == row_two
            assert hash(row_one) == hash(row_two)
            assert len({row_one, row_two}) == 1

    def test_different_core_rows_are_not_equal(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            assert dwca.rows[0] != dwca.rows[1]

    def test_comparing_a_core_row_to_an_extension_row_returns_false(self):
        """__key() is name-mangled, so CoreRow.__eq__ used to call other._CoreRow__key() on an
        ExtensionRow, which doesn't have it: the comparison raised AttributeError instead of
        returning False."""
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            core_row = dwca.rows[0]
            extension_row = core_row.extensions[0]

            assert core_row != extension_row
            assert extension_row != core_row
            assert not (core_row == extension_row)

    def test_comparing_rows_with_other_types_returns_false(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            core_row = dwca.rows[0]
            extension_row = core_row.extensions[0]

            for row in (core_row, extension_row):
                assert row != "not a row"
                assert row != 42
                assert row != None  # noqa: E711 - we're testing __eq__, not identity
                assert not (row == "not a row")

    def test_rows_of_different_types_can_share_a_set(self):
        """A CoreRow and an ExtensionRow landing in the same hash bucket must compare, not
        raise."""
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            core_row = dwca.rows[0]
            extension_row = core_row.extensions[0]

            assert len({core_row, extension_row}) == 2


class TestRowFromFields(unittest.TestCase):
    def _descriptor(self):
        import xml.etree.ElementTree as ET

        from dwca.descriptors import DataFileDescriptor

        section = """
        <core encoding="utf-8" fieldsTerminatedBy="\\t" linesTerminatedBy="\\n" \
fieldsEnclosedBy="" ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files><location>occurrence.txt</location></files>
            <id index="0" />
            <field index="0" term="http://x/id"/>
            <field index="1" term="http://x/locality"/>
        </core>
        """
        return DataFileDescriptor.make_from_metafile_section(ET.fromstring(section))

    def test_from_fields_matches_the_raw_line_constructor(self):
        from dwca.rows import CoreRow

        descriptor = self._descriptor()

        from_line = CoreRow("1\tBorneo\n", 0, descriptor)
        from_fields = CoreRow.from_fields(["1", "Borneo"], 0, descriptor)

        assert from_line.data == from_fields.data
        assert from_line.raw_fields == from_fields.raw_fields
        assert from_line.id == from_fields.id
        assert from_line.position == from_fields.position
        assert from_line.rowtype == from_fields.rowtype

    def test_from_fields_returns_the_right_class(self):
        from dwca.rows import CoreRow

        row = CoreRow.from_fields(["1", "Borneo"], 0, self._descriptor())

        assert isinstance(row, CoreRow)


class TestCsvLineToFieldsQuoting(unittest.TestCase):
    def test_quote_at_the_edge_of_content_is_preserved(self):
        """The csv module already un-doubles escaped quotes; stripping afterwards ate a
        legitimate leading or trailing quote from the field's own content."""
        assert ['1', 'say "hi"'] == csv_line_to_fields(
            '"1","say ""hi"""', "\n", ",", '"'
        )
        assert ['1', '"hi" she said'] == csv_line_to_fields(
            '"1","""hi"" she said"', "\n", ",", '"'
        )

    def test_delimiter_inside_a_quoted_field_still_works(self):
        """Regression guard for the v0.11.0 fix."""
        assert ["field 1", "field 2, with comma", "field 3"] == csv_line_to_fields(
            'field 1,"field 2, with comma",field 3', "\n", ",", '"'
        )

    def test_unenclosed_line_keeps_quote_characters(self):
        assert ["1", '"betta" splendens'] == csv_line_to_fields(
            '1\t"betta" splendens', "\n", "\t", ""
        )
