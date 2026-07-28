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


class TestHeaderLines(unittest.TestCase):
    """ignoreHeaderLines, for BOTH access paths.

    The two paths disagree today: DwCAReader iteration goes through get_row_by_position()
    (which offsets correctly), while CSVDataFile.__iter__ uses readlines(hint) where the
    argument is a byte-size hint rather than a line count. coreid_index is built from the
    second path, so it picks up leftover header lines.
    """

    def _archive(self, ignore_header_lines, header_rows):
        return build_archive(
            temp_archive_dir(self),
            rows=[["1", "Borneo"], ["2", "Mumbai"]],
            ignore_header_lines=ignore_header_lines,
            header_rows=header_rows,
        )

    def test_no_header(self):
        path = self._archive(0, [])

        with DwCAReader(path) as dwca:
            assert ["1", "2"] == [row.id for row in dwca]
            assert "1" == dwca.core_file.get_row_by_position(0).id

    def test_one_header(self):
        path = self._archive(1, [["id", "locality"]])

        with DwCAReader(path) as dwca:
            assert ["1", "2"] == [row.id for row in dwca]
            assert "1" == dwca.core_file.get_row_by_position(0).id
            assert {"1": [0], "2": [1]} == {
                k: list(v) for k, v in dwca.core_file.coreid_index.items()
            }

    def test_two_headers_iteration_and_random_access_agree(self):
        path = self._archive(2, [["idA", "locA"], ["idB", "locB"]])

        with DwCAReader(path) as dwca:
            assert ["1", "2"] == [row.id for row in dwca]
            assert "1" == dwca.core_file.get_row_by_position(0).id

            # CHARACTERIZATION: wrong, see B1. readlines() takes a byte-size hint, not a
            # line count, so the second header line leaks into the index as a data row.
            assert {"idB": [0], "1": [1], "2": [2]} == {
                k: list(v) for k, v in dwca.core_file.coreid_index.items()
            }


class TestLineTerminators(unittest.TestCase):
    def test_unix_terminator(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[["1", "Borneo"], ["2", "Mumbai"]],
            lines_terminated_by="\n",
        )

        with DwCAReader(path) as dwca:
            assert ["Borneo", "Mumbai"] == [row.data[TERM1] for row in dwca]

    def test_dos_terminator(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[["1", "Borneo"], ["2", "Mumbai"]],
            lines_terminated_by="\r\n",
        )

        with DwCAReader(path) as dwca:
            assert ["Borneo", "Mumbai"] == [row.data[TERM1] for row in dwca]

    def test_multichar_terminator_is_rejected_by_python_io(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[["1", "Borneo"]],
            lines_terminated_by="@@\n",
        )

        # io.open() only accepts None, '', '\n', '\r' and '\r\n' as newline, so an archive
        # declaring anything else cannot be opened at all. Pinned so a rewrite that moves
        # off the newline= parameter has to decide what to do about it.
        with pytest.raises(ValueError):
            DwCAReader(path)

    def test_unicode_next_line_does_not_split_a_row(self):
        """U+0085 must not be treated as a line break (issue #20).

        str.splitlines() splits on U+0085 but io line iteration does not, so any rewrite
        using splitlines() would silently double the row count here.
        """
        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=2,
            raw_payload=b"1\tbefore\xc2\x85after\n",  # U+0085 encoded as UTF-8
        )

        with DwCAReader(path) as dwca:
            rows = list(dwca)

        assert 1 == len(rows)
        assert "before\u0085after" == rows[0].data[TERM1]


class TestEncodings(unittest.TestCase):
    def test_windows1252_data_file(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[["1", "caf\xe9"], ["2", "na\xefve"]],
            encoding="windows-1252",
        )

        with DwCAReader(path) as dwca:
            assert ["caf\xe9", "na\xefve"] == [row.data[TERM1] for row in dwca]

    def test_latin1_data_file(self):
        path = build_archive(
            temp_archive_dir(self), rows=[["1", "caf\xe9"]], encoding="latin-1"
        )

        with DwCAReader(path) as dwca:
            assert ["caf\xe9"] == [row.data[TERM1] for row in dwca]

    def test_utf8_bom_leaks_into_the_first_field(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=2,
            raw_payload=b"\xef\xbb\xbf1\tBorneo\n",  # UTF-8 byte order mark
        )

        with DwCAReader(path) as dwca:
            rows = list(dwca)

        # CHARACTERIZATION: the encoding is "utf-8", not "utf-8-sig", so the byte order
        # mark becomes part of the id. A rewrite adding BOM handling changes this
        # deliberately.
        assert "\ufeff1" == rows[0].id

    def test_undecodable_byte_desynchronises_random_access(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=2,
            raw_payload=b"1\tcaf\xe9\n2\tMumbai\n3\tBorneo\n",
        )

        with DwCAReader(path) as dwca:
            # Row 0 is fine: the offset index has not drifted yet.
            assert "caf\ufffd" == dwca.core_file.get_row_by_position(0).data[TERM1]

            # CHARACTERIZATION: wrong, see B2. errors="replace" turns the undecodable byte
            # into U+FFFD, which re-encodes to three bytes instead of one, so every offset
            # after it is two bytes too large. The seek lands mid-row and the truncated row
            # no longer has enough columns.
            with pytest.raises(InvalidArchive):
                dwca.core_file.get_row_by_position(1)

            # CHARACTERIZATION: wrong, see B2. Iteration is broken too, because today it is
            # implemented as repeated get_row_by_position() calls. After Phase 1 this reads
            # ["caf\ufffd", "Mumbai", "Borneo"], which is the whole point of the fix.
            with pytest.raises(InvalidArchive):
                list(dwca)
