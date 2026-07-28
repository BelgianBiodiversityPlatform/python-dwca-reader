"""File-related classes and functions."""

import csv
import io
import os
from array import array
from itertools import islice
from typing import Iterator, List, Tuple, Union, IO, Dict, Optional

from dwca.descriptors import DataFileDescriptor
from dwca.rows import CoreRow, ExtensionRow, Row


class CSVDataFile(object):
    """Object used to access a DwCA-enclosed CSV data file.

    :param work_directory: absolute path to the target directory (archive content, previously\
    extracted if necessary).
    :param file_descriptor: an instance of :class:`dwca.descriptors.DataFileDescriptor`\
    describing the data file.

    The file content can be accessed:

    * By iterating on this object: a str is returned, including separators.
    * With :meth:`get_row_by_position` (A :class:`dwca.rows.CoreRow` or :class:`dwca.rows.ExtensionRow` object is \
    returned)
    * For an extension data file, with :meth:`get_all_rows_by_coreid` (A :class:`dwca.rows.CoreRow` or \
    :class:`dwca.rows.ExtensionRow` object is returned)

    An index of line offsets is built on first random access (:meth:`get_row_by_position` or\
    :meth:`get_all_rows_by_coreid`). This may take time for large files, but makes further random\
    access faster.
    """

    def __init__(
        self, work_directory: str, file_descriptor: DataFileDescriptor
    ) -> None:
        """Initialize the CSVDataFile object."""
        #: An instance of :class:`dwca.descriptors.DataFileDescriptor`, as given to the
        #: constructor.
        self.file_descriptor = file_descriptor  # type: DataFileDescriptor

        self._file_path = os.path.join(
            work_directory, self.file_descriptor.file_location
        )
        self._file_stream = self._open_stream(
            newline=self.file_descriptor.lines_terminated_by
        )

        # Opened lazily, on first random-access read: a dedicated binary stream used to
        # fetch the exact byte range of a record (see _read_record).
        self._binary_stream = None  # type: Optional[IO]

        # The index of line offsets is only needed for random access, so it is built on
        # first use rather than here: opening an archive stays O(1) whatever its size.
        self._line_offsets = None  # type: Optional[array]

        #: Number of lines to ignore (header lines) in the CSV file.
        self.lines_to_ignore = self.file_descriptor.lines_to_ignore  # type: int

        self._coreid_index = None  # type: Optional[Dict[str, List[int]]]

    def iter_terms(self, terms: List[str]) -> Iterator[Tuple[str, ...]]:
        """Yield one tuple of values per data row, holding `terms` in the order given.

        This is a faster alternative to iterating over rows for consumers that only need a
        few of the file's columns: neither a :class:`dwca.rows.Row` object nor its term to
        value dict is built. A single term still yields a one-element tuple.

        Usage::

            for locality, latitude in data_file.iter_terms([qn('locality'),
                                                            qn('decimalLatitude')]):
                pass

        The special names "id" and "coreid" request the file's key column - the same names
        used by :attr:`dwca.descriptors.DataFileDescriptor.headers`. "id" resolves for a core
        file, "coreid" for an extension file; the other one raises, as does either name when
        the file has no such column (metafile-less archives have neither). If the file
        declares an actual term of the same name, that declared term takes precedence, which
        matches what `Row.data['id']` already returns.

        :param terms: a list of full term identifiers.
        :raises ValueError: if any of `terms` is not present in this data file.
        """
        # The getter is resolved eagerly so an unknown term is reported by this call rather
        # than on first iteration.
        getter = self.file_descriptor.field_plan.term_getter(terms)

        return self._iter_terms(getter)

    def _iter_terms(self, getter) -> Iterator[tuple]:
        for fields in self._iter_field_lists():
            yield getter(fields)

    def __str__(self) -> str:
        return self.file_descriptor.file_location

    def _open_stream(self, newline: str) -> IO:
        return io.open(
            self._file_path,
            mode="r",
            encoding=self.file_descriptor.file_encoding,
            newline=newline,
            errors="replace",
        )

    def _get_line_offsets(self) -> array:
        if self._line_offsets is None:
            descriptor = self.file_descriptor
            self._line_offsets = _build_line_offsets(
                self._file_path,
                descriptor.file_encoding,
                descriptor.lines_terminated_by,
                descriptor.fields_enclosed_by,
                descriptor.fields_terminated_by,
            )
        return self._line_offsets

    def _iter_field_lists(self) -> Iterator[List[str]]:
        """Yield each data row of the file as a list of raw field values.

        Header lines are skipped. This is a single forward pass over a dedicated stream, so
        it is safe to run several of these concurrently and alongside random access.
        """
        if self._file_stream.closed:
            raise ValueError("The data file has been closed.")

        descriptor = self.file_descriptor
        quoted = descriptor.fields_enclosed_by != ""

        # The csv module refuses a stream that can hand it an embedded carriage return, so
        # the quoted path has to let Python handle newlines. The unquoted path keeps the
        # archive's own terminator, which is what stops U+0085 from being treated as a line
        # break (issue #20).
        stream = self._open_stream(
            newline="" if quoted else descriptor.lines_terminated_by
        )
        try:
            if quoted:
                source = csv.reader(
                    stream,
                    delimiter=descriptor.fields_terminated_by,
                    quotechar=descriptor.fields_enclosed_by,
                    quoting=csv.QUOTE_MINIMAL,
                )  # type: Iterator[List[str]]
            else:
                # A carriage return is stripped alongside the declared terminator: archives
                # routinely declare "\n" while the file itself has CRLF line endings, and the
                # csv module this replaced dropped the stray CR for us. Without this, the last
                # field of every row would keep it.
                line_ending = descriptor.lines_terminated_by + "\r"
                separator = descriptor.fields_terminated_by
                source = (line.rstrip(line_ending).split(separator) for line in stream)

            for fields in islice(source, self.lines_to_ignore, None):
                yield fields
        finally:
            stream.close()

    def iter_rows(self) -> Iterator[Union[CoreRow, ExtensionRow]]:
        """Yield every data row of the file, in order of appearance.

        Unlike repeated :meth:`get_row_by_position` calls this is a single forward pass and
        never touches the line offset index.
        """
        descriptor = self.file_descriptor
        row_class = CoreRow if descriptor.represents_corefile else ExtensionRow

        for position, fields in enumerate(self._iter_field_lists()):
            yield row_class.from_fields(fields, position, descriptor)

    def _position_file_after_header(self) -> None:
        self._file_stream.seek(0, 0)
        # NOTE: readlines() takes a byte-size hint, not a line count, so it cannot be used
        # here. With ignoreHeaderLines="2" it would read a single line.
        for _ in range(self.lines_to_ignore):
            self._file_stream.readline()

    def __iter__(self) -> "CSVDataFile":
        self._position_file_after_header()
        return self

    def __next__(self) -> str:
        return self.next()

    def next(self) -> str:  # NOQA
        """Return the next raw line of the data file, including its line terminator.

        Header lines are skipped. Raises `StopIteration` once the file is exhausted. This is
        the iterator protocol behind `for line in data_file`, described in the class
        docstring.
        """
        for line in self._file_stream:
            return line

        raise StopIteration

    @property
    def coreid_index(self) -> Dict[str, array]:
        """An index of the core rows referenced by this data file.

        It is a Python dict such as:
        ::

            {
            core_id1: [1],    # Row at position 1 references a Core Row whose ID is core_id1
            core_id2: [8, 10] # Rows at position 8 and 10 references a Core Row whose ID is core_id2
            }

        .. warning::

            for performance reasons, dictionary values are arrays('L') instead of regular python lists

        .. warning::

            Creating this index can be time and memory consuming for large archives, so it's created on the fly
            at first access.
        """
        if self._coreid_index is None:
            self._coreid_index = self._build_coreid_index()

        return self._coreid_index

    def _build_coreid_index(self) -> Dict[str, List[int]]:
        """Build and return an index of Core Rows IDs suitable for `CSVDataFile.coreid_index`."""
        index = {}  # type: Dict[str, array[int]]

        represents_corefile = self.file_descriptor.represents_corefile
        for row in self.iter_rows():
            key = row.id if represents_corefile else row.core_id
            index.setdefault(key, array("L")).append(row.position)

        return index

    def get_all_rows_by_coreid(self, core_id: int) -> List[Row]:
        """Return the rows whose linking id matches `core_id`.

        For an extension file, this is the row's `coreid` field. For a core file, it is the
        row's own `id`, since `coreid_index` then maps each row's id to its position. The
        return type is `List[Row]` to cover both :class:`dwca.rows.CoreRow` (core file) and
        :class:`dwca.rows.ExtensionRow` (extension file). Returns an empty list if `core_id`
        is not found.
        """
        if core_id not in self.coreid_index:
            return []

        return [self.get_row_by_position(p) for p in self.coreid_index[core_id]]  # type: ignore # FIXME

    def get_row_by_position(self, position: int) -> Union[CoreRow, ExtensionRow]:
        """Return the row at `position` in the file.

        Header lines are ignored.

        :raises: IndexError if there's no line at `position`.
        """

        line = self._get_line_by_position(position)
        if self.file_descriptor.represents_corefile:
            return CoreRow(line, position, self.file_descriptor)
        else:
            return ExtensionRow(line, position, self.file_descriptor)

    # Raises IndexError if position is incorrect
    def _get_line_by_position(self, position: int) -> str:
        if self._file_stream.closed:
            raise ValueError("The data file has been closed.")

        offsets = self._get_line_offsets()
        index = position + self.lines_to_ignore
        return self._read_record(offsets, index)

    def _get_binary_stream(self) -> IO:
        # A dedicated handle, separate from self._file_stream: random access reads the
        # exact byte range of a record (see _read_record), and must not disturb the
        # position of the text stream used for sequential iteration.
        if self._binary_stream is None:
            self._binary_stream = io.open(self._file_path, mode="rb")
        return self._binary_stream

    def _read_record(self, offsets: array, index: int) -> str:
        """Return the full text of the record starting at offsets[index].

        offsets holds byte offsets, computed by scanning the file as bytes (see
        _build_line_offsets). A text stream's read(n) counts characters, not bytes, so
        turning a byte delta into a character count would silently truncate or over-read
        wherever a character takes more than one byte in the file's encoding (e.g.
        multi-byte UTF-8). Reading the exact byte range through a dedicated binary stream
        and decoding it afterwards keeps this correct regardless of encoding, and also
        regardless of how many physical lines the record spans (a quoted field may
        legally contain the line terminator).

        `index` supports the same negative-indexing quirk as a plain list/array
        (get_row_by_position(-1) is pinned by TestNegativePosition), so `offsets[index]`
        is used rather than any manual wraparound arithmetic.
        """
        start = offsets[index]
        stream = self._get_binary_stream()
        stream.seek(start, 0)

        following = index + 1
        if following < len(offsets) and offsets[following] > start:
            raw = stream.read(offsets[following] - start)
        else:
            raw = stream.read()

        return raw.decode(self.file_descriptor.file_encoding, errors="replace")

    def close(self) -> None:
        """Close the file.

        The content of the file will not be accessible in any way afterwards.
        """
        self._file_stream.close()
        if self._binary_stream is not None:
            self._binary_stream.close()


def _build_line_offsets(
    path: str,
    encoding: str,
    lines_terminated_by: str,
    fields_enclosed_by: str = "",
    fields_terminated_by: str = "\t",
    chunk_size: int = 1024 * 1024,
) -> array:
    """Return an array of the byte offset of every CSV record in the file at `path`.

    The values are suitable for seek() on a stream opened with the same encoding.

    Without an enclosure character every terminator ends a record, so this is a plain scan.
    With one, a terminator inside an enclosed field is data rather than a record boundary
    (a quoted field may legally contain the line terminator), so the scan tracks whether it
    is inside an enclosure.

    The file is scanned as bytes rather than as decoded text: decoding with
    errors="replace" turns an undecodable byte into U+FFFD, which does not re-encode to the
    same length, so computing offsets from decoded text desynchronises the index from the
    file.

    An array of Longs is used instead of a list. It is much more memory efficient, and a few
    tests with 1-4Gb uncompressed archives didn't show any significant slowdown.
    """
    terminator = lines_terminated_by.encode(encoding)
    tlen = len(terminator)

    if not fields_enclosed_by:
        return _scan_plain(path, terminator, tlen, chunk_size)

    quote = fields_enclosed_by.encode(encoding)

    # Fast screen: if no physical line ends with an unbalanced number of quote characters,
    # then no record spans a line break and the plain scan is already correct. This is the
    # overwhelmingly common case - including files where EVERY field is quoted - and it costs
    # one C-level count() per line instead of a Python step per quote character.
    offsets = _scan_screened(path, terminator, tlen, quote, chunk_size)
    if offsets is not None:
        return offsets

    return _scan_enclosed(
        path,
        terminator,
        tlen,
        quote,
        fields_terminated_by.encode(encoding),
        chunk_size,
    )


def _scan_plain(path, terminator, tlen, chunk_size):
    offsets = array("L", [0])
    buffer = b""
    base = 0
    with io.open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            buffer += chunk
            consumed = 0
            while True:
                found = buffer.find(terminator, consumed)
                if found == -1:
                    break
                consumed = found + tlen
                offsets.append(base + consumed)
            base += consumed
            buffer = buffer[consumed:]
    _trim(offsets, path)
    return offsets


def _scan_screened(path, terminator, tlen, quote, chunk_size):
    """Return record offsets if every physical line has balanced quotes, else None."""
    offsets = array("L", [0])
    buffer = b""
    base = 0
    line_start = 0  # index within buffer of the current line's first byte
    with io.open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            buffer += chunk
            consumed = 0
            while True:
                found = buffer.find(terminator, consumed)
                if found == -1:
                    break
                if buffer.count(quote, line_start, found) % 2:
                    return None  # a quoted field spans this line break; needs the exact scan
                consumed = found + tlen
                line_start = consumed
                offsets.append(base + consumed)
            base += consumed
            buffer = buffer[consumed:]
            line_start = 0
    _trim(offsets, path)
    return offsets


def _scan_enclosed(path, terminator, tlen, quote, delimiter, chunk_size):
    qlen = len(quote)
    dlen = len(delimiter)
    # A quote opens a field only at the very start of a record or immediately after a
    # delimiter; anywhere else it is literal content, which is what csv.reader does under
    # QUOTE_MINIMAL. Deciding that needs to look back at the bytes before the quote, and
    # deciding whether a quote is escaped needs to look ahead, so the buffer keeps a margin
    # of context on both sides of the cursor rather than being trimmed flush to it.
    margin = max(dlen, tlen, 2 * qlen)

    offsets = array("L", [0])
    buffer = b""
    base = 0           # absolute offset of buffer[0]
    pos = 0            # cursor within buffer
    in_quotes = False
    record_start = 0   # absolute offset of the current record

    with io.open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            eof = not chunk
            if not eof:
                buffer += chunk

            # Without more bytes coming, patterns can be resolved right up to the end.
            limit = len(buffer) if eof else len(buffer) - margin

            while pos < len(buffer):
                if in_quotes:
                    found = buffer.find(quote, pos)
                    if found == -1 or (not eof and found > limit):
                        pos = max(pos, limit)
                        break
                    if not eof and found + 2 * qlen > len(buffer):
                        break  # cannot yet tell an escaped quote from a closing one
                    if buffer.startswith(quote, found + qlen):
                        pos = found + 2 * qlen
                        continue
                    in_quotes = False
                    pos = found + qlen
                    continue

                nq = buffer.find(quote, pos)
                nt = buffer.find(terminator, pos)
                if nt == -1 and nq == -1:
                    pos = max(pos, limit)
                    break
                if not eof and min(x for x in (nq, nt) if x != -1) > limit:
                    pos = max(pos, limit)
                    break
                if nt != -1 and (nq == -1 or nt < nq):
                    pos = nt + tlen
                    offsets.append(base + pos)
                    record_start = base + pos
                    continue
                if base + nq == record_start:
                    opens = True
                else:
                    opens = (
                        (nq >= dlen and buffer.startswith(delimiter, nq - dlen))
                        or (nq >= tlen and buffer.startswith(terminator, nq - tlen))
                    )
                if opens:
                    in_quotes = True
                pos = nq + qlen

            if eof:
                break

            # Keep `margin` bytes behind the cursor so the look-back above still works after
            # the buffer is trimmed.
            drop = max(0, pos - margin)
            buffer = buffer[drop:]
            base += drop
            pos -= drop

    _trim(offsets, path)
    return offsets


def _trim(offsets: array, path: str) -> None:
    # A file ending with the terminator has no extra empty line after it, so the offset
    # pointing at EOF is spurious. This also empties the index for a zero-byte file, which
    # must report no lines at all rather than one empty one.
    if offsets and offsets[-1] == os.path.getsize(path):
        offsets.pop()
