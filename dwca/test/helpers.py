# -*- coding: utf-8 -*-

import os


def _sample_data_path(filename):
    return os.path.join(os.path.dirname(__file__), 'sample_files', filename)

GBIF_RESULTS_PATH = _sample_data_path('gbif-results.zip')
BASIC_ARCHIVE_PATH = _sample_data_path('dwca-simple-test-archive.zip')
NOHEADERS1_PATH = _sample_data_path('dwca-noheaders-1.zip')
NOHEADERS2_PATH = _sample_data_path('dwca-noheaders-2.zip')
DEFAULT_VAL_PATH = _sample_data_path('dwca-test-default.zip')
EXTENSION_ARCHIVE_PATH = _sample_data_path('dwca-star-test-archive.zip')
MULTIEXTENSIONS_ARCHIVE_PATH = _sample_data_path('dwca-2extensions.zip')
IDS_ARCHIVE_PATH = _sample_data_path('dwca-ids.zip')
UTF8EOL_ARCHIVE_PATH = _sample_data_path('dwca-utf8-eol-test.zip')
DIRECTORY_ARCHIVE_PATH = _sample_data_path('dwca-simple-folder')
DEFAULT_META_VALUES = _sample_data_path('dwca-meta-default-values')
