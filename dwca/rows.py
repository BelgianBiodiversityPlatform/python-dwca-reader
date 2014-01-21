# -*- coding: utf-8 -*-

from dwca.utils import _EmbeddedCSV

# TODO: document attributes !


# Make it abstract ? Private ?
class Row(object):

    """This class is used to represent a row/line in a Darwin Core Archive.

    This class is intended to be subclassed.
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
        source_metadata_flag = "Yes" if (hasattr(self, 'source_metadata') and self.source_metadata) else "No"

        return txt.format(rowtype=self.rowtype,
                          source_str=source_str,
                          data=self.data,
                          id_row=id_str,
                          extension_flag=extension_flag,
                          source_metadata_flag=source_metadata_flag)

    def __init__(self, csv_line, metadata_section):
        #: The csv line type as stated in the archive descriptor.
        #: Examples: http://rs.tdwg.org/dwc/terms/Occurrence,
        #: http://rs.gbif.org/terms/1.0/VernacularName, ...
        self.rowtype = metadata_section['rowType']

        # self.raw_fields is a list of the csv_line's content
        line_ending = metadata_section['linesTerminatedBy'].decode("string-escape")
        field_ending = metadata_section['fieldsTerminatedBy'].decode("string-escape")
        #:
        self.raw_fields = csv_line.rstrip(line_ending).split(field_ending)
        # TODO: raw_fields is a new property: to test

        # TODO: Consistency chek ?? self.raw_fields length should be :
        # num of self.raw_fields described in core_meta + 2 (id and \n)

        #: a dict containing the csv_line/row data, such as:
        #: {'dwc_term_1': 'value',
        #: 'dwc_term_2': 'value',
        #: ...}
        self.data = {}

        for f in metadata_section.findAll('field'):
            # if field by default, we can find its value directly in <field>
            # attribute
            if f.has_attr('default'):
                self.data[f['term']] = f['default']
            else:
                # else, we have to look in core file
                self.data[f['term']] = self.raw_fields[int(f['index'])]

        # These properties are set by subclasses and are only listed here for documentation
        # and clarity purposes

        #:
        self.metadata_section = None


class CoreRow(Row):
    
    """ This class is used to represent a row/line from a Darwin Core Archive core file.

    It is a subclass of :class:`lines.DwCARow` and therefore inherits all of its methods and
    attributes.

    Most of the time, you won't instantiate it manually but rather obtain it trough
    :class:`dwca.DwCAReader` or :class:`dwca.GBIFResultsReader` (by iterating, using the rows
    attribute, get_row_by_index, get_row_by_id, ...).
    """
    
    def __str__(self):
        id_str = "Row id: " + str(self.id)
        return super(CoreRow, self)._build_str("Core file", id_str)

    def __init__(self, line, metadata, unzipped_folder, archive_source_metadata=None):
        # metadata = whole metaxml (we'll need it to discover extensions)
        super(CoreRow, self).__init__(line, metadata.core)

        self.metadata_section = metadata.core

        #:
        self.id = self.raw_fields[int(self.metadata_section.id['index'])]

        # Load related extension row
        #: A list of :class:`.ExtensionRow` instances that relates to this Core row
        self.extensions = []
        for ext_meta in metadata.findAll('extension'):
            csv = _EmbeddedCSV(ext_meta, unzipped_folder)
            for l in csv:
                tmp = ExtensionRow(l, ext_meta)
                if tmp.core_id == self.id:
                    self.extensions.append(tmp)

        # If we have additional metadata about the dataset we're originally
        # from (AKA source/row-level metadata), make it accessible trough
        # the source_metadata attribute

        # If this data is not available
        # (because the archive don't provide source metadata or because it
        # provide some, but not for this row, it will be set to None)
        field_name = 'http://rs.tdwg.org/dwc/terms/datasetID'

        if (archive_source_metadata and (field_name in self.data)):
            try:
                m = archive_source_metadata[self.data[field_name]]
            except KeyError:
                m = None
        else:
            m = None

        #:
        self.source_metadata = m

    # __key is different between CoreRow and ExtensionRow, while eq, ne and hash are identical
    # Should these 3 be factorized ? How ? Mixin ? Parent class ?
    def __key(self):
        """Return a tuple representing the row. Common ground between equality and hash."""
        return (self.metadata_section, self.id, self.data, self.extensions, self.source_metadata,
                self.rowtype, self.raw_fields)

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__key())


class ExtensionRow(Row):
    
    """ This class is used to represent a row/line from a Darwin Core Archive extension file.

    It is a subclass of :class:`rows.DwCARow` and therefore inherits all of its methods and
    attributes.

    Most of the time, you won't instantiate it manually but rather obtain it trough the extensions
    attribute of :class:`.CoreRow`.
    """

    def __str__(self):
        id_str = "Core row id: " + str(self.core_id)
        return super(ExtensionRow, self)._build_str("Extension file", id_str)

    def __init__(self, line, metadata):
        # metadata = only the section that concerns me
        super(ExtensionRow, self).__init__(line, metadata)

        self.metadata_section = metadata

        #:
        self.core_id = self.raw_fields[int(self.metadata_section.coreid['index'])]

    def __key(self):
        """Return a tuple representing the row. Common ground between equality and hash."""
        return (self.metadata_section, self.core_id, self.data, self.rowtype, self.raw_fields)

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__key())
