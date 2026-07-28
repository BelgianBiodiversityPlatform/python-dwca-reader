"""Objects that represents data rows coming from DarwinCore Archives."""

import csv
from typing import Dict, List, Optional

from dwca.descriptors import DataFileDescriptor


class Row(object):
    """This class is used to represent a row/line in a Darwin Core Archive.

    This class is intended to be subclassed rather than used directly.
    """

    __slots__ = ("descriptor", "position", "rowtype", "raw_fields", "data")

    # Common ground for __str__ between subclasses
    def _build_str(self, source_str, id_str):
        txt = (
            "--\n"
            "Rowtype: {rowtype}\n"
            "Position: {position}\n"
            "Source: {source_str}\n"
            "{id_row}\n"
            "Reference extension rows: {extension_flag}\n"
            "Reference source metadata: {source_metadata_flag}\n"
            "Data: {data}\n"
            "--\n"
        )

        extension_flag = (
            "Yes"
            if (hasattr(self, "extensions") and (len(self.extensions) > 0))
            else "No"
        )

        if hasattr(self, "source_metadata") and (self.source_metadata is not None):
            source_metadata_flag = "Yes"
        else:
            source_metadata_flag = "No"

        return txt.format(
            rowtype=self.rowtype,
            position=self.position,
            source_str=source_str,
            data=self.data,
            id_row=id_str,
            extension_flag=extension_flag,
            source_metadata_flag=source_metadata_flag,
        )

    def __init__(
        self, csv_line: str, position: int, datafile_descriptor: DataFileDescriptor
    ) -> None:
        self._populate(
            csv_line_to_fields(
                csv_line,
                line_ending=datafile_descriptor.lines_terminated_by,
                field_ending=datafile_descriptor.fields_terminated_by,
                fields_enclosed_by=datafile_descriptor.fields_enclosed_by,
            ),
            position,
            datafile_descriptor,
        )

    @classmethod
    def from_fields(
        cls,
        raw_fields: List[str],
        position: int,
        datafile_descriptor: DataFileDescriptor,
    ) -> "Row":
        """Build a Row from an already-split data row.

        This is the constructor used by the streaming engine. :meth:`__init__`, which takes a
        raw CSV line, is kept for backwards compatibility.
        """
        row = cls.__new__(cls)
        row._populate(raw_fields, position, datafile_descriptor)
        return row

    def _populate(self, raw_fields, position, datafile_descriptor) -> None:
        #: An instance of :class:`dwca.descriptors.DataFileDescriptor` describing the
        #: originating data file.
        self.descriptor = datafile_descriptor  # type: DataFileDescriptor

        #: The row position/index (starting at 0) in the source data file. This can be used,
        #: for example with :meth:`dwca.read.DwCAReader.get_corerow_by_position` or
        #: :meth:`dwca.files.CSVDataFile.get_row_by_position`.
        self.position = position  # type: int

        #: The csv line type as stated in the archive descriptor (or None if the archive has
        #: no descriptor). Examples: http://rs.tdwg.org/dwc/terms/Occurrence,
        #: http://rs.gbif.org/terms/1.0/VernacularName, ...
        self.rowtype = self.descriptor.type  # type: Optional[str]

        #: A list of the row's raw (unmapped) field values.
        self.raw_fields = raw_fields

        #: A dict containing the Row data, such as::
        #:
        #:      {'dwc_term_1': 'value',
        #:       'dwc_term_2': 'value',
        #:       ...}
        #:
        #: Usage::
        #:
        #:      myrow.data['http://rs.tdwg.org/dwc/terms/locality']  # => "Brussels"
        #:
        #: .. note:: The :func:`dwca.darwincore.utils.qualname` helper is available to make
        #:    such calls less verbose.
        self.data = datafile_descriptor.field_plan.build_data(
            raw_fields
        )  # type: Dict[str, str]


class CoreRow(Row):
    """This class is used to represent a row/line from a Darwin Core Archive core data file.

    You probably won't instantiate it manually but rather obtain it via
    :meth:`dwca.read.DwCAReader.get_corerow_by_position`, :meth:`dwca.read.DwCAReader.get_corerow_by_id` or simply by
    looping over a :class:`dwca.read.DwCAReader` object.
    """

    def __str__(self) -> str:
        id_str = "Row id: " + str(self.id)
        return super(CoreRow, self)._build_str("Core file", id_str)

    __slots__ = ("id", "source_metadata", "extension_data_files", "_extensions")

    def _populate(self, raw_fields, position, datafile_descriptor) -> None:
        super(CoreRow, self)._populate(raw_fields, position, datafile_descriptor)

        if datafile_descriptor.id_index is not None:
            #: The row id
            self.id = raw_fields[datafile_descriptor.id_index]
        else:
            self.id = None

    def link_source_metadata(self, archive_source_metadata):
        # If we have additional metadata about the dataset we're originally
        # from (AKA source/row-level metadata), make it accessible trough
        # the source_metadata attribute

        # If this data is not available
        # (because the archive don't provide source metadata or because it
        # provide some, but not for this row, it will be set to None).
        #
        # If this method is never called, the source_metadata attribute will not exist
        field_name = "http://rs.tdwg.org/dwc/terms/datasetID"

        #: Row-level metadata (if provided by the archive).
        #: This is a non-standard DwCA feature currently that we can sometimes encounter (in downloads from GBIF.org
        #: for example).
        self.source_metadata = None

        if archive_source_metadata and (field_name in self.data):
            try:
                self.source_metadata = archive_source_metadata[self.data[field_name]]
            except KeyError:
                pass

    def link_extension_files(self, extension_data_files):
        self.extension_data_files = extension_data_files

    @property
    def extensions(self):
        # type () -> List[ExtensionRow]
        """A list of :class:`.ExtensionRow` instances that relates to this Core row."""
        # We use lazy loading
        if not hasattr(self, "_extensions"):
            self._extensions = []
            for csv_file in self.extension_data_files:
                [
                    self._extensions.append(r)
                    for r in csv_file.get_all_rows_by_coreid(self.id)
                ]

        return self._extensions

    # __key is different between CoreRow and ExtensionRow, while eq, ne and hash are identical
    # Should these 3 be factorized ? How ? Mixin ? Parent class ?
    def __key(self):
        """Return a tuple representing the row. Common ground between equality and hash."""
        # A CoreRow obtained without going through DwCAReader iteration (e.g.
        # CSVDataFile.get_row_by_position() called directly) never had link_extension_files()
        # / link_source_metadata() called on it, so self.extensions and self.source_metadata
        # don't exist. Fall back to None for those rows instead of letting the attribute
        # access raise AttributeError. This doesn't change equality for linked rows (both
        # attributes are always present after DwCAReader.next() links them).
        extensions = self.extensions if hasattr(self, "extension_data_files") else None
        source_metadata = (
            self.source_metadata if hasattr(self, "source_metadata") else None
        )

        return (
            self.descriptor,
            self.id,
            self.data,
            extensions,
            source_metadata,
            self.rowtype,
            self.raw_fields,
            self.position,
        )

    def __eq__(self, other):
        # The isinstance test is required, not just defensive: __key is name-mangled, so
        # other.__key() means other._CoreRow__key(), which an ExtensionRow (or any non-row)
        # doesn't have. Without it, comparing to anything else raises AttributeError.
        if not isinstance(other, CoreRow):
            return NotImplemented

        return self.__key() == other.__key()

    def __hash__(self):
        # __key() embeds the data dict, the raw field list and the lazily-loaded extensions,
        # none of which are hashable. Equal rows still hash equally because this is a subset
        # of the equality key.
        return hash((self.descriptor, self.id, self.rowtype, self.position))


class ExtensionRow(Row):
    """This class is used to represent a row/line from a Darwin Core Archive extension data file.

    Most of the time, you won't instantiate it manually but rather obtain it trough the extensions
    attribute of :class:`.CoreRow`.
    """

    def __str__(self):
        id_str = "Core row id: " + str(self.core_id)
        return super(ExtensionRow, self)._build_str("Extension file", id_str)

    __slots__ = ("core_id",)

    def _populate(self, raw_fields, position, datafile_descriptor) -> None:
        super(ExtensionRow, self)._populate(raw_fields, position, datafile_descriptor)

        #: The id of the core row this extension row is referring to.
        self.core_id = raw_fields[datafile_descriptor.coreid_index]

    def __key(self):
        """Return a tuple representing the row. Common ground between equality and hash."""
        return (
            self.descriptor,
            self.core_id,
            self.data,
            self.rowtype,
            self.raw_fields,
            self.position,
        )

    def __eq__(self, other):
        # See the note on CoreRow.__eq__: __key is name-mangled, so this test is what keeps
        # comparisons against a CoreRow (or anything else) from raising AttributeError.
        if not isinstance(other, ExtensionRow):
            return NotImplemented

        return self.__key() == other.__key()

    def __hash__(self):
        return hash((self.descriptor, self.core_id, self.rowtype, self.position))


def csv_line_to_fields(csv_line, line_ending, field_ending, fields_enclosed_by):
    """Split a line from a CSV file.

    Return a list of fields. Content is not trimmed.
    """
    # A carriage return is stripped alongside the declared terminator: archives routinely
    # declare "\n" while the file itself has CRLF line endings. This matches both the csv
    # module's own behavior and CSVDataFile._iter_field_lists, so the two access paths agree.
    csv_line = csv_line.rstrip(line_ending + "\r")

    if fields_enclosed_by == "":
        # No enclosure: the line is simply split on the separator. This also keeps any
        # quote character that happens to appear in the content.
        return csv_line.split(field_ending)

    # The csv module unwraps the enclosure and un-doubles escaped quote characters itself.
    # Stripping the quote character afterwards would eat a legitimate leading or trailing
    # one from the field's own content.
    for row in csv.reader(
        [csv_line],
        delimiter=field_ending,
        quotechar=fields_enclosed_by,
        quoting=csv.QUOTE_MINIMAL,
    ):
        return row

    return []
