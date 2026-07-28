"""Build synthetic Darwin Core Archives for tests.

Produces a directory-based archive (DwCAReader reads directories directly, so nothing
needs zipping). Every parameter that the Metafile can express is explicit, which is what
lets the characterization tests cover encodings, terminators, quoting and header counts
without committing more binary sample files.
"""

import os
import shutil
import tempfile
from xml.sax.saxutils import quoteattr

TERM_PREFIX = "http://rs.tdwg.org/dwc/terms/"


def temp_archive_dir(test_case):
    """Return a temporary directory that is removed when `test_case` finishes.

    Several tests in the suite count the entries in the system temporary directory, so
    leaking one per test would eventually make them flaky.
    """
    directory = tempfile.mkdtemp()
    test_case.addCleanup(shutil.rmtree, directory, ignore_errors=True)
    return directory

METAFILE_TEMPLATE = """<archive xmlns="http://rs.tdwg.org/dwc/text/">
  <core encoding={encoding} fieldsTerminatedBy={fields_terminated_by} \
linesTerminatedBy={lines_terminated_by} fieldsEnclosedBy={fields_enclosed_by} \
ignoreHeaderLines={ignore_header_lines} rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
    <files><location>occurrence.txt</location></files>
    <id index="{id_index}" />
{fields}
  </core>
{extension}
</archive>
"""

EXTENSION_TEMPLATE = """  <extension encoding={encoding} fieldsTerminatedBy={fields_terminated_by} \
linesTerminatedBy={lines_terminated_by} fieldsEnclosedBy={fields_enclosed_by} \
ignoreHeaderLines={ignore_header_lines} rowType="http://rs.gbif.org/terms/1.0/VernacularName">
    <files><location>extension.txt</location></files>
    <coreid index="0" />
{fields}
  </extension>"""


def _escape(raw):
    # The Metafile stores separators escaped, e.g. the tab character as the two
    # characters backslash-t. Mirror what real archives contain.
    escaped = (
        raw.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    return quoteattr(escaped)


def _field_tags(terms, defaults, indent="    "):
    lines = []
    for index, term in enumerate(terms):
        default = (defaults or {}).get(term)
        if default is None:
            lines.append(
                '{i}<field index="{n}" term="{t}"/>'.format(i=indent, n=index, t=term)
            )
        else:
            lines.append(
                '{i}<field index="{n}" term="{t}" default={d}/>'.format(
                    i=indent, n=index, t=term, d=quoteattr(default)
                )
            )
    for term, default in (defaults or {}).items():
        if term not in terms:
            lines.append(
                '{i}<field term="{t}" default={d}/>'.format(
                    i=indent, t=term, d=quoteattr(default)
                )
            )
    return "\n".join(lines)


def _render_rows(rows, fields_terminated_by, lines_terminated_by, fields_enclosed_by):
    out = []
    for row in rows:
        if fields_enclosed_by:
            cells = [
                fields_enclosed_by
                + cell.replace(fields_enclosed_by, fields_enclosed_by * 2)
                + fields_enclosed_by
                for cell in row
            ]
        else:
            cells = list(row)
        out.append(fields_terminated_by.join(cells))
    return lines_terminated_by.join(out) + (lines_terminated_by if out else "")


def build_archive(
    directory,
    rows,
    columns=None,
    encoding="utf-8",
    lines_terminated_by="\n",
    fields_terminated_by="\t",
    fields_enclosed_by="",
    ignore_header_lines=0,
    header_rows=(),
    id_index=0,
    terms=None,
    defaults=None,
    extension=None,
    trailing_newline=True,
    raw_payload=None,
):
    """Write a Darwin Core Archive into `directory` and return its path.

    :param rows: list of lists of str, the data rows.
    :param terms: list of full term URIs, one per column. Defaults to term0, term1, ...
    :param defaults: dict term -> default value. A term not present in `terms` becomes a
        default-only field (no index attribute), as the standard allows.
    :param extension: list of rows for an extension data file, or None. Column 0 is the coreid.
    :param raw_payload: bytes written verbatim as the core data file instead of `rows`.
        Used to build inputs no well-formed writer would produce (undecodable bytes, ragged
        rows, blank lines).
    """
    if columns is None:
        columns = max([len(r) for r in rows] + [1]) if rows else 1
    if terms is None:
        terms = [TERM_PREFIX + "term" + str(i) for i in range(columns)]

    metafile = METAFILE_TEMPLATE.format(
        encoding=quoteattr(encoding),
        fields_terminated_by=_escape(fields_terminated_by),
        lines_terminated_by=_escape(lines_terminated_by),
        fields_enclosed_by=_escape(fields_enclosed_by),
        ignore_header_lines=quoteattr(str(ignore_header_lines)),
        id_index=id_index,
        fields=_field_tags(terms, defaults),
        extension=(
            ""
            if extension is None
            else EXTENSION_TEMPLATE.format(
                encoding=quoteattr(encoding),
                fields_terminated_by=_escape(fields_terminated_by),
                lines_terminated_by=_escape(lines_terminated_by),
                fields_enclosed_by=_escape(fields_enclosed_by),
                ignore_header_lines=quoteattr(str(ignore_header_lines)),
                fields=_field_tags(
                    [TERM_PREFIX + "vernacularName"], None, indent="    "
                ).replace('index="0"', 'index="1"'),
            )
        ),
    )

    with open(os.path.join(directory, "meta.xml"), "w", encoding="utf-8") as f:
        f.write(metafile)

    data_path = os.path.join(directory, "occurrence.txt")
    if raw_payload is not None:
        with open(data_path, "wb") as f:
            f.write(raw_payload)
    else:
        payload = _render_rows(
            list(header_rows) + list(rows),
            fields_terminated_by,
            lines_terminated_by,
            fields_enclosed_by,
        )
        if not trailing_newline and payload.endswith(lines_terminated_by):
            payload = payload[: -len(lines_terminated_by)]
        with open(data_path, "w", encoding=encoding, newline="") as f:
            f.write(payload)

    if extension is not None:
        payload = _render_rows(
            list(header_rows) + list(extension),
            fields_terminated_by,
            lines_terminated_by,
            fields_enclosed_by,
        )
        with open(
            os.path.join(directory, "extension.txt"), "w", encoding=encoding, newline=""
        ) as f:
            f.write(payload)

    return directory
