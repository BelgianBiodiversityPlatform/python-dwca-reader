# -*- coding: utf-8 -*-

import unittest

from dwca.read import DwCAReader

from .helpers import MULTIEXTENSIONS_ARCHIVE_PATH


class TestCSVDataFile(unittest.TestCase):
    def test_coreid_index(self):
        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            extension_files = dwca._extensionfiles

            description_txt = extension_files[0]
            vernacular_txt = extension_files[1]

            expected_vernacular = {
                '1': [0, 1, 2],
                '2': [3]
            }
            self.assertEqual(vernacular_txt.coreid_index, expected_vernacular)

            expected_description = {
                '1': [0, 1],
                '4': [2]
            }
            self.assertEqual(description_txt.coreid_index, expected_description)

            with self.assertRaises(AttributeError):
                dwca._corefile.coreid_index
            
