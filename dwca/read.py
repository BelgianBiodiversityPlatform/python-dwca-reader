# -*- coding: utf-8 -*-

"""This module provides high-level classes to open and read DarwinCore Archive."""

import os
import zipfile
import tarfile
from tempfile import mkdtemp
from shutil import rmtree
from errno import ENOENT

import xml.etree.ElementTree as ET

from dwca.files import CSVDataFile
from dwca.descriptors import ArchiveDescriptor, DataFileDescriptor
from dwca.exceptions import RowNotFound, InvalidArchive, InvalidSimpleArchive

DEFAULT_METADATA_FILENAME = "EML.xml"
METAFILE_NAME = "meta.xml"
SOURCE_METADATA_DIRECTORY = 'dataset'


class DwCAReader(object):
    """This class is used to represent a Darwin Core Archive as a whole.

    It gives read access to the contained data, to the scientific metadata, ... It supports
    archives with or without Metafiles, such as described on page 2 of the Reference Guide
    to the XML Descriptor (http://www.gbif.org/resource/80639).

    :param path: path to the Darwin Core Archive (either a zip/tgz file or a directory) to open.
    :type path: str
    :param extensions_to_ignore: relative path (within the archive) of extension data files to \
    ignore. This will improve performances and memory consumption with large archives. Missing \
    files are silently ignored.
    :type extensions_to_ignore: list

    :raises: :class:`dwca.exceptions.InvalidArchive`
    :raises: :class:`dwca.exceptions.InvalidSimpleArchive`

    A simple usage example::

        from dwca.read import DwCAReader

        dwca = DwCAReader('my_archive.zip')
        # Iterating on core rows is easy:
        for core_row in dwca:
            # core_row is an instance of dwca.rows.CoreRow
            print(core_row)

        # Scientific metadata (EML) is available as an ElementTree.Element object
        print(dwca.metadata)

        # Close the archive to free resources
        dwca.close()

    The archive can also be opened with the `with` statement. This is recommended, since it ensures
    resources will be properly cleaned after usage:

    ::

        from dwca.read import DwCAReader

        with DwCAReader('my-archive.zip') as dwca:
            pass  # Do what you want

        # When leaving the block, resources are automatically freed.

    """

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __init__(self, path, extensions_to_ignore=None):
        """Open the Darwin Core Archive."""
        if extensions_to_ignore is None:
            extensions_to_ignore = []

        #: The path to the Darwin Core Archive file, as passed to the constructor.
        self.archive_path = path

        if os.path.isdir(self.archive_path):  # Archive is a (directly readable) directory
            self._workin_directory_path = self.archive_path
            self._directory_to_clean = None
        else:  # Archive is zipped/tgzipped, we have to extract it first.
            self._directory_to_clean, self._workin_directory_path = self._extract()

        #: An :class:`descriptors.ArchiveDescriptor` instance giving access to the archive
        #: descriptor/metafile (``meta.xml``)
        try:
            self.descriptor = ArchiveDescriptor(self.open_included_file(METAFILE_NAME).read(),
                                                files_to_ignore=extensions_to_ignore)
        except IOError as e:
            if e.errno == ENOENT:
                self.descriptor = None

        #: A :class:`xml.etree.ElementTree.Element` instance containing the (scientific) metadata
        #: of the archive, or None if the Archive contains no metadata.
        self.metadata = self._parse_metadata_file()
        #: If the archive contains source metadata (typically, GBIF downloads) this dict will
        #: be something like:
        #: {'dataset1_UUID': <dataset1 EML (xml.etree.ElementTree.Element instance)>,
        #: 'dataset2_UUID': <dataset2 EML (xml.etree.ElementTree.Element instance)>, ...}
        #: see :doc:`gbif_results` for more details.
        self.source_metadata = self._load_source_metadata()

        if self.descriptor:
            #  We have an Archive descriptor that we can use to access data files.
            self._corefile = CSVDataFile(self._workin_directory_path, self.descriptor.core)
            self._extensionfiles = [CSVDataFile(work_directory=self._workin_directory_path,
                                                file_descriptor=d)
                                    for d in self.descriptor.extensions]
        else:  # Archive without descriptor, we'll have to find and inspect the data file
            try:
                datafile_name = self._is_valid_simple_archive()
                d = DataFileDescriptor.make_from_file(os.path.join(self._workin_directory_path, datafile_name))

                self._corefile = CSVDataFile(work_directory=self._workin_directory_path,
                                             file_descriptor=d)
                self._extensionfiles = []
            except InvalidSimpleArchive:
                msg = "No metafile was found, but archive includes multiple files/directories."
                raise InvalidSimpleArchive(msg)

    def _load_source_metadata(self):
        r = {}

        dataset_dir = os.path.join(self._workin_directory_path, SOURCE_METADATA_DIRECTORY)
        if os.path.isdir(dataset_dir):
            for f in os.listdir(dataset_dir):
                if os.path.isfile(os.path.join(dataset_dir, f)):
                    key = os.path.splitext(f)[0]
                    r[key] = self._parse_xml_included_file(os.path.join(SOURCE_METADATA_DIRECTORY, f))
        return r

    @property
    def use_extensions(self):
        """Return True if the Archive makes use of extensions."""
        return (self.descriptor is not None) and self.descriptor.extensions

    @property
    # TODO: decide, test and document what we guarantee about ordering
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
            - If the archive is contained in a zip or tgz file, the returned path will point to a\
            temporary file that will be removed when closing the :class:`dwca.read.DwCAReader`\
            instance.
            - File existence is not tested.

        """
        return os.path.abspath(os.path.join(self._workin_directory_path, relative_path))

    def _is_valid_simple_archive(self):
        # If the working dir appear to contains a valid simple darwin core archive
        # (one single data file + possibly some metadata), returns the name of the data file.
        #
        # Otherwise, throws an InvalidSimpleArchive exception.
        path, dirs, files = next(os.walk(self._workin_directory_path))

        if len(files) == 1:  # We found a single file
            return files[0]
        elif len(files) == 2:
            # Two files found: if one of them is EML.xml, the other is considered as the data file
            if DEFAULT_METADATA_FILENAME in files:
                return [f for f in files if f is not DEFAULT_METADATA_FILENAME][0]
            else:
                invalid = True
        else:
            invalid = True

        if invalid:
            raise InvalidSimpleArchive()

    # TODO: Document: Win won't be able to cleanup if some files are not closed
    def open_included_file(self, relative_path, *args, **kwargs):
        """Simple wrapper around Python's open build-in function.

        To be used for reading only.
        """
        return open(self.absolute_temporary_path(relative_path), *args, **kwargs)

    def _parse_metadata_file(self):
        """Load the archive (scientific) Metadata file, parse it with\
        ElementTree and return its content (or None if the Archive contains no metadata).

        :raises: :class:`dwca.exceptions.InvalidArchive` if the archive references an inexisting
        metadata file.
        """
        # If the archive has descriptor, look for the metadata filename there.
        if self.descriptor and self.descriptor.metadata_filename:
            fn = self.descriptor.metadata_filename

            try:
                return self._parse_xml_included_file(fn)
            except IOError as e:
                if e.errno == ENOENT:  # File not found
                    msg = "{} is referenced in the archive descriptor but missing.".format(fn)
                    raise InvalidArchive(msg)

        else:  # Otherwise, the metadata file has to be named 'EML.xml'
            try:
                return self._parse_xml_included_file(DEFAULT_METADATA_FILENAME)
            except IOError as e:
                if e.errno == ENOENT:  # File not found, this is an archive without metadata
                    return None

    def _parse_xml_included_file(self, relative_path):
        """Load, parse and returns (as ElementTree.Element) XML file located at relative_path."""
        return ET.fromstring(self.open_included_file(relative_path).read())

    def _unzip_or_untar(self):
        """Create a temporary dir. and uncompress/unarchive self.archive_path there.

        Returns the path to that temporary directory.

        Raises InvalidArchive if not a zip nor a tgz file.
        """
        tmp_dir = mkdtemp()

        # We first try to unzip (most common archives)
        try:
            # Security note: with Python < 2.7.4, a zip file may be able to write outside of the
            # directory using absolute paths, parent (..) path, ... See note in ZipFile.extract doc
            zipfile.ZipFile(self.archive_path, 'r').extractall(tmp_dir)
        except zipfile.BadZipfile:
            # Doesn't look like a valid zip, let's see if it's a tar archive (possibly compressed)
            try:
                tarfile.open(self.archive_path, 'r:*').extractall(tmp_dir)
            except tarfile.ReadError:
                raise InvalidArchive("The archive cannot be read. Is it a .zip or .tgz file?")

        return tmp_dir

    def _extract(self):
        """Extract the current (Zip of Tar) archive in a temporary directory and return paths.

        Returns (path_to_clean_afterwards, path_to_content)
        """
        extracted_dir = self._unzip_or_untar()
        content = os.listdir(extracted_dir)
        # If the archive contains a single directory, we assume the real content is indeed under
        # this directory.
        #
        # See https://github.com/BelgianBiodiversityPlatform/python-dwca-reader/issues/49
        if len(content) == 1 and os.path.isdir(os.path.join(extracted_dir, content[0])):
            content_dir = os.path.join(extracted_dir, content[0])
        else:
            content_dir = extracted_dir

        return (extracted_dir, content_dir)

    def close(self):
        """Close the Darwin Core Archive and remove temporary/working files.

        .. note::
            - Alternatively, :class:`.DwCAReader` can be instanciated using the `with` statement.\
            (see example above).

        """
        #  Windows can't remove a dir with opened files
        self._corefile.close()
        [f.close() for f in self._extensionfiles]

        if self._directory_to_clean:
            self._cleanup_temporary_dir()

    def _cleanup_temporary_dir(self):
        rmtree(self._directory_to_clean, False)

    def core_contains_term(self, term_url):
        """Return True if the Core file of the archive contains the term_url term."""
        return term_url in self._corefile.file_descriptor.terms

    def __iter__(self):
        self._corefile_pointer = 0
        return self

    def __next__(self):
        return self.next()

    def next(self):  # NOQA
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
    """This class is used to represent the slightly augmented variant of Darwin Core Archive\
    produced by the new GBIF Data Portal when exporting occurrences.

    .. warning:: This class is deprecated. See :doc:`gbif_results` to learn how to achive the same\
    results with :class:`.DwCAReader`.

    """

    @property
    def citations(self):
        """Return the content of the citations.txt file included in the archive."""
        return self.open_included_file('citations.txt').read()

    @property
    def rights(self):
        """Return the content of the rights.txt file included in the archive."""
        return self.open_included_file('rights.txt').read()
