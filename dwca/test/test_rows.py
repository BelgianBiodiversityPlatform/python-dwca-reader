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

    def test_equal_rows_hash_equally(self):
        # Uses two independently-fetched (but equal) CoreRow instances from the *same* reader,
        # rather than from two separate readers. DataFileDescriptor has no __eq__ of its own, so
        # instances from two separate readers never compare equal (identity-based comparison) -
        # that is a pre-existing bug unrelated to hashing, out of scope for this fix. Within a
        # single reader, descriptor is the same shared instance, so this still genuinely exercises
        # "two distinct objects that compare equal must hash equal".
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            one = dwca.rows[0]
            two = dwca.rows[0]

            assert one is not two
            assert one == two
            assert hash(one) == hash(two)
