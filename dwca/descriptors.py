"""Classes to represents descriptors of a DwC-A.

- :class:`ArchiveDescriptor` represents the full archive descriptor, initialized from the \
metafile content.
- :class:`DataFileDescriptor` describes characteristics of a given data file in the archive. It's \
either created from a subsection of the ArchiveDescriptor describing the data file, either by \
introspecting the CSV data file (useful for Archives without metafile).

"""

import csv
import io
import os
import re
from operator import itemgetter
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Set
from xml.etree.ElementTree import Element

from dwca.exceptions import InvalidArchive


class DataFileDescriptor(object):
    """Those objects describe a data file fom the archive.

    They're generally not instanciated manually, but rather by calling:

        * :meth:`.make_from_metafile_section` (if the archive contains a metafile)
        * :meth:`make_from_file` (created by analyzing the data file)
    """

    def __init__(
        self,
        created_from_file: bool,
        raw_element: Element,
        represents_corefile: bool,
        datafile_type: Optional[str],
        file_location: str,
        file_encoding: str,
        id_index: int,
        coreid_index: int,
        fields: List[Dict],
        lines_terminated_by: str,
        fields_enclosed_by: str,
        fields_terminated_by: str,
    ) -> None:
        #: True if this descriptor was created by analyzing the data file.
        self.created_from_file = created_from_file
        #: The <section> element describing the data file, from the metafile. None if the
        #: archive contains no metafile.
        self.raw_element = raw_element
        #: True if this descriptor is used to represent the core file an archive.
        self.represents_corefile = represents_corefile
        #: True if this descriptor is used to represent an extension file in an archive.
        self.represents_extension = not represents_corefile
        #:
        self.type = datafile_type
        #: The data file location, relative to the archive root.
        self.file_location = file_location  # type: str
        #: The encoding of the data file. Example: "utf-8".
        self.file_encoding = file_encoding
        #: If the section represents a core data file, the index/position of the id column in
        #: that file.
        self.id_index = id_index
        #: If the section represents an extension data file, the index/position of the core_id
        #: column in that file. The `core_id` in an extension is the foreign key to the
        #: "extended" core row.
        self.coreid_index = coreid_index
        #: A list of dicts where each entry represent a data field in use.
        #:
        #: Each dict contains:
        #:      - The term identifier
        #:      - (Possibly) a default value
        #:      - The column index/position in the CSV file (except if we use a default value
        #:        instead)
        #:
        #: Example::
        #:
        #:      [{'term': 'http://rs.tdwg.org/dwc/terms/scientificName',
        #:        'index': '1',
        #:        'default': None},
        #:
        #:       {'term': 'http://rs.tdwg.org/dwc/terms/locality',
        #:        'index': '2',
        #:        'default': ''},
        #:
        #:       # The data for `country` is a the default value 'Belgium' for all rows, so there's
        #:       # no column in CSV file.
        #:
        #:       {'term': 'http://rs.tdwg.org/dwc/terms/country',
        #:        'index': None,
        #:        'default': 'Belgium'}]
        self.fields = fields

        #: The string or character used as a line separator in the data file. Example: "\\n".
        self.lines_terminated_by = lines_terminated_by
        #: The string or character used to enclose fields in the data file.
        self.fields_enclosed_by = fields_enclosed_by
        #: The string or character used as a field separator in the data file. Example: "\\t".
        self.fields_terminated_by = fields_terminated_by

    @classmethod
    def make_from_file(cls, datafile_path):
        """Create and return a DataFileDescriptor by analyzing the file at datafile_path.

        :param datafile_path: Relative path to a data file to analyze in order to instantiate the\
        descriptor.
        :type datafile_path: str
        """
        file_encoding = "utf-8"

        with io.open(datafile_path, "r", encoding=file_encoding) as datafile:
            # Autodetect fields/lines termination
            dialect = csv.Sniffer().sniff(datafile.readline())

            # Normally, EOL characters should be available in dialect.lineterminator, but it
            # seems it always returns \r\n. The workaround therefore consists to open the file
            # in universal-newline mode, which adds a newlines attribute.
            lines_terminated_by = datafile.newlines

            fields_terminated_by = dialect.delimiter
            fields_enclosed_by = dialect.quotechar

            datafile.seek(0)

            dr = csv.reader(datafile, dialect)
            columns = next(dr)

            fields = [
                {"index": i, "term": column, "default": None}
                for i, column in enumerate(columns)
            ]

        return cls(
            created_from_file=True,
            raw_element=None,  # No metafile, so no XML section to store
            represents_corefile=True,  # In archives w/o metafiles, there's only core data
            datafile_type=None,  # No metafile => no rowType information
            file_location=os.path.basename(
                datafile_path
            ),  # datafile_path also has the dir
            file_encoding=file_encoding,
            id_index=None,
            coreid_index=None,
            fields=fields,
            lines_terminated_by=lines_terminated_by,
            fields_enclosed_by=fields_enclosed_by,
            fields_terminated_by=fields_terminated_by,
        )

    @classmethod
    def make_from_metafile_section(cls, section_tag):
        """Create and return a DataFileDescriptor from a metafile <section> tag.

        :param section_tag: The XML Element section containing details about the data file.
        :type section_tag: :class:`xml.etree.ElementTree.Element`
        """
        if section_tag.tag == "core":
            id_index = int(section_tag.find("id").get("index"))
            coreid_index = None
        else:
            id_index = None
            coreid_index = int(section_tag.find("coreid").get("index"))

        fields = []
        for field_tag in section_tag.findall("field"):
            default = field_tag.get("default", None)

            # Default fields don't have an index attribute
            index = int(field_tag.get("index")) if field_tag.get("index") else None

            fields.append(
                {"term": field_tag.get("term"), "index": index, "default": default}
            )

        file_encoding = section_tag.get("encoding")

        lines_terminated_by = _decode_xml_attribute(
            raw_element=section_tag,
            attribute_name="linesTerminatedBy",
            default_value="\n",
            encoding=file_encoding,
        )

        fields_terminated_by = _decode_xml_attribute(
            raw_element=section_tag,
            attribute_name="fieldsTerminatedBy",
            default_value="\t",
            encoding=file_encoding,
        )

        fields_enclosed_by = _decode_xml_attribute(
            raw_element=section_tag,
            attribute_name="fieldsEnclosedBy",
            default_value="",
            encoding=file_encoding,
        )

        return cls(
            created_from_file=False,
            raw_element=section_tag,
            represents_corefile=(section_tag.tag == "core"),
            datafile_type=section_tag.get("rowType"),
            file_location=section_tag.find("files").find("location").text,
            file_encoding=file_encoding,
            id_index=id_index,
            coreid_index=coreid_index,
            fields=fields,
            lines_terminated_by=lines_terminated_by,
            fields_enclosed_by=fields_enclosed_by,
            fields_terminated_by=fields_terminated_by,
        )

    def __key(self):
        """Return a tuple describing the data file layout. Common ground between equality and hash.

        Deliberately excludes `raw_element`: it's an xml.etree.ElementTree.Element, which
        compares by identity, so including it would make two descriptors built from the same
        metafile section never compare equal. `lines_to_ignore` stands in for the only part of
        `raw_element` that affects parsing (the ignoreHeaderLines attribute).

        `created_from_file` is excluded too: it records where the descriptor came from, not how
        the file is laid out, and its only behavioral effect is already covered by
        `lines_to_ignore`. `represents_extension` is excluded as it's just the negation of
        `represents_corefile`.
        """
        return (
            self.file_location,
            self.file_encoding,
            self.type,
            self.id_index,
            self.coreid_index,
            self.represents_corefile,
            self.fields,
            self.lines_terminated_by,
            self.fields_enclosed_by,
            self.fields_terminated_by,
            self.lines_to_ignore,
        )

    def __eq__(self, other):
        if not isinstance(other, DataFileDescriptor):
            return NotImplemented

        return self.__key() == other.__key()

    def __hash__(self):
        # __key() embeds `fields`, a list of dicts, which isn't hashable. Equal descriptors
        # still hash equally because this is a subset of the equality key.
        return hash(
            (
                self.file_location,
                self.file_encoding,
                self.type,
                self.id_index,
                self.coreid_index,
                self.represents_corefile,
                self.lines_terminated_by,
                self.fields_enclosed_by,
                self.fields_terminated_by,
                self.lines_to_ignore,
            )
        )

    @property
    def field_plan(self) -> "FieldPlan":
        """A cached :class:`FieldPlan` turning a split data row into a term -> value dict."""
        plan = self.__dict__.get("_field_plan")
        if plan is None:
            plan = FieldPlan(self.fields)
            self.__dict__["_field_plan"] = plan
        return plan

    @property
    def terms(self) -> Set[str]:
        """Return a Python set containing all the Darwin Core terms appearing in file."""
        return set([f["term"] for f in self.fields])

    @property
    def headers(self) -> List[str]:
        """A list of (ordered) column names that can be used to create a header line for the data file.

        Example::

            ['id', 'http://rs.tdwg.org/dwc/terms/scientificName', 'http://rs.tdwg.org/dwc/terms/basisOfRecord',
            'http://rs.tdwg.org/dwc/terms/family', 'http://rs.tdwg.org/dwc/terms/locality']

        See also :py:attr:`short_headers` if you prefer less verbose headers.
        """
        columns = {}

        for f in self.fields:
            # Some fields (those carrying only a default value) have no column. Note the
            # explicit None test: index 0 is a valid column and must not be dropped.
            if f["index"] is not None:
                columns[f["index"]] = f["term"]

        # In addition to DwC terms, we may also have id (Core) or core_id (Extensions) columns
        if self.id_index is not None:
            columns[self.id_index] = "id"
        if self.coreid_index is not None:
            columns[self.coreid_index] = "coreid"

        return [columns[f] for f in sorted(columns.keys())]

    @property
    def short_headers(self) -> List[str]:
        """A list of (ordered) column names (short version) that can be used to create a header line for the data file.

           Example::

                ['id', 'scientificName', 'basisOfRecord', 'family', 'locality']

        See also :py:attr:`headers`.
        """
        return [shorten_term(long_term) for long_term in self.headers]

    @property
    def lines_to_ignore(self) -> int:
        """Return the number of header lines/lines to ignore in the data file."""
        if self.created_from_file:
            # Single-file archives always have a header line with DwC terms
            return 1

        return int(self.raw_element.get("ignoreHeaderLines", 0))


class FieldPlan(object):
    """Precomputed mapping from a split CSV line to a term -> value dict.

    Built once per :class:`DataFileDescriptor` (see its ``field_plan`` property) so that
    parsing a row costs one C-level ``dict(zip(...))`` instead of a Python loop over the
    field descriptors.
    """

    __slots__ = (
        "_fields",
        "_contiguous_terms",
        "_terms",
        "_getter",
        "_single_column",
        "_defaults",
        "_constants",
        "_ordered",
        "required_columns",
    )

    def __init__(self, fields):
        self._fields = fields

        indexed = [f for f in fields if f["index"] is not None]
        indexes = [f["index"] for f in indexed]

        #: Number of columns a data row must have for this plan to apply.
        self.required_columns = max(indexes) + 1 if indexes else 0

        # Terms without a column: the value is always the default.
        self._constants = tuple(
            (f["term"], f["default"] or "") for f in fields if f["index"] is None
        )
        # Indexed terms that also carry a default, used when the cell is empty (issue #80).
        self._defaults = tuple(
            (f["term"], f["default"]) for f in indexed if f["default"]
        )

        # When some terms have no column, the fast paths below would append them after the
        # mapped ones and change the key order of Row.data (which is user-visible through
        # str(row)). Those archives use an ordered path instead; they are rare, and the
        # ordered path is still free of the per-field try/except and int() it replaces.
        self._ordered = (
            tuple((f["term"], f["index"], f["default"]) for f in fields)
            if self._constants
            else None
        )

        if indexes and sorted(indexes) == list(range(len(indexes))):
            # Fast path: the indexed fields cover columns 0..n-1 exactly once.
            ordered = sorted(indexed, key=lambda f: f["index"])
            self._contiguous_terms = tuple(f["term"] for f in ordered)
            self._terms = None
            self._getter = None
            self._single_column = False
        else:
            self._contiguous_terms = None
            self._terms = tuple(f["term"] for f in indexed)
            self._getter = itemgetter(*indexes) if indexes else None
            # itemgetter with a single argument returns a scalar, not a tuple.
            self._single_column = len(indexes) == 1

    def build_data(self, raw_fields):
        """Return the term -> value dict for an already-split data row."""
        if len(raw_fields) < self.required_columns:
            self._raise_missing_column(raw_fields)

        if self._ordered is not None:
            data = {}
            for term, index, default in self._ordered:
                value = raw_fields[index] if index is not None else None
                data[term] = value or default or ""
            return data

        if self._contiguous_terms is not None:
            data = dict(zip(self._contiguous_terms, raw_fields))
        elif self._getter is not None:
            values = self._getter(raw_fields)
            if self._single_column:
                values = (values,)
            data = dict(zip(self._terms, values))
        else:
            data = {}

        for term, default in self._defaults:
            if not data[term]:
                data[term] = default
        for term, constant in self._constants:
            data[term] = constant

        return data

    def term_getter(self, terms):
        """Return a callable mapping a split data row to a tuple of values for `terms`.

        :raises ValueError: if any requested term is absent from the data file.
        """
        by_term = {f["term"]: f for f in self._fields}

        missing = [term for term in terms if term not in by_term]
        if missing:
            raise ValueError(
                "These terms are not in this data file: {t}".format(
                    t=", ".join(sorted(missing))
                )
            )

        indexes = tuple(by_term[term]["index"] for term in terms)
        defaults = tuple(by_term[term]["default"] for term in terms)

        if indexes and all(i is not None for i in indexes) and not any(defaults):
            # Fast path: every term maps to a column and none has a default, so the whole
            # tuple comes out of a single C-level call.
            getter = itemgetter(*indexes)
            required = max(indexes) + 1

            if len(indexes) == 1:
                # itemgetter with a single argument returns a scalar, not a tuple.
                def get_one(raw_fields):
                    if len(raw_fields) < required:
                        self._raise_missing_column(raw_fields)
                    return (getter(raw_fields),)

                return get_one

            def get_many(raw_fields):
                if len(raw_fields) < required:
                    self._raise_missing_column(raw_fields)
                return getter(raw_fields)

            return get_many

        required = max([i for i in indexes if i is not None] or [-1]) + 1

        def get_general(raw_fields):
            if len(raw_fields) < required:
                self._raise_missing_column(raw_fields)
            return tuple(
                (raw_fields[index] if index is not None else None) or default or ""
                for index, default in zip(indexes, defaults)
            )

        return get_general

    def _raise_missing_column(self, raw_fields):
        # Slow path: report the same index the old per-field loop would have reported.
        for field in self._fields:
            index = field["index"]
            if index is not None and index >= len(raw_fields):
                raise InvalidArchive(
                    "The descriptor references a non-existent field (index={i})".format(
                        i=index
                    )
                )
        raise InvalidArchive("The descriptor references a non-existent field")


class ArchiveDescriptor(object):
    """Class used to encapsulate the whole Metafile (`meta.xml`)."""

    def __init__(self, metaxml_content: str, files_to_ignore: List[str] = None) -> None:
        if files_to_ignore is None:
            files_to_ignore = []

        # Let's drop the XML namespace to avoid prefixes
        metaxml_content = re.sub(' xmlns="[^"]+"', "", metaxml_content, count=1)

        #: A :class:`xml.etree.ElementTree.Element` instance containing the complete Archive Descriptor.
        self.raw_element = ET.fromstring(metaxml_content)  # type: Element

        #: The path (relative to archive root) of the (scientific) metadata of the archive.
        self.metadata_filename = self.raw_element.get("metadata", None)

        #: An instance of :class:`dwca.descriptors.DataFileDescriptor` describing the core data file.
        raw_core_element = self.raw_element.find("core")
        self.core = DataFileDescriptor.make_from_metafile_section(
            raw_core_element
        )  # type: DataFileDescriptor

        #: A list of :class:`dwca.descriptors.DataFileDescriptor` instances describing each of the archive's extension
        #: data files.
        self.extensions = []  # type: List[DataFileDescriptor]
        for extension_tag in self.raw_element.findall("extension"):  # type: Element
            location_tag = extension_tag.find("./files/location")
            if location_tag is not None:
                extension_filename = location_tag.text
                if extension_filename not in files_to_ignore:
                    self.extensions.append(
                        DataFileDescriptor.make_from_metafile_section(extension_tag)
                    )
            else:
                raise InvalidArchive(
                    "An extension file is referenced in Metafile, but its path is not specified."
                )

        #: A list of extension (types) in use in the archive.
        #:
        #: Example::
        #:
        #:     ["http://rs.gbif.org/terms/1.0/VernacularName",
        #:      "http://rs.gbif.org/terms/1.0/Description"]
        self.extensions_type = [e.type for e in self.extensions]


def shorten_term(long_term):
    return long_term.split("/")[-1]


def _decode_xml_attribute(raw_element, attribute_name, default_value, encoding):
    # Gets XML attribute and decode it to make it usable. If it doesn't exists, it returns
    # default_value.

    raw_attribute = raw_element.get(attribute_name)
    if raw_attribute:
        return bytes(raw_attribute, encoding).decode("unicode-escape")

    return default_value
