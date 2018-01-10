# -*- coding: utf-8 -*-

"""Helpers for the test suite."""

import os


def sample_data_path(filename):
    return os.path.join(os.path.dirname(__file__), 'sample_files', filename)
