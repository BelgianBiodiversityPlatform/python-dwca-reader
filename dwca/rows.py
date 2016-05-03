# -*- coding: utf-8 -*-

"""This module provides objects that represents data rows coming from DarwinCore Archive."""

from dwca.exceptions import InvalidArchive


# TODO: Make it abstract ? Private ?
class Row(object):
    """This class is used to represent a row/line in a Darwin Core Archive.

    This class is intended to be subclassed rather than used directly.
    """

    # Common ground for __str__ between subclasses
    def _build_str(self, source_str, id_str):
        txt = ("--\n"
               "Rowtype: {rowtype}\n"
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
                          source_str=source_str,
                          data=self.data,
                          id_row=id_str,
                          extension_flag=extension_flag,
                          source_metadata_flag=source_metadata_flag)

    def __init__(self, csv_line, descriptor):
        #: An instance of :class:`dwca.descriptors.DataFileDescriptor` describing the originating
        #: data file.
        self.descriptor = descriptor

        #: The csv line type as stated in the archive descriptor.
        #: Examples: http://rs.tdwg.org/dwc/terms/Occurrence,
        #: http://rs.gbif.org/terms/1.0/VernacularName, ...
        self.rowtype = self.descriptor.type

        line_ending = self.descriptor.lines_terminated_by
        field_ending = self.descriptor.fields_terminated_by

        fields_enclosed_by = self.descriptor.fields_enclosed_by

        # self.raw_fields is a list of the csv_line's content
        #:
        self.raw_fields = []
        for f in csv_line.rstrip(line_ending).split(field_ending):
            self.raw_fields.append(f.strip(fields_enclosed_by))

        # TODO: raw_fields is a new property: to test

        # TODO: Consistency chek ?? self.raw_fields length should be :
        # num of self.raw_fields described in core_meta + 2 (id and \n)

        #: A dict containing the Row data, such as:
        #: {'dwc_term_1': 'value',
        #: 'dwc_term_2': 'value',
        #: ...}.
        #:
        #: Example::
        #:
        #:      print myrow.data['http://rs.tdwg.org/dwc/terms/locality']  # => "Brussels"
        #:
        #: .. note:: The :func:`dwca.darwincore.utils.qualname` helper is avalaible to make such calls less verbose.
        self.data = {}

        for f in self.descriptor.fields:
            # if field by default, we can find its value directly in <field>
            # attribute
            if f['default'] is not None:
                self.data[f['term']] = f['default']
            else:
                # else, we have to look in core file
                field_index = int(f['index'])
                try:
                    self.data[f['term']] = self.raw_fields[field_index]
                except IndexError:
                    msg = 'The descriptor references a non-existent field (index={i})'.format(i=field_index)
                    raise InvalidArchive(msg)


class CoreRow(Row):
    """This class is used to represent a row/line from a Darwin Core Archive data core file.

    You probably won't instantiate it manually but rather obtain it trough :class:`read.DwCAReader`
    or :class:`read.GBIFResultsReader` (by iterating, using the rows attribute, get_row_by_index,
    get_row_by_id, ...).
    """

    def __str__(self):
        id_str = "Row id: " + str(self.id)
        return super(CoreRow, self)._build_str("Core file", id_str)

    def __init__(self, line, section_descriptor):
        super(CoreRow, self).__init__(line, section_descriptor)

        #: The row id (from the data file).
        if self.descriptor.id_index is not None:
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

        if (archive_source_metadata and (field_name in self.data)):
            try:
                m = archive_source_metadata[self.data[field_name]]
            except KeyError:
                m = None
        else:
            m = None

        #: Row-level metadata (if provided by the archive).
        #: This is a non-standard feature currently only provided when using
        #: :class:`dwca.read.GBIFResultsReader`.
        self.source_metadata = m

    def link_extension_files(self, extension_data_files):
        self.extension_data_files = extension_data_files

    #: A list of :class:`.ExtensionRow` instances that relates to this Core row.
    @property
    def extensions(self):
        # We use lazy loading
        if not hasattr(self, '_extensions'):
            self._extensions = []
            for csv in self.extension_data_files:
                [self._extensions.append(r) for r in csv.get_all_rows_by_coreid(self.id)]

        return self._extensions

    # __key is different between CoreRow and ExtensionRow, while eq, ne and hash are identical
    # Should these 3 be factorized ? How ? Mixin ? Parent class ?
    def __key(self):
        """Return a tuple representing the row. Common ground between equality and hash."""
        return (self.descriptor, self.id, self.data, self.extensions, self.source_metadata,
                self.rowtype, self.raw_fields)

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__key())


class ExtensionRow(Row):
    """This class is used to represent a row/line from a Darwin Core Archive extension file.

    Most of the time, you won't instantiate it manually but rather obtain it trough the extensions
    attribute of :class:`.CoreRow`.
    """

    def __str__(self):
        id_str = "Core row id: " + str(self.core_id)
        return super(ExtensionRow, self)._build_str("Extension file", id_str)

    def __init__(self, line, descriptor):
        super(ExtensionRow, self).__init__(line, descriptor)

        #: The id of the core row this extension is reffering to.
        self.core_id = self.raw_fields[descriptor.coreid_index]

    def __key(self):
        """Return a tuple representing the row. Common ground between equality and hash."""
        return (self.descriptor, self.core_id, self.data, self.rowtype, self.raw_fields)

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__key())
