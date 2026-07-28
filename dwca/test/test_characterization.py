"""Characterization tests: these pin CURRENT behavior so a rewrite of the parsing
engine produces a visible diff rather than a silent change.

Tests marked with a `# CHARACTERIZATION: wrong, see B<n>` comment assert behavior we
know to be incorrect. Phase 1 changes them deliberately.
"""

import unittest
from array import array

import pytest

from dwca.exceptions import InvalidArchive
from dwca.read import DwCAReader

from .archive_builder import build_archive, temp_archive_dir
from .helpers import sample_data_path

TERM1 = "http://rs.tdwg.org/dwc/terms/term1"
VERNACULAR_TERM = "http://rs.tdwg.org/dwc/terms/vernacularName"


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

    The two paths used to disagree: DwCAReader iteration went through get_row_by_position()
    (which offset correctly), while CSVDataFile.__iter__ used readlines(hint), where the
    argument is a byte-size hint rather than a line count. coreid_index was built from the
    second path, so it used to pick up leftover header lines. Both paths now agree.
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

            assert {"1": [0], "2": [1]} == {
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

    def test_crlf_file_declaring_a_bare_lf_terminator(self):
        """A CRLF file whose Metafile declares "\\n" must not leave a stray CR on the row.

        This combination is common rather than exotic: git checks text files out with CRLF on
        Windows, so an archive committed to a repository hits it without anyone choosing it.
        The library's own dwca-simple-dir fixture behaves this way on a Windows runner, which
        is how a regression here was caught.
        """
        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=2,
            raw_payload=b"1\tBorneo\r\n2\tMumbai\r\n",
        )

        with DwCAReader(path) as dwca:
            streamed = [row.data[TERM1] for row in dwca]
            seeked = [
                dwca.core_file.get_row_by_position(i).data[TERM1] for i in range(2)
            ]

        assert ["Borneo", "Mumbai"] == streamed
        assert streamed == seeked

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

        # Surprising but not a known bug: the encoding is "utf-8", not "utf-8-sig", so the
        # byte order mark becomes part of the id instead of being stripped. A rewrite adding
        # BOM handling would change this deliberately.
        assert "\ufeff1" == rows[0].id

    def test_undecodable_byte_does_not_break_random_access(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=2,
            raw_payload=b"1\tcaf\xe9\n2\tMumbai\n3\tBorneo\n",
        )

        with DwCAReader(path) as dwca:
            # Row 0 is fine: the offset index has not drifted yet.
            assert "caf\ufffd" == dwca.core_file.get_row_by_position(0).data[TERM1]

            assert "Mumbai" == dwca.core_file.get_row_by_position(1).data[
                "http://rs.tdwg.org/dwc/terms/term1"
            ]

            assert ["caf\ufffd", "Mumbai", "Borneo"] == [
                row.data["http://rs.tdwg.org/dwc/terms/term1"] for row in dwca
            ]


class TestQuoting(unittest.TestCase):
    def _read_localities(self, payload):
        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=2,
            fields_terminated_by=",",
            fields_enclosed_by='"',
            raw_payload=payload,
        )

        with DwCAReader(path) as dwca:
            return [row.data[TERM1] for row in dwca]

    def test_delimiter_inside_a_quoted_field(self):
        """Regression guard for the v0.11.0 fix. Any hand-rolled parser breaks this."""
        assert ["plain, with comma"] == self._read_localities(
            b'"1","plain, with comma"\n'
        )

    def test_quote_in_the_middle_of_content(self):
        assert ['say "hi" there'] == self._read_localities(b'"1","say ""hi"" there"\n')

    def test_quote_at_the_edge_of_content_is_preserved(self):
        assert ['say "hi"'] == self._read_localities(b'"1","say ""hi"""\n')
        assert ['"hi" she said'] == self._read_localities(b'"1","""hi"" she said"\n')

    def test_quote_characters_are_kept_when_the_archive_declares_no_enclosure(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=2,
            raw_payload=b'1\t"betta" splendens\n',
        )

        with DwCAReader(path) as dwca:
            assert '"betta" splendens' == list(dwca)[0].data[TERM1]


class TestDegenerateRows(unittest.TestCase):
    def test_row_with_fewer_columns_than_declared(self):
        path = build_archive(
            temp_archive_dir(self), rows=[], columns=3, raw_payload=b"1\tBorneo\n"
        )

        with DwCAReader(path) as dwca:
            with pytest.raises(InvalidArchive):
                list(dwca)

    def test_row_with_more_columns_than_declared(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=2,
            raw_payload=b"1\tBorneo\textra\n",
        )

        with DwCAReader(path) as dwca:
            rows = list(dwca)

        # Extra columns are ignored by data but kept in raw_fields.
        assert "Borneo" == rows[0].data[TERM1]
        assert ["1", "Borneo", "extra"] == rows[0].raw_fields

    def test_blank_line_in_the_middle(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=2,
            raw_payload=b"1\tBorneo\n\n2\tMumbai\n",
        )

        with DwCAReader(path) as dwca:
            with pytest.raises(InvalidArchive):
                list(dwca)

    def test_no_trailing_newline_at_eof(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=2,
            raw_payload=b"1\tBorneo\n2\tMumbai",
        )

        with DwCAReader(path) as dwca:
            assert ["Borneo", "Mumbai"] == [row.data[TERM1] for row in dwca]

    def test_empty_core_file(self):
        path = build_archive(
            temp_archive_dir(self), rows=[], columns=2, raw_payload=b""
        )

        with DwCAReader(path) as dwca:
            assert [] == list(dwca)
            assert [] == dwca.rows

    def test_header_only_core_file(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=2,
            ignore_header_lines=1,
            raw_payload=b"id\tlocality\n",
        )

        with DwCAReader(path) as dwca:
            assert [] == list(dwca)


class TestIterationSemantics(unittest.TestCase):
    def _archive(self):
        return build_archive(
            temp_archive_dir(self),
            rows=[["1", "Borneo"], ["2", "Mumbai"], ["3", "Paris"]],
        )

    def test_sequential_re_iteration(self):
        with DwCAReader(self._archive()) as dwca:
            assert 3 == len(list(dwca))
            assert 3 == len(list(dwca))

    def test_nested_iteration(self):
        with DwCAReader(self._archive()) as dwca:
            pairs = [(outer.id, inner.id) for outer in dwca for inner in dwca]

        assert 9 == len(pairs)

    def test_lookup_inside_a_loop(self):
        seen = []
        with DwCAReader(self._archive()) as dwca:
            for row in dwca:
                seen.append(row.id)
                assert "2" == dwca.get_corerow_by_id("2").id

        assert ["1", "2", "3"] == seen

    def test_random_access_interleaved_with_iteration_is_safe(self):
        with DwCAReader(self._archive()) as dwca:
            seen = []
            for row in dwca:
                seen.append(row.id)
                # This path is offset-based, so it does not disturb iteration.
                assert "1" == dwca.core_file.get_row_by_position(0).id

        assert ["1", "2", "3"] == seen


class TestExtensionFiles(unittest.TestCase):
    """extension= was never passed to build_archive by any test, so that whole branch of the
    builder was dead code, and every extension-bearing behavior below ran only on the three
    bundled sample archives, which all happen to share one configuration (utf-8, tab, no
    enclosure, ignoreHeaderLines="1"). CSVDataFile.coreid_index used to be built through
    CSVDataFile.__iter__ (the readlines(byte-hint) header bug, see TestHeaderLines above and
    B1), and get_all_rows_by_coreid() fed those positions into get_row_by_position(), which
    re-applied lines_to_ignore - exactly the seam the B1 bug lived in, and it was unpinned for
    extensions until this test was added. coreid_index is now built through iter_rows()
    instead, so that seam no longer exists here.
    """

    def _archive(self, **kwargs):
        return build_archive(
            temp_archive_dir(self),
            rows=[["1", "Borneo"], ["2", "Mumbai"]],
            extension=[["1", "elephant"], ["1", "tiger"], ["2", "monkey"]],
            **kwargs,
        )

    def test_coreid_index(self):
        path = self._archive()

        with DwCAReader(path) as dwca:
            index = dwca.extension_files[0].coreid_index

            assert {"1": array("L", [0, 1]), "2": array("L", [2])} == index

    def test_get_all_rows_by_coreid(self):
        path = self._archive()

        with DwCAReader(path) as dwca:
            ext = dwca.extension_files[0]

            several = ext.get_all_rows_by_coreid("1")
            assert ["elephant", "tiger"] == [r.data[VERNACULAR_TERM] for r in several]

            one = ext.get_all_rows_by_coreid("2")
            assert ["monkey"] == [r.data[VERNACULAR_TERM] for r in one]

            assert [] == ext.get_all_rows_by_coreid("unknown")

    def test_orphaned_extension_rows(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[["1", "Borneo"], ["2", "Mumbai"]],
            extension=[["1", "elephant"], ["99", "ghost"]],
        )

        with DwCAReader(path) as dwca:
            assert {"extension.txt": {"99": [1]}} == dwca.orphaned_extension_rows()

    def test_core_row_extensions_content_and_ordering(self):
        path = self._archive()

        with DwCAReader(path) as dwca:
            rows = list(dwca)

            assert ["elephant", "tiger"] == [
                r.data[VERNACULAR_TERM] for r in rows[0].extensions
            ]
            assert ["monkey"] == [r.data[VERNACULAR_TERM] for r in rows[1].extensions]

    def test_ignore_header_lines_are_skipped_in_the_extension_index(self):
        path = self._archive(
            ignore_header_lines=2, header_rows=[["idA", "locA"], ["idB", "locB"]]
        )

        with DwCAReader(path) as dwca:
            index = dwca.extension_files[0].coreid_index

            assert {"1": array("L", [0, 1]), "2": array("L", [2])} == index


class TestRandomAccessDirect(unittest.TestCase):
    """DwCAReader.next() is implemented as CSVDataFile.get_row_by_position() (see
    dwca/read.py), so today every iteration test incidentally exercises random access too.
    A rewrite that stops delegating would make that coverage disappear silently unless
    something calls get_row_by_position() directly, which is what these tests do.
    """

    def test_multibyte_utf8(self):
        # "\u4e2d\u6587" ("Chinese" in Chinese) is 2 characters but 6 bytes in UTF-8, so the
        # byte offset of row 1 (used internally for seek()) differs from what a
        # character-based offset would be.
        locality = "caf\u00e9 \u4e2d\u6587"
        path = build_archive(
            temp_archive_dir(self),
            rows=[["1", locality], ["2", "Mumbai"]],
        )

        with DwCAReader(path) as dwca:
            first = dwca.core_file.get_row_by_position(0)
            second = dwca.core_file.get_row_by_position(1)

        assert locality == first.data[TERM1]
        assert ["1", locality] == first.raw_fields
        assert "Mumbai" == second.data[TERM1]
        assert ["2", "Mumbai"] == second.raw_fields

    def test_dos_terminator(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[["1", "Borneo"], ["2", "Mumbai"]],
            lines_terminated_by="\r\n",
        )

        with DwCAReader(path) as dwca:
            first = dwca.core_file.get_row_by_position(0)
            second = dwca.core_file.get_row_by_position(1)

        assert "Borneo" == first.data[TERM1]
        assert ["1", "Borneo"] == first.raw_fields
        assert "Mumbai" == second.data[TERM1]
        assert ["2", "Mumbai"] == second.raw_fields

    def test_quoted_field_containing_the_separator(self):
        path = build_archive(
            temp_archive_dir(self),
            rows=[["1", "plain, with comma"], ["2", "second"]],
            fields_terminated_by=",",
            fields_enclosed_by='"',
        )

        with DwCAReader(path) as dwca:
            first = dwca.core_file.get_row_by_position(0)
            second = dwca.core_file.get_row_by_position(1)

        assert "plain, with comma" == first.data[TERM1]
        assert ["1", "plain, with comma"] == first.raw_fields
        assert "second" == second.data[TERM1]
        assert ["2", "second"] == second.raw_fields


class TestRowExtensionsDuringCoreIteration(unittest.TestCase):
    def _archive(self):
        return build_archive(
            temp_archive_dir(self),
            rows=[["1", "Borneo"], ["2", "Mumbai"]],
            extension=[["1", "elephant"], ["1", "tiger"], ["2", "monkey"]],
        )

    def test_row_extensions_accessible_during_core_iteration(self):
        path = self._archive()

        seen = {}
        with DwCAReader(path) as dwca:
            for row in dwca:
                seen[row.id] = [e.data[VERNACULAR_TERM] for e in row.extensions]

        assert {"1": ["elephant", "tiger"], "2": ["monkey"]} == seen

    def test_row_extensions_are_cached(self):
        path = self._archive()

        with DwCAReader(path) as dwca:
            row = next(iter(dwca))
            first = row.extensions
            second = row.extensions

        # Lazy-loaded and cached on the instance: same list object both times, not rebuilt.
        assert first is second
        assert ["elephant", "tiger"] == [e.data[VERNACULAR_TERM] for e in first]


class TestNegativePosition(unittest.TestCase):
    def test_negative_position_returns_the_header_line(self):
        # get_row_by_position() computes self._line_offsets[position + lines_to_ignore]. For
        # position=-1 this wraps around to the last entry in the offsets array, which is the
        # header line (kept in the index but skipped during normal iteration).
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            row = dwca.core_file.get_row_by_position(-1)

        # CHARACTERIZATION: wrong, see B7. A rewrite will likely raise IndexError instead.
        assert "id" == row.id


class TestDuplicateCoreIds(unittest.TestCase):
    """get_corerow_by_id()'s docstring disclaims which row wins when ids repeat, and
    coreid_index maps one id to several positions. Pin both so a rewrite has to decide
    deliberately rather than by accident.
    """

    def _archive(self):
        return build_archive(
            temp_archive_dir(self),
            rows=[["1", "Borneo"], ["1", "Mumbai"], ["2", "Paris"]],
        )

    def test_get_corerow_by_id_returns_the_first_match(self):
        with DwCAReader(self._archive()) as dwca:
            row = dwca.get_corerow_by_id("1")

        assert "Borneo" == row.data[TERM1]

    def test_coreid_index_holds_every_position(self):
        with DwCAReader(self._archive()) as dwca:
            index = dwca.core_file.coreid_index

        assert {"1": array("L", [0, 1]), "2": array("L", [2])} == index


class TestQuotedRecordsSpanningLines(unittest.TestCase):
    """A quoted field may contain the line terminator. Iteration and random access must agree."""

    QUOTED_META = {"fields_terminated_by": ",", "fields_enclosed_by": '"'}

    def _archive(self, payload, columns=3):
        return build_archive(
            temp_archive_dir(self),
            rows=[],
            columns=columns,
            raw_payload=payload,
            **self.QUOTED_META
        )

    def test_iteration_and_random_access_agree(self):
        path = self._archive(b'0,b,a\n1,a,"x\ny\nz"\n2,"x\ny\nz",a\n')

        with DwCAReader(path) as dwca:
            streamed = [row.raw_fields for row in dwca]
            seeked = [
                dwca.core_file.get_row_by_position(i).raw_fields
                for i in range(len(streamed))
            ]

        assert [["0", "b", "a"], ["1", "a", "x\ny\nz"], ["2", "x\ny\nz", "a"]] == streamed
        assert streamed == seeked

    def test_extensions_are_not_truncated(self):
        """coreid_index is built from the streaming pass but consumed through seeks."""
        directory = temp_archive_dir(self)
        path = build_archive(
            directory,
            rows=[["1", "Lagopus"], ["2", "Struthio"]],
            fields_terminated_by=",",
            fields_enclosed_by='"',
            extension=[["1", "grouse\nfoo"], ["2", "ostrich"]],
        )

        with DwCAReader(path) as dwca:
            per_core = [[e.raw_fields for e in row.extensions] for row in dwca]

        assert [["1", "grouse\nfoo"]] == per_core[0]
        assert [["2", "ostrich"]] == per_core[1]
