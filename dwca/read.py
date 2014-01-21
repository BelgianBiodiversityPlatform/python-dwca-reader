# -*- coding: utf-8 -*-

import os
from tempfile import mkdtemp
from zipfile import ZipFile
from shutil import rmtree

from bs4 import BeautifulSoup

from dwca.rows import CoreRow
from dwca.utils import _EmbeddedCSV
from dwca.exceptions import RowNotFound


class DwCAReader(object):
    
    """This class is used to represent a Darwin Core Archive as a whole.

    It gives read access to the (Core file) rows, to the Archive metadata, ...

    A short usage example::

        from dwca import DwCAReader

        # The with statement is recommended as it ensures resources will be properly cleaned after
        # usage:
        with DwCAReader('my_archive.zip') as dwca:
            # Iterating on core rows is easy:
            for core_row in dwca:
                # core_row is an instance of rows.CoreRow
                print core_row

            # Scientific metadata (EML) is available as a BeautifulSoup object
            print dwca.metadata.prettify()

    """

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __init__(self, path):
        """Open the file, reads all metadata and store it in self.meta
        (BeautifulSoup obj.) Also already open the core file so we've
        a file descriptor for further access.

        :param path: path to the Darwin Core Archive file to open.
        """
        #:
        self.archive_path = path

        self._unzipped_folder_path = self._unzip()
        
        #: A BeautifulSoup instance containing the archive descriptor (``meta.xml``)
        self.descriptor = self._parse_metaxml_file()

        # Load the (scientific) metadata file and store its representation in an attribute
        #:
        self.metadata = self._parse_metadata_file()
        #:
        self.source_metadata = None
        #:
        self.core_rowtype = self._get_core_type()
        #:
        self.extensions_rowtype = self._get_extensions_types()

        self._corefile = _EmbeddedCSV(self.descriptor.core,
                                      self._unzipped_folder_path)

    @property
    #TODO: decide, test and document what we guarantee about ordering
    def rows(self):
        """Return all rows from the core file as a list of :class:`rows.CoreRow` instances."""
        return list(self)

    def get_row_by_id(self, row_id):
        """Return the (Core) row whose id is row_id. Raise RowNotFound if no match.

        .. warning::

            It is rarely a good idea to rely on the row ID, because:
            1) Not all Darwin Core Archives specifies row IDs.
            2) Nothing guarantees that the ID will actually be unique within the archive (depends
            of the data publisher). In that case, this method don't guarantee which one will be
            returned. :meth:`.get_row_by_index` may be more appropriate in this case.

        """
        for row in self:
            if row.id == str(row_id):
                return row
        else:
            raise RowNotFound

    def get_row_by_index(self, index):
        """Return a core row according to its index in core file. Raise RowNotFound if no match.

        .. note::

            - First row has index 0
            - If index is bigger than the length of the archive, None is returned
            - The index is often an appropriate way to unambiguously identify a core row in a DwCA.

        """
        for (i, row) in enumerate(self):
            if i == index:
                return row
        else:
            raise RowNotFound

    def absolute_temporary_path(self, relative_path):
        """Return the absolute path of the file located at relative_path within the archive.

        .. note::
            - This method allows raw access to the files contained in the archive. It is for\
            example useful to open additional, non-standard files embedded in the archive.
            - The file at this path is temporary and will be removed when closing the instance.
            - File existence is not tested.

        """
        return os.path.abspath(os.path.join(self._unzipped_folder_path, relative_path))

    def _read_additional_file(self, relative_path):
        """Read an additional file in the archive and return its content."""
        p = self.absolute_temporary_path(relative_path)
        return open(p).read()

    @staticmethod
    def _create_temporary_folder():
        return mkdtemp()[1]

    def _parse_metadata_file(self):
        """Load the archive (scientific) Metadata file, parse it with
        BeautifulSoup and return its content."""

        # This method should be called only after descriptor attribute is set
        # because the name/path to metadata file is stored in the "metadata"
        # attribute of the "archive" tag
        metadata_file = self._get_metadata_filename()
        return self._parse_xml_included_file(metadata_file)

    def _parse_metaxml_file(self):
        """Load the meta.xml, parse it with BeautifulSoup and return its
        content."""
        return self._parse_xml_included_file('meta.xml')

    def _parse_xml_included_file(self, relative_path):
        """Load, parse with BeautifulSoup and returns XML file located
        at relative_path."""
        return BeautifulSoup(self._read_additional_file(relative_path), "xml")

    def _unzip(self):
        """Unzip the current archive in a temporary directory and return its path."""
        unzipped_folder = self._create_temporary_folder()
        #TODO: check content of file!!!! It may, for example contains
        #absolute path (see zipfile doc)
        ZipFile(self.archive_path, 'r').extractall(unzipped_folder)
        return unzipped_folder

    def close(self):
        """Close the Darwin Core Archive and cleanup temporary/working files.

        .. note::
            - Alternatively, :class:`.DwCAReader` can be instanciated using the `with` statement.\
            Cleanup will then be automatically performed when leaving the block.

        """
        self._cleanup_temporary_folder()

    def _cleanup_temporary_folder(self):
        rmtree(self._unzipped_folder_path, False)

    def _get_core_type(self):
        return self.descriptor.core['rowType']

    def _get_extensions_types(self):
        return [e['rowType'] for e in self.descriptor.findAll('extension')]

    def core_contains_term(self, term_url):
        """Return True if the Core file of the archive contains the term_url term."""
        return term_url in self.core_terms

    @property
    def core_terms(self):
        """Return a Set containing all the Darwin Core terms appearing in Core file."""
        term_names = [f['term'] for f in self.descriptor.core.findAll('field')]
        return set(term_names)

    def _get_metadata_filename(self):
        return self.descriptor.archive['metadata']

    def __iter__(self):
        self._corefile_pointer = 0
        return self

    def next(self):
        cl = self._corefile.get_row_by_index(self._corefile_pointer)
        if cl:
            self._corefile_pointer = self._corefile_pointer + 1
            return CoreRow(cl, self.descriptor, self._unzipped_folder_path, self.source_metadata)
        else:
            raise StopIteration


class GBIFResultsReader(DwCAReader):
    
    """This class is used to represent the (slightly augmented) variant of Darwin Core Archive
    produced by the new GBIF Data Portal when exporting occurrences.


    It is a subclass of :class:`.DwCAReader` and provides a few more features that reflect the
    additional data provided in these specific archives:

        - The content of `citations.txt` and `rights.txt` is available via specific properties.
        - (core) Rows accessed trough this class have a `source_metadata` property that gives\
        access to the metadata of the originating dataset.

    """
    
    def __init__(self, path):
        super(GBIFResultsReader, self).__init__(path)
        #: a dict containing source/original metadata of the archive, such as
        #: {'dataset_uuid': 'dataset_metadata', ...}
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
