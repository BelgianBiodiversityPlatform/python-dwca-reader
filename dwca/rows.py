"""Objects that represents data rows coming from DarwinCore Archives."""

import csv
import sys
from typing import Dict, Optional

from dwca.descriptors import DataFileDescriptor
from dwca.exceptions import InvalidArchive


class Row(object):
    """This class is used to represent a row/line in a Darwin Core Archive.

    This class is intended to be subclassed rather than used directly.
    """

    # Common ground for __str__ between subclasses
    def _build_str(self, source_str, id_str):
        txt = ("--\n"
               "Rowtype: {rowtype}\n"
               "Position: {position}\n"
               "Source: {source_str}\n"
               "{id_row}\n"
               "Reference extension rows: {extension_flag}\n"
               "Reference source metadata: {source_metadata_flag}\n"
               "Data: {data}\n"
               "--\n")

        extension_flag = "Yes" if (hasattr(self, 'extensions') and (len(self.extensions) > 0)) else "No"

        if hasattr(self, 'source_metadata') and (self.source_metadata is not None):
            source_metadata_flag = 'Yes'
        else:
            source_metadata_flag = 'No'

        return txt.format(rowtype=self.rowtype,
                          position=self.position,
                          source_str=source_str,
                          data=self.data,
                          id_row=id_str,
                          extension_flag=extension_flag,
                          source_metadata_flag=source_metadata_flag)

    def __init__(self, csv_line: str, position: int, datafile_descriptor: DataFileDescriptor) -> None:

        #: An instance of :class:`dwca.descriptors.DataFileDescriptor` describing the originating
        #: data file.
        self.descriptor = datafile_descriptor  # type: DataFileDescriptor 

        #: The row position/index (starting at 0) in the source data file. This can be used, for example with
        #: :meth:`dwca.read.DwCAReader.get_corerow_by_position` or :meth:`dwca.files.CSVDataFile.get_row_by_position`.
        self.position = position  # type: int

        #: The csv line type as stated in the archive descriptor.
        #: (or None if the archive has no descriptor). Examples:
        #: http://rs.tdwg.org/dwc/terms/Occurrence,
        #: http://rs.gbif.org/terms/1.0/VernacularName, ...
        self.rowtype = self.descriptor.type  # type: Optional[str]

        # self.raw_fields is a list of the csv_line's content
        #:
        self.raw_fields = csv_line_to_fields(csv_line,
                                             line_ending=self.descriptor.lines_terminated_by,
                                             field_ending=self.descriptor.fields_terminated_by,
                                             fields_enclosed_by=self.descriptor.fields_enclosed_by)

        # TODO: raw_fields is a new property: to test

        # TODO: Consistency check ?? self.raw_fields length should be :
        # num of self.raw_fields described in core_meta + 2 (id and \n)

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
        #: .. note:: The :func:`dwca.darwincore.utils.qualname` helper is available to make such calls less verbose.
        self.data = {}  # type: Dict[str, str]

        for field_descriptor in self.descriptor.fields:
            try:
                column_index = int(field_descriptor['index'])
                field_row_value = self.raw_fields[column_index]
            except TypeError:
                # int() argument must be a string... We don't have an index for this field
                field_row_value = None
            except IndexError:
                msg = 'The descriptor references a non-existent field (index={i})'.format(i=column_index)
                raise InvalidArchive(msg)

            field_default_value = field_descriptor['default']

            self.data[field_descriptor['term']] = field_row_value or field_default_value or ''


class CoreRow(Row):
    """This class is used to represent a row/line from a Darwin Core Archive core data file.

    You probably won't instantiate it manually but rather obtain it via
    :meth:`dwca.read.DwCAReader.get_corerow_by_position`, :meth:`dwca.read.DwCAReader.get_corerow_by_id` or simply by
    looping over a :class:`dwca.read.DwCAReader` object.
    """

    def __str__(self) -> str:
        id_str = "Row id: " + str(self.id)
        return super(CoreRow, self)._build_str("Core file", id_str)

    def __init__(self, csv_line: str, position: int, datafile_descriptor: DataFileDescriptor) -> None:
        super(CoreRow, self).__init__(csv_line, position, datafile_descriptor)

        if self.descriptor.id_index is not None:
            #: The row id
            self.id = self.raw_fields[self.descriptor.id_index]
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
        field_name = 'http://rs.tdwg.org/dwc/terms/datasetID'

        #: Row-level metadata (if provided by the archive).
        #: This is a non-standard DwCA feature currently that we can sometimes encounter (in downloads from GBIF.org
        #: for example).
        self.source_metadata = None

        if (archive_source_metadata and (field_name in self.data)):
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
        if not hasattr(self, '_extensions'):
            self._extensions = []
            for csv_file in self.extension_data_files:
                [self._extensions.append(r) for r in csv_file.get_all_rows_by_coreid(self.id)]

        return self._extensions

    # __key is different between CoreRow and ExtensionRow, while eq, ne and hash are identical
    # Should these 3 be factorized ? How ? Mixin ? Parent class ?
    def __key(self):
        """Return a tuple representing the row. Common ground between equality and hash."""
        return (self.descriptor, self.id, self.data, self.extensions, self.source_metadata,
                self.rowtype, self.raw_fields, self.position)

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__key())


class ExtensionRow(Row):
    """This class is used to represent a row/line from a Darwin Core Archive extension data file.

    Most of the time, you won't instantiate it manually but rather obtain it trough the extensions
    attribute of :class:`.CoreRow`.
    """

    def __str__(self):
        id_str = "Core row id: " + str(self.core_id)
        return super(ExtensionRow, self)._build_str("Extension file", id_str)

    def __init__(self, csv_line: str, position: int, datafile_descriptor: DataFileDescriptor) -> None:
        super(ExtensionRow, self).__init__(csv_line, position, datafile_descriptor)

        #: The id of the core row this extension row is referring to.
        self.core_id = self.raw_fields[datafile_descriptor.coreid_index]

    def __key(self):
        """Return a tuple representing the row. Common ground between equality and hash."""
        return (self.descriptor, self.core_id, self.data, self.rowtype, self.raw_fields, self.position)

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__key())


def csv_line_to_fields(csv_line, line_ending, field_ending, fields_enclosed_by):
    """Split a line from a CSV file.

    Return a list of fields. Content is not trimmed.
    """
    csv_line = csv_line.rstrip(line_ending)
    raw_fields = []

    if fields_enclosed_by == "":
        opts = {'quoting': csv.QUOTE_NONE}
    else:
        opts = {'quoting': csv.QUOTE_ALL,
                'quotechar': fields_enclosed_by}

    for row in csv.reader([csv_line], delimiter=field_ending, **opts):
        for f in row:
            field = f.strip(fields_enclosed_by)
            raw_fields.append(field)
    return raw_fields
