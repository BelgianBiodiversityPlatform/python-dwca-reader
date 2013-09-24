from .utils import _EmbeddedCSV


# Make it abstract ? Private ?
class DwCALine(object):
    # TODO: Split string representation between subclasses ?
    # (This one should only display the common stuff and be called by others)
    def __str__(self):
        txt = ("--\n"
               "Rowtype: {rowtype}\n"
               "Source: {source_str}\n"
               "{id_line}\n"
               "Reference extension lines: {extension_flag}\n"
               "Reference source metadata: {source_metadata_flag}\n"
               "Data: {data}\n"
               "--\n")
        
        if self.from_core:
            source_str = "Core file"
            id_str = "Line id: " + str(self.id)
        else:
            source_str = "Extension file"
            id_str = "Core Line id: " + str(self.core_id)

        extension_flag = "Yes" if (hasattr(self, 'extensions') and (len(self.extensions) > 0)) else "No"
        source_metadata_flag = "Yes" if (hasattr(self, 'source_metadata') and self.source_metadata) else "No"

        return txt.format(rowtype=self.rowtype,
                          source_str=source_str,
                          data=self.data,
                          id_line=id_str,
                          extension_flag=extension_flag,
                          source_metadata_flag=source_metadata_flag)

    def __init__(self, line, metadata_section):
        # line is the raw line data, directly from file
        self.rowtype = metadata_section['rowType']

        # TODO: Move line/field stripping to _EmbeddedCSV ??

        # self.raw_fields is a list of the line's content
        line_ending = metadata_section['linesTerminatedBy'].decode("string-escape")
        field_ending = metadata_section['fieldsTerminatedBy'].decode("string-escape")
        self.raw_fields = line.rstrip(line_ending).split(field_ending)
        # TODO: raw_fields is a new property: to test

        # TODO: Consistency chek ?? self.raw_fields length should be :
        # num of self.raw_fields described in core_meta + 2 (id and \n)

        self.data = {}

        for f in metadata_section.findAll('field'):
            # if field by default, we can find its value directly in <field>
            # attribute
            if f.has_attr('default'):
                self.data[f['term']] = f['default']
            else:
                # else, we have to look in core file
                self.data[f['term']] = self.raw_fields[int(f['index'])]


class DwCACoreLine(DwCALine):
    def __init__(self, line, metadata, unzipped_folder, archive_source_metadata=None):
        # metadata = whole metaxml (we'll need it to discover extensions)
        super(DwCACoreLine, self).__init__(line, metadata.core)

        self.metadata_section = metadata.core
        self.from_core = True
        self.from_extension = False

        self.id = self.raw_fields[int(self.metadata_section.id['index'])]

        # Extension load
        self.extensions = []
        for ext_meta in metadata.findAll('extension'):
            csv = _EmbeddedCSV(ext_meta, unzipped_folder)
            for l in csv.lines():
                tmp = DwCAExtensionLine(l, ext_meta)
                if tmp.core_id == self.id:
                    self.extensions.append(tmp)

        # If we have additional metadata about the dataset we're originally
        # from (AKA source/line-level metadata), make it accessible trough
        # the source_metadata attribute

        # If this data is not available
        # (because the archive don't provide source metadata or because it
        # provide some, but not for this line, it will be None)
        field_name = 'http://rs.tdwg.org/dwc/terms/datasetID'

        if (archive_source_metadata and (field_name in self.data)):
            try:
                m = archive_source_metadata[self.data[field_name]]
            except KeyError:
                m = None
        else:
            m = None

        self.source_metadata = m

    # __key is different between DwCACoreLine and DwCAExtensionLine, while eq, ne and hash are identical
    # Should these 3 be factorized ? How ? Mixin ? Parent class ?
    def __key(self):
        """Returns a tuple representing the line. Common ground between equality and hash."""
        return (self.from_core, self.from_extension, self.metadata_section, self.id, self.data,
                self.extensions, self.source_metadata, self.rowtype, self.raw_fields)

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__key())


class DwCAExtensionLine(DwCALine):
    def __init__(self, line, metadata):
        # metadata = only the section that concerns me
        super(DwCAExtensionLine, self).__init__(line, metadata)

        self.metadata_section = metadata
        self.from_core = False
        self.from_extension = True

        self.core_id = self.raw_fields[int(self.metadata_section.coreid['index'])]

    def __key(self):
        """Returns a tuple representing the line. Common ground between equality and hash."""
        return (self.from_core, self.from_extension, self.metadata_section, self.core_id,
                self.data, self.rowtype, self.raw_fields)

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__key())
