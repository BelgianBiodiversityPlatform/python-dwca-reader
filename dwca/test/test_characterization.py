"""Characterization tests: these pin CURRENT behavior so a rewrite of the parsing
engine produces a visible diff rather than a silent change.

Tests marked with a `# CHARACTERIZATION: wrong, see B<n>` comment assert behavior we
know to be incorrect. Phase 1 changes them deliberately.
"""

import unittest

import pytest

from dwca.exceptions import InvalidArchive
from dwca.read import DwCAReader

from .archive_builder import build_archive, temp_archive_dir

TERM0 = "http://rs.tdwg.org/dwc/terms/term0"
TERM1 = "http://rs.tdwg.org/dwc/terms/term1"


class TestArchiveBuilder(unittest.TestCase):
    def test_builds_a_readable_archive(self):
        path = build_archive(
            temp_archive_dir(self), rows=[["1", "Borneo"], ["2", "Mumbai"]]
        )

        with DwCAReader(path) as dwca:
            rows = list(dwca)

        assert 2 == len(rows)
        assert "1" == rows[0].id
        assert "Borneo" == rows[0].data[TERM1]
        assert "Mumbai" == rows[1].data[TERM1]

    def test_raw_payload_is_written_verbatim(self):
        path = build_archive(
            temp_archive_dir(self), rows=[], columns=2, raw_payload=b"1\tBorneo\n"
        )

        with DwCAReader(path) as dwca:
            assert ["Borneo"] == [row.data[TERM1] for row in dwca]
