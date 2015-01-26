# -*- coding: utf-8 -*-

"""This module provides high-level classes to open and read DarwinCore Archive (DwC-A) files.

"""

import os
from tempfile import mkdtemp
from zipfile import ZipFile
from shutil import rmtree

from bs4 import BeautifulSoup

from dwca.utils import _DataFile
from dwca.descriptors import ArchiveDescriptor
from dwca.exceptions import RowNotFound


class DwCAReader(object):
    
    """This class is used to represent a Darwin Core Archive as a whole.

    It gives read access to the contained data, to the scientific metadata, ...

    :param path: path to the Darwin Core Archive (either a zip file or a directory) to open.
    :type path: str

    A short usage example::

        from dwca import DwCAReader
        
        dwca = DwCAReader('my_archive.zip')
        # Iterating on core rows is easy:
        for core_row in dwca:
            # core_row is an instance of rows.CoreRow
            print core_row

        # Scientific metadata (EML) is available as a BeautifulSoup object
        print dwca.metadata.prettify()

        # Close the archive to free resources
        dwca.close()

    The archive can also be opened with the `with` statement. This is recommended, since it ensures
    resources will be properly cleaned after usage:

    ::

        from dwca import DwCAReader

        with DwCAReader('my-archive.zip') as dwca:
            pass  # Do what you want

        # When leaving the block, resources are automatically freed.

    """

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __init__(self, path):
        """Open the file, reads all metadata and store it in self.metadata (BeautifulSoup obj.)
        Also already open the core file so we've a file descriptor for further access.
        """
        #: The path to the Darwin Core Archive file, as passed to the constructor.
        self.archive_path = path

        if os.path.isdir(self.archive_path):  # Archive as a directly readable directory
            self._workin_directory_path = self.archive_path
            self._workin_directory_cleanable = False
        else:  # Archive is zipped, we have to unzip it
            self._workin_directory_path = self._unzip()
            self._workin_directory_cleanable = True
        
        #: An :class:`descriptors.ArchiveDescriptor` instance giving access to the archive descriptor (``meta.xml``)
        self.descriptor = ArchiveDescriptor(self._read_additional_file('meta.xml'))

        #: A :class:`BeautifulSoup` instance containing the (scientific) metadata of the archive.
        self.metadata = self._parse_metadata_file()
        #:
        self.source_metadata = None

        self._corefile = _DataFile(self.descriptor.core,
                                   self._workin_directory_path)
        self._extensionfiles = [_DataFile(d, self._workin_directory_path) for d in self.descriptor.extensions]

    @property
    #TODO: decide, test and document what we guarantee about ordering
    def rows(self):
        """A list of :class:`rows.CoreRow` instances representing the content of the archive.

        .. warning::

            This will cause all rows to be loaded in memory. In case of large Darwin Core Archive,
            you may prefer iterating with a for loop.
        """
        return list(self)

    def get_row_by_id(self, row_id):
        """Return the (core) row whose id is row_id.

        :returns:  :class:`dwca.rows.CoreRow` -- the matching row.
        :raises: :class:`dwca.exceptions.RowNotFound`

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
        """Return a core row according to its position/index in core file.

        :returns:  :class:`dwca.rows.CoreRow` -- the matching row.
        :raises: :class:`dwca.exceptions.RowNotFound`

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
        return os.path.abspath(os.path.join(self._workin_directory_path, relative_path))

    def _read_additional_file(self, relative_path):
        """Read an additional file in the archive and return its content."""
        p = self.absolute_temporary_path(relative_path)
        return open(p).read()

    def _parse_metadata_file(self):
        """Load the archive (scientific) Metadata file, parse it with
        BeautifulSoup and return its content."""

        return self._parse_xml_included_file(self.descriptor.metadata_filename)

    def _parse_xml_included_file(self, relative_path):
        """Load, parse with BeautifulSoup and returns XML file located
        at relative_path."""
        return BeautifulSoup(self._read_additional_file(relative_path), "xml")

    def _unzip(self):
        """Unzip the current archive in a temporary directory and return its path."""
        unzipped_folder = mkdtemp()[1]  # Creating a temporary folder
        #TODO: check content of file!!!! It may, for example contains
        #absolute path (see zipfile doc)
        ZipFile(self.archive_path, 'r').extractall(unzipped_folder)
        return unzipped_folder

    def close(self):
        """Close the Darwin Core Archive and cleanup temporary/working files.

        .. note::
            - Alternatively, :class:`.DwCAReader` can be instanciated using the `with` statement.\
            (see example above).

        """
        if self._workin_directory_cleanable:
            self._cleanup_temporary_folder()

    def _cleanup_temporary_folder(self):
        rmtree(self._workin_directory_path, False)

    def core_contains_term(self, term_url):
        """Return True if the Core file of the archive contains the term_url term."""
        return term_url in self.descriptor.core.terms

    def __iter__(self):
        self._corefile_pointer = 0
        return self

    def next(self):
        r = self._corefile.get_row_by_position(self._corefile_pointer)
        if r:
            # Set up linked data so the CoreRow will know about them
            r.link_extension_files(self._extensionfiles)
            r.link_source_metadata(self.source_metadata)

            self._corefile_pointer = self._corefile_pointer + 1
            return r
        else:
            raise StopIteration


class GBIFResultsReader(DwCAReader):
    
    """This class is used to represent the slightly augmented variant of Darwin Core Archive
    produced by the new GBIF Data Portal when exporting occurrences.


    It provides a few additions to :class:`.DwCAReader` that reflect the additional data provided
    in these specific archives:

        - The content of `citations.txt` and `rights.txt` is available via specific properties.
        - (core) Rows accessed trough this class have a `source_metadata` property that gives\
        access to the metadata of the originating dataset.

    """
    
    def __init__(self, path):
        super(GBIFResultsReader, self).__init__(path)
        #: A dict containing source/original metadata of the archive, such as
        #: {'dataset_uuid': 'dataset_metadata', ...}
        self.source_metadata = self._dataset_metadata_to_dict('dataset')

    def _dataset_metadata_to_dict(self, folder):
        dataset_dir = os.path.join(self._workin_directory_path, folder)

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
