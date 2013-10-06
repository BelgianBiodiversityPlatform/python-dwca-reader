# -*- coding: utf-8 -*-
import os
from tempfile import mkdtemp
from zipfile import ZipFile
from shutil import rmtree

from bs4 import BeautifulSoup

from lines import DwCACoreLine
from utils import _EmbeddedCSV


class DwCAReader(object):
    
    """This class is used to represent a Darwin Core Archive as a whole.

    It gives read access to the data lines (from the Core file), to the Archive metadata, ...
    """

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __init__(self, path):
        """Opens the file, reads all metadata and store it in self.meta
        (BeautifulSoup obj.) Also already open the core file so we've
        a file descriptor for further access.

        :param path: path to the Darwin Core Archive file to open.
        """
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
        """Returns all rows from the core file as a list of :class:`lines.DwCACoreLine` instances."""
        return list(self.each_line())

    def get_line_by_id(self, line_id):
        """Return the (Core) line whose id is line_id.

        .. warning::

            It is rarely a good idea to rely on the line ID, because:
            1) Not all Darwin Core Archives specifies line IDs.
            2) Nothing guarantees that the ID will actually be unique within the archive (depends
            of the data publisher). In that case, this method don't guarantee which one will be
            returned. :meth:`.get_line_by_index` may be more appropriate in this case.

        """
        for line in self.each_line():
            if line.id == str(line_id):
                return line
        else:
            return None

    def get_line_by_index(self, index):
        """Return a core line according to its index in core file.

        .. note::

            - First line has index 0
            - If index is bigger than the length of the archive, None is returned
            - The index is often an appropriate way to unambiguously identify a core line in a DwCA.

        """
        for (i, line) in enumerate(self.each_line()):
            if i == index:
                return line
        else:
            return None

    def absolute_temporary_path(self, relative_path):
        """Returns the absolute path of the file located at relative_path within the archive.

        Notes:
            - The file at this path is temporary and will be removed when closing the instance.
            - File existence is not tested.
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
        # because the name/path to metadata file is stored in the "metadata"
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
        """Close the Darwin Core Archive and cleanup temporary/working files."""
        self._cleanup_temporary_folder()

    def _cleanup_temporary_folder(self):
        rmtree(self._unzipped_folder_path, False)

    def _get_core_type(self):
        return self._metaxml.core['rowType']

    def _get_extensions_types(self):
        return [e['rowType'] for e in self._metaxml.findAll('extension')]

    def core_contains_term(self, term_url):
        """Returns True if the core file of the archive contains the term_url term, False otherwise."""
        return term_url in self.core_terms

    @property
    def core_terms(self):
        """Returns a set of all the terms (URL) contained in Core file."""
        term_names = [f['term'] for f in self._metaxml.core.findAll('field')]
        return set(term_names)

    def _get_metadata_filename(self):
        return self._metaxml.archive['metadata']

    def each_line(self):
        """Iterates, in order, over each (core) line of the Archive."""
        self._corefile.reset_line_iterator()

        # Some Archives (Currently GBIF Results) have line-level (source data)
        # In that case, we'll pass all of them to the line.
        try:
            sm = self.source_metadata
        except AttributeError:
            sm = None

        for line in self._corefile.lines():
            yield DwCACoreLine(line, self._metaxml, self._unzipped_folder_path, sm)


class GBIFResultsReader(DwCAReader):
    
    """This class is used to represent the (slightly augmented) variant of Darwin Core Archive
    produced by the new GBIF Data Portal when exporting occurrences.


    It is a subclass of :class:`.DwCAReader` and provides a few more features that reflect the
    additional data provided in these specific archives:

        - The content of `citations.txt` and `rights.txt` is available via specific properties.
        - Core lines accessed trough this class have a `source_metadata` property that gives\
        access to the metadata of the originating dataset.

    """
    
    def __init__(self, path):
        super(GBIFResultsReader, self).__init__(path)

        self.source_metadata = self._dataset_metadata_to_dict('dataset')

    def _dataset_metadata_to_dict(self, folder):
        dataset_dir = os.path.join(self._unzipped_folder_path, folder)

        r = {}
        for f in os.listdir(dataset_dir):
            if os.path.isfile(os.path.join(dataset_dir, f)):
                key = os.path.splitext(f)[0]
                r[key] = self._parse_xml_included_file(os.path.join(folder, f))

        return r

    # Compared to a standard DwC-A, GBIF results export contains
    # two additional files to give details about IP rights and citations
    # We make them accessible trough two simples properties

    @property
    def citations(self):
        """Return the content of the citations.txt file included in the archive."""
        return self._read_additional_file('citations.txt')

    @property
    def rights(self):
        """Return the content of the rights.txt file included in the archive."""
        return self._read_additional_file('rights.txt')
