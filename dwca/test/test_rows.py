import unittest

from dwca.read import DwCAReader
from dwca.rows import csv_line_to_fields
from .helpers import sample_data_path


class TestUtils(unittest.TestCase):
    def test_csv_line_to_fields(self):
        raw_fields = csv_line_to_fields('field 1,"field 2, with comma",field 3', '\n', ',', '"')
        assert raw_fields[0] == "field 1"
        assert raw_fields[1] == "field 2, with comma"
        assert raw_fields[2] == "field 3"


class TestCoreRow(unittest.TestCase):
    def test_position(self):
        # Test with archives with and without headers:
        archives_to_test = (sample_data_path('dwca-simple-test-archive.zip'), sample_data_path('dwca-noheaders-1.zip'))

        for archive_path in archives_to_test:
            with DwCAReader(archive_path) as dwca:
                for i, row in enumerate(dwca):
                    assert i == row.position


class TestExtensionRow(unittest.TestCase):
    def test_position(self):

        with DwCAReader(sample_data_path('dwca-2extensions.zip')) as dwca:
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
