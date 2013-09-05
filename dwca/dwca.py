# -*- coding: utf-8 -*-
import io
import os
from tempfile import mkdtemp
from zipfile import ZipFile
from shutil import rmtree

from bs4 import BeautifulSoup


class DwCALine():
    # TODO: if core line: display the number of related extension lines ?
    # TODO: test string representation
    def __str__(self):
        txt = "--\n"

        txt += "Rowtype: " + self.rowtype + "\n"

        if self.from_core:
            txt += "Source: Core file\n"
        else:
            txt += "Source: Extension file\n"

        try:
            txt += 'Line ID: ' + self.id + "\n"
        except AttributeError:
            pass

        try:
            txt += 'Core ID: ' + self.core_id + "\n"
        except AttributeError:
            pass

        txt += "Data: " + str(self.data)

        txt += '\n--'
        return txt

    def __init__(self, line, is_core_type, metadata, unzipped_folder=None,
                 archive_source_metadata=None):
        # line is the raw line data, directly from file
        # is_core is a flag:
        #   if True:
        #        - metadata contains the whole metaxml
        #        - it will also recursively load the related lines
        #          in the 'extensions' attribute (and unzipped_folder
        #          should be provided for this)
        #   else:
        #        - metadata contains only the <extension> section about our
        #          file
        #        - we don't load other lines recursively
        #
        # source metadata: dict of all the source metadata available in the
        # archive (if applicable)

        self.from_core = is_core_type
        self.from_extension = not self.from_core

        if self.from_core:
            my_meta = metadata.core
        else:
            my_meta = metadata

        self.rowtype = my_meta['rowType']

        # TODO: Move line/field stripping to _EmbeddedCSV ??

        # fields is a list of the line's content
        line_ending = my_meta['linesTerminatedBy'].decode("string-escape")
        field_ending = my_meta['fieldsTerminatedBy'].decode("string-escape")
        fields = line.rstrip(line_ending).split(field_ending)

        # TODO: Consistency chek ?? fields length should be :
        # num of fields described in core_meta + 2 (id and \n)

        # If core, we have an id; if extension a coreid
        # TODO: ensure in the norm this is always true
        self.id = None
        self.core_id = None

        if self.from_core:
            self.id = fields[int(my_meta.id['index'])]
        else:
            self.core_id = fields[int(my_meta.coreid['index'])]

        self.data = {}

        for f in my_meta.findAll('field'):
            # if field by default, we can find its value directly in <field>
            # attribute

            if f.has_attr('default'):
                self.data[f['term']] = f['default']
            else:
                # else, we have to look in core file
                self.data[f['term']] = fields[int(f['index'])]

        # Core line: we also need to store related (extension) lines in the
        # extensions attribute

        self.extensions = []

        if self.from_core:
            for ext_meta in metadata.findAll('extension'):
                csv = _EmbeddedCSV(ext_meta, unzipped_folder)
                for l in csv.lines():
                    tmp = DwCALine(l, False, ext_meta)
                    if tmp.core_id == self.id:
                        self.extensions.append(tmp)

        # If we have additional metadata about the dataset we're originally
        # from (AKA source/line-level metadata), make it accessible trough
        # the source_metadata attribute

        # If this data is not available
        # (because the archive don't provide source metadata or because it
        # provide some, but not for this dataset, it will be None)
        field_name = 'http://rs.tdwg.org/dwc/terms/datasetID'

        if (archive_source_metadata and (field_name in self.data)):
            try:
                m = archive_source_metadata[self.data[field_name]]
            except KeyError:
                m = None
        else:
            m = None

        self.source_metadata = m

    # Equality, hashing, ...
    def __key(self):
        """Returns a tuple representing the line. Common ground between equality and hash."""
        return (self.from_core, self.from_extension, self.id, self.core_id, self.data,
                self.extensions, self.source_metadata)

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__key())


class DwCAReader(object):
    # Define __enter__ and __exit__ to be used with the 'with' statement
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __init__(self, path):
        """Opens the file, reads all metadata and store it in self.meta
        (BeautifulSoup obj.) Also already open the core file so we've
        a file descriptor for further access."""
        self.archive_path = path

        self._unzipped_folder_path = self._unzip()
        self._metaxml = self._parse_metaxml_file()

        # Load the (scientific) metadata file and store its representation
        # in metadata attribute for future use.
        self.metadata = self._parse_metadata_file()
        self.core_rowtype = self._get_core_type()
        self.extensions_rowtype = self._get_extensions_types()

        self._corefile = _EmbeddedCSV(self._metaxml.core,
                                      self._unzipped_folder_path)

    @property
    #TODO: decide, test and document what we guarantee about ordering
    def lines(self):
        """Get a list containing all (core) lines of the archive"""
        return list(self.each_line())

    def get_line(self, line_id):
        """Get the line whose id is line_id."""
        for line in self.each_line():
            if line.id == str(line_id):
                return line
        else:
            return None

    def absolute_temporary_path(self, relative_path):
        """Returns the absolute path of the file located at relative_path within the archive.

        Notes:
            - The file at this path is temporary and will be removed when closing the instance.
            - File existence is not tested
        """

        return os.path.abspath(os.path.join(self._unzipped_folder_path, relative_path))

    def _read_additional_file(self, relative_path):
        """Read an additional file in the archive and return its content."""
        p = self.absolute_temporary_path(relative_path)
        return open(p).read()

    def _create_temporary_folder(self):
        return mkdtemp()[1]

    def _parse_metadata_file(self):
        """Loads the archive (scientific) Metadata file, parse it with
        BeautifulSoup and return its content."""

        # This method should be called only after ._metaxml attribute is set
        # because the name/path to metadat file is stored in the "metadata"
        # attribute of the "archive" tag
        metadata_file = self._get_metadata_filename()
        return self._parse_xml_included_file(metadata_file)

    def _parse_metaxml_file(self):
        """Loads the meta.xml, parse it with BeautifulSoup and return its
        content."""
        return self._parse_xml_included_file('meta.xml')

    def _parse_xml_included_file(self, relative_path):
        """Loads, parse with BeautifulSoup and returns XML file located
        at relative_path."""
        return BeautifulSoup(self._read_additional_file(relative_path), "xml")

    def _unzip(self):
        """Unzip the current archive in a temporary directory and returns its path."""
        unzipped_folder = self._create_temporary_folder()
        #TODO: check content of file!!!! It may, for example contains
        #absolute path (see zipfile doc)
        ZipFile(self.archive_path, 'r').extractall(unzipped_folder)
        return unzipped_folder

    def close(self):
        self._cleanup_temporary_folder()

    def _cleanup_temporary_folder(self):
        rmtree(self._unzipped_folder_path, False)

    def _get_core_type(self):
        return self._metaxml.core['rowType']

    def _get_extensions_types(self):
        return [e['rowType'] for e in self._metaxml.findAll('extension')]

    def core_contains_term(self, term_url):
        return term_url in self.core_terms

    @property
    def core_terms(self):
        """Returns a set of all the terms (URL) contained in Core file."""
        term_names = [f['term'] for f in self._metaxml.core.findAll('field')]
        return set(term_names)

    def _get_metadata_filename(self):
        return self._metaxml.archive['metadata']

    #TODO: decide, test and document what we guarantee about ordering
    # We'll have to edit test_lines_property() if we don't guarantee the
    # same order
    def each_line(self):
        self._corefile.reset_line_iterator()

        # Some Archives (Currently GBIF Results) have line-level (source data)
        # In that case, we'll pass all of them to the line.
        try:
            sm = self.source_metadata
        except AttributeError:
            sm = None

        for line in self._corefile.lines():
            yield DwCALine(line, True, self._metaxml, self._unzipped_folder_path, sm)


class GBIFResultsReader(DwCAReader):
    def __init__(self, path):
        super(GBIFResultsReader, self).__init__(path)

        self.source_metadata = self._dataset_metadata_to_dict('dataset')

    # Compared to a standard DwC-A, GBIF results export contains
    # two additional files to give details about IP rights and citations
    # We make them accessible trough two simples properties
    def _dataset_metadata_to_dict(self, folder):
        dataset_dir = os.path.join(self._unzipped_folder_path, folder)

        r = {}
        for f in os.listdir(dataset_dir):
            if os.path.isfile(os.path.join(dataset_dir, f)):
                key = os.path.splitext(f)[0]
                r[key] = self._parse_xml_included_file(os.path.join(folder, f))

        return r

    @property
    def citations(self):
        return self._read_additional_file('citations.txt')

    @property
    def rights(self):
        return self._read_additional_file('rights.txt')


class _EmbeddedCSV:
    """Internal use class used to encapsulate a DwcA-enclosed CSV file and its metadata."""
    # TODO: Test this class
    # Not done yet cause issues there will probably make DwCAReader tests fails anyway
    # In the future it could make sense to make it public
    def __init__(self, metadata_section, unzipped_folder_path):
        #metadata_section: <core> or <extension> section of metaxml concerning the file to iterate.
        #unzipped_folder_path: absolute path to the directory containing the unzipped archive.
        
        self._metadata_section = metadata_section
        self._unzipped_folder_path = unzipped_folder_path

        self._core_fhandler = io.open(self.filepath,
                                      mode='r',
                                      encoding=self._get_encoding(),
                                      newline=self._get_newline_str(),
                                      errors='replace')
        self.reset_line_iterator()

    def lines(self):
        for line in self._core_fhandler:
            self._line_pointer += 1

            if (self._line_pointer <= self._get_lines_to_ignore()):
                continue
            else:
                yield line

    @property
    def headers(self):
        """Returns a list of (ordered) column names that can be used to create a header line."""
        field_tags = self._metadata_section.find_all('field')

        columns = {}
        
        for tag in field_tags:
            columns[int(tag['index'])] = tag['term']

        # In addition to DwC terms, we may also have id or core_id columns
        if self._metadata_section.id:
            columns[int(self._metadata_section.id['index'])] = 'id'
        if self._metadata_section.coreid:
            columns[int(self._metadata_section.id['coreindex'])] = 'coreid'

        return [columns[f] for f in sorted(columns.iterkeys())]

    @property
    def filepath(self):
        """Returns the absolute path to the 'subject' file."""
        return os.path.join(self._unzipped_folder_path,
                            self._metadata_section.files.location.string)

    def _get_encoding(self):
        return self._metadata_section['encoding']

    def _get_newline_str(self):
        return self._metadata_section['linesTerminatedBy'].decode("string-escape")

    def reset_line_iterator(self):
        self._core_fhandler.seek(0, 0)
        self._line_pointer = 0

    def _get_lines_to_ignore(self):
        try:
            return int(self._metadata_section['ignoreHeaderLines'])
        except KeyError:
            return 0
