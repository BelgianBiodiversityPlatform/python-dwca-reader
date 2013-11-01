import os


def _sample_data_path(filename):
    return os.path.join(os.path.dirname(__file__), 'sample_files', filename)

GBIF_RESULTS_PATH = _sample_data_path('gbif-results.zip')
