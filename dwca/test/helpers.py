# -*- coding: utf-8 -*-

"""This module provides helpers for python-dwca-reader's test suite."""

import os


def _sample_data_path(filename):
    return os.path.join(os.path.dirname(__file__), 'sample_files', filename)

GBIF_RESULTS_PATH = _sample_data_path('gbif-results.zip')
BASIC_ARCHIVE_PATH = _sample_data_path('dwca-simple-test-archive.zip')
BASIC_ENCLOSED_ARCHIVE_PATH = _sample_data_path('dwca-simple-test-archive-enclosed.zip')
NOHEADERS1_PATH = _sample_data_path('dwca-noheaders-1.zip')
NOHEADERS2_PATH = _sample_data_path('dwca-noheaders-2.zip')
DEFAULT_VAL_PATH = _sample_data_path('dwca-test-default.zip')
EXTENSION_ARCHIVE_PATH = _sample_data_path('dwca-star-test-archive.zip')
MULTIEXTENSIONS_ARCHIVE_PATH = _sample_data_path('dwca-2extensions.zip')
IDS_ARCHIVE_PATH = _sample_data_path('dwca-ids.zip')
UTF8EOL_ARCHIVE_PATH = _sample_data_path('dwca-utf8-eol-test.zip')
DIRECTORY_ARCHIVE_PATH = _sample_data_path('dwca-simple-dir')
DIRECTORY_CSV_QUOTE_ARCHIVE_PATH = _sample_data_path('dwca-csv-quote-dir')
DEFAULT_META_VALUES = _sample_data_path('dwca-meta-default-values')
INVALID_LACKS_METADATA = _sample_data_path('dwca-invalid-lacks-metadata')
MISSINGMETA_PATH = _sample_data_path('gbif-results-lacks-s-metadata.zip')
SUBDIR_ARCHIVE_PATH = _sample_data_path('dwca-simple-subdir.zip')
SIMPLE_CSV = _sample_data_path('dwca-simple-csv.zip')
SIMPLE_CSV_EML = _sample_data_path('dwca-simple-csv-eml.zip')
SIMPLE_CSV_DOS = _sample_data_path('dwca-simple-csv-dos.zip')
INVALID_SIMPLE_TOOMUCH = _sample_data_path('dwca-invalid-simple-toomuch.zip')
INVALID_SIMPLE_TWO = _sample_data_path('dwca-invalid-simple-two.zip')
SIMPLE_CSV_NOTENCLOSED = _sample_data_path('dwca-simple-csv-notenclosed.zip')
NOMETADATA_PATH = _sample_data_path('dwca-nometadata.zip')
DEFAULT_METADATA_FILENAME = _sample_data_path('dwca-default-metadata-filename.zip')
BASIC_ARCHIVE_TGZ_PATH = _sample_data_path('dwca-simple-test-archive.tgz')
INVALID_DESCRIPTOR = _sample_data_path('dwca-malformed-descriptor')
DWCA_ORPHANED_ROWS = _sample_data_path('dwca-orphaned-rows.zip')
