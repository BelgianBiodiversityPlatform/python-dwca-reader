# -*- coding: utf-8 -*-

"""High-level classes to open and read DarwinCore Archive."""

import os
import tarfile
import xml.etree.ElementTree as ET
import zipfile
from errno import ENOENT
from shutil import rmtree
from tempfile import mkdtemp
from typing import List, Optional, Dict, Any, IO
from xml.etree.ElementTree import Element

import dwca.vendor
from dwca.descriptors import ArchiveDescriptor, DataFileDescriptor, shorten_term
from dwca.exceptions import RowNotFound, InvalidArchive, InvalidSimpleArchive, NotADataFile
from dwca.files import CSVDataFile
from dwca.rows import CoreRow


class DwCAReader(object):
    """This class is used to represent a Darwin Core Archive as a whole.

    It gives read access to the contained data, to the scientific metadata, ... It supports
    archives with or without Metafile, such as described on page 2 of the `Reference Guide
    to the XML Descriptor <http://www.gbif.jp/v2/pdf/gbif_dwc-a_metafile_en_v1.pdf>`_.

    :param path: path to the Darwin Core Archive (either a zip/tgz file or a directory) to open.
    :type path: str
    :param extensions_to_ignore: path (relative to the archive root) of extension data files to ignore. This will \
    improve speed and memory usage for large archives. Missing files are silently ignored.
    :type extensions_to_ignore: list

    :raises: :class:`dwca.exceptions.InvalidArchive`
    :raises: :class:`dwca.exceptions.InvalidSimpleArchive`

    Usage::

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

    The archive can also be opened using the `with` statement. This is recommended, since it ensures
    resources will be properly cleaned after usage:

    ::

        from dwca.read import DwCAReader

        with DwCAReader('my-archive.zip') as dwca:
            pass  # Do what you want

        # When leaving the block, resources are automatically freed.

    """

    default_metadata_filename = "EML.xml"
    default_metafile_name = "meta.xml"
    source_metadata_directory = 'dataset'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def __init__(self, path, extensions_to_ignore=None):
        # type: (str, List[str]) -> None
        """Open the Darwin Core Archive."""
        if extensions_to_ignore is None:
            extensions_to_ignore = []

        #: The path to the Darwin Core Archive file, as passed to the constructor.
        self.archive_path = path  # type: str

        if os.path.isdir(self.archive_path):  # Archive is a (directly readable) directory
            self._working_directory_path = self.archive_path
            self._directory_to_clean = None  # type: Optional[str]
        else:  # Archive is zipped/tgzipped, we have to extract it first.
            self._directory_to_clean, self._working_directory_path = self._extract()

        #: An :class:`descriptors.ArchiveDescriptor` instance giving access to the archive
        #: descriptor/metafile (``meta.xml``)
        self.descriptor = None  # type: Optional[ArchiveDescriptor]
        try:
            self.descriptor = ArchiveDescriptor(self.open_included_file(self.default_metafile_name).read(),
                                                files_to_ignore=extensions_to_ignore)
        except IOError as exc:
            if exc.errno == ENOENT:
                pass

        #: A :class:`xml.etree.ElementTree.Element` instance containing the (scientific) metadata
        #: of the archive, or `None` if the archive has no metadata.
        self.metadata = self._parse_metadata_file()  # type: Optional[Element]

        #: If the archive contains source-level metadata (typically, GBIF downloads), this is a dict such as::
        #:
        #:      {'dataset1_UUID': <dataset1 EML> (xml.etree.ElementTree.Element object),
        #:       'dataset2_UUID': <dataset2 EML> (xml.etree.ElementTree.Element object), ...}
        #:
        #: See :doc:`gbif_results` for more details.
        self.source_metadata = self._get_source_metadata()  # type: Dict[str, Element]

        if self.descriptor:  # We have an Archive descriptor that we can use to access data files.
            #: An instance of :class:`dwca.files.CSVDataFile` for the core data file.
            self.core_file = CSVDataFile(self._working_directory_path, self.descriptor.core)  # type: CSVDataFile

            #: A list of :class:`dwca.files.CSVDataFile`, one entry for each extension data file , sorted by order of
            #: appearance in the Metafile (or an empty list if the archive doesn't use extensions).
            self.extension_files = [CSVDataFile(work_directory=self._working_directory_path,
                                                file_descriptor=d)
                                    for d in self.descriptor.extensions]  # type: List[CSVDataFile]
        else:  # Archive without descriptor, we'll have to find and inspect the data file
            try:
                datafile_name = self._is_valid_simple_archive()
                descriptor = DataFileDescriptor.make_from_file(
                    os.path.join(self._working_directory_path, datafile_name))

                self.core_file = CSVDataFile(work_directory=self._working_directory_path,
                                             file_descriptor=descriptor)
                self.extension_files = []
            except InvalidSimpleArchive:
                msg = "No Metafile was found, but the archive contains multiple files/directories."
                raise InvalidSimpleArchive(msg)

    def _get_source_metadata(self):
        # type: () -> Dict[str, Element]
        source_metadata = {}  # type: Dict[str, Element]
        source_metadata_dir = os.path.join(self._working_directory_path, self.source_metadata_directory)

        if os.path.isdir(source_metadata_dir):
            for f in os.listdir(source_metadata_dir):
                if os.path.isfile(os.path.join(source_metadata_dir, f)):
                    dataset_key = os.path.splitext(f)[0]
                    source_metadata[dataset_key] = self._parse_xml_included_file(
                        os.path.join(self.source_metadata_directory, f))

        return source_metadata

    @property
    def core_file_location(self):
        # type: () -> str
        """The (relative) path to the core data file.

        Example: `'occurrence.txt'`
        """
        return self.core_file.file_descriptor.file_location

    def pd_read(self, relative_path, **kwargs):
        """Return a `Pandas <https://pandas.pydata.org>`_ \
        `DataFrame <https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.html>`_ for the data file \
        located at `relative_path`.

        This method wraps pandas.read_csv() and accept the same keyword arguments. The following arguments will be
        ignored (because they are set appropriately for the data file): `delimiter`, `skiprows`, `header` and `names`.

        :param relative_path: path to the data file (relative to the archive root).
        :type relative_path: str

        :raises: `ImportError` if Pandas is not installed.
        :raises: :class:`dwca.exceptions.NotADataFile` if `relative_path` doesn't designate a valid data file\
        in the archive.

        .. warning::

            You'll need to `install Pandas <http://pandas.pydata.org/pandas-docs/stable/install.html>`_ before using
            this method.

        .. note::

            Default values of Darwin Core Archive are supported: A column will be added to the DataFrame if a term has
            a default value in the Metafile (but no corresponding column in the CSV Data File).
        """
        datafile_descriptor = self.get_descriptor_for(relative_path)  # type: DataFileDescriptor

        if not dwca.vendor._has_pandas:
            raise ImportError("Pandas is missing.")

        from pandas import read_csv

        kwargs['delimiter'] = datafile_descriptor.fields_terminated_by
        kwargs['skiprows'] = datafile_descriptor.lines_to_ignore
        kwargs['header'] = None
        kwargs['names'] = datafile_descriptor.short_headers

        df = read_csv(self.absolute_temporary_path(relative_path), **kwargs)

        # Add a column for default values, if present in the file descriptor
        for field in datafile_descriptor.fields:
            field_default_value = field['default']
            if field_default_value is not None:
                df[shorten_term(field['term'])] = field_default_value

        return df

    def orphaned_extension_rows(self):
        # type: () -> Dict[str, Dict[str, List[int]]]
        """Return a dict of the orphaned extension rows.

        Orphaned extension rows are extension rows who reference non-existing core rows. This methods returns a dict
        such as::

         {'description.txt': {u'5': [3, 4], u'6': [5]},
          'vernacularname.txt': {u'7': [4]}}

        Meaning:

            * in `description.txt`, rows at position 3 and 4 reference a core row whose ID is '5', but such a core \
            row doesn't exists. Row at position 5 references an imaginary core row with ID '6'
            * in `vernacularname.txt`, the row at position 4 references an imaginary core row with ID '7'

        """
        indexes = {}

        if len(self.extension_files) > 0:
            temp_ids = {}
            for row in self:
                temp_ids[row.id] = 1
            ids = temp_ids.keys()

            for extension in self.extension_files:
                coreid_index = extension.coreid_index.copy()
                for id in ids:
                    coreid_index.pop(id, None)
                indexes[extension.file_descriptor.file_location] = coreid_index

        return indexes

    @property
    def use_extensions(self):
        # type: () -> bool
        """`True` if the archive makes use of extensions."""
        return self.descriptor and len(self.descriptor.extensions) > 0

    @property
    # TODO: decide, test and document what we guarantee about ordering
    def rows(self):
        # type: () -> List[CoreRow]
        """A list of :class:`rows.CoreRow` objects representing the content of the archive.

        .. warning::

            All rows will be loaded in memory. In case of a large Darwin Core Archive, you may prefer iterating with
            a for loop.
        """
        return list(self)

    def get_corerow_by_id(self, row_id):
        # type: (str) -> CoreRow
        """Return the (core) row whose ID is `row_id`.

        :param row_id: ID of the core row you want
        :type row_id: str

        :returns:  :class:`dwca.rows.CoreRow` -- the matching row.
        :raises: :class:`dwca.exceptions.RowNotFound`

        .. warning::

            It is rarely a good idea to rely on the row ID, because:
            1) Not all Darwin Core Archives specifies row IDs.
            2) Nothing guarantees that the ID will actually be unique within the archive (depends
            of the data publisher). In that case, this method don't guarantee which one will be
            returned. :meth:`.get_corerow_by_position` may be more appropriate in this case.

        """
        for row in self:
            if row.id == str(row_id):
                return row

        raise RowNotFound

    def get_row_by_id(self, row_id):
        # type: (str) -> CoreRow
        """
        .. warning::

            Deprecated: this method has been renamed to :meth:`get_corerow_by_id`.

        """
        import warnings
        warnings.warn("This method has been renamed to get_corerow_by_id().", DeprecationWarning)
        return self.get_corerow_by_id(row_id)

    def get_corerow_by_position(self, position):
        # type: (int) -> CoreRow
        """Return a core row according to its position/index in core file.

        :param position: the position (starting at 0) of the row you want in the core file.
        :type position: int

        :returns:  :class:`dwca.rows.CoreRow` -- the matching row.
        :raises: :class:`dwca.exceptions.RowNotFound`

        .. note::

            - If index is bigger than the length of the archive, None is returned
            - The position is often an appropriate way to unambiguously identify a core row in a DwCA.

        """
        for (i, row) in enumerate(self):
            if i == position:
                return row

        raise RowNotFound

    def get_row_by_index(self, index):
        # type: (int) -> CoreRow
        """
        .. warning::

            Deprecated: this method has been renamed to :meth:`get_corerow_by_position`.

        """
        import warnings
        warnings.warn("This method has been renamed to get_corerow_by_position().", DeprecationWarning)
        return self.get_corerow_by_position(index)

    def absolute_temporary_path(self, relative_path):
        # type: (str) -> str
        """Return the absolute path of a file located within the archive.

        This method allows raw access to the files contained in the archive. It can be useful to open additional, \
        non-standard files embedded in the archive, or to open a standard file with another library.

        :param relative_path: the path (relative to the archive root) of the file.
        :type relative_path: str

        :returns: the absolute path to the file.

        Usage::

            dwca.absolute_temporary_path('occurrence.txt')  # => /tmp/afdfsec7/occurrence.txt

        .. warning::
            If the archive is contained in a zip or tgz file, the returned path will point to a temporary file that \
            will be removed when closing the :class:`dwca.read.DwCAReader` instance.

        .. note::
            File existence is not tested.

        """
        return os.path.abspath(os.path.join(self._working_directory_path, relative_path))

    def get_descriptor_for(self, relative_path):
        # type: (str) -> DataFileDescriptor
        """Return a descriptor for the data file located at relative_path.

        :param relative_path: the path (relative to the archive root) to the data file you want info about.
        :type relative_path: str

        :returns:  :class:`dwca.descriptors.DataFileDescriptor`
        :raises: :class:`dwca.exceptions.NotADataFile` if `relative_path` doesn't reference a valid data file.

        Examples::

            dwca.get_descriptor_for('occurrence.txt')
            dwca.get_descriptor_for('verbatim.txt')
        """
        all_datafiles = [self.core_file] + self.extension_files

        for datafile in all_datafiles:
            if datafile.file_descriptor.file_location == relative_path:
                return datafile.file_descriptor

        raise NotADataFile("{fn} is not a data file".format(fn=relative_path))

    def _is_valid_simple_archive(self):
        # type: () -> str
        # If the working dir appear to contains a valid simple darwin core archive
        # (one single data file + possibly some metadata), returns the name of the data file.
        #
        # Otherwise, throws an InvalidSimpleArchive exception.
        _, _, files = next(os.walk(self._working_directory_path))

        if len(files) == 1:
            return files[0]  # A single file, so that's the one
        elif len(files) == 2:
            # Two files found: if one of them is EML.xml, the other is considered as the data file
            if self.default_metadata_filename in files:
                return [f for f in files if f != self.default_metadata_filename][0]

        raise InvalidSimpleArchive()

    def open_included_file(self, relative_path, *args, **kwargs):
        # type: (str, Any, Any) -> IO
        """Simple wrapper around Python's build-in `open` function.

        To be used only for reading.

        .. warning ::
            Don't forget to close the files after usage. This is especially important on Windows because temporary
            (extracted) files won't be cleanable if not closed.
        """
        return open(self.absolute_temporary_path(relative_path), *args, **kwargs)

    def _parse_metadata_file(self):
        # type: () -> Optional[Element]
        """Load the archive (scientific) Metadata file, parse it with\
        ElementTree and return its content (or `None` if the archive has no metadata).

        :raises: :class:`dwca.exceptions.InvalidArchive` if the archive references an non-existent
        metadata file.
        """
        # If the archive has descriptor, look for the metadata filename there.
        if self.descriptor and self.descriptor.metadata_filename:
            filename = self.descriptor.metadata_filename

            try:
                return self._parse_xml_included_file(filename)
            except IOError as exc:
                if exc.errno == ENOENT:  # File not found
                    msg = "{} is referenced in the archive descriptor but missing.".format(filename)
                    raise InvalidArchive(msg)

        else:  # Otherwise, the metadata file has to be named 'EML.xml'
            try:
                return self._parse_xml_included_file(self.default_metadata_filename)
            except IOError as exc:
                if exc.errno == ENOENT:  # File not found, this is an archive without metadata
                    return None

        assert False  # For MyPy, see: https://github.com/python/mypy/issues/4223#issuecomment-342865133

    def _parse_xml_included_file(self, relative_path):
        # type: (str) -> Element
        """Load, parse and returns (as ElementTree.Element) XML file located at relative_path."""
        return ET.parse(self.absolute_temporary_path(relative_path)).getroot()

    def _unzip_or_untar(self):
        # type: () -> str
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

        return extracted_dir, content_dir

    def close(self):
        """Close the Darwin Core Archive and remove temporary/working files.

        .. note::
            - Alternatively, :class:`.DwCAReader` can be instanciated using the `with` statement.\
            (see example above).

        """
        #  Windows can't remove a dir with opened files
        self.core_file.close()
        for extension_file in self.extension_files:
            extension_file.close()

        if self._directory_to_clean:
            rmtree(self._directory_to_clean, False)

    def core_contains_term(self, term_url):
        # type: (str) -> bool
        """Return `True` if the Core file of the archive contains the `term_url` term."""
        return term_url in self.core_file.file_descriptor.terms

    def __iter__(self):
        self._corefile_pointer = 0
        return self

    def __next__(self):
        return self.next()

    def next(self):  # NOQA
        try:
            row = self.core_file.get_row_by_position(self._corefile_pointer)

            # Set up linked data so the CoreRow will know about them
            row.link_extension_files(self.extension_files)
            row.link_source_metadata(self.source_metadata)

            self._corefile_pointer = self._corefile_pointer + 1
            return row
        except IndexError:
            raise StopIteration


class GBIFResultsReader(DwCAReader):
    """This class is used to represent the slightly augmented variant of Darwin Core Archive produced by the GBIF Data
    Portal when exporting occurrences.

    .. warning:: This class is deprecated. See :doc:`gbif_results` to learn how to achieve the same results with \
    :class:`.DwCAReader`.

    """

    @property
    def citations(self):
        """The content of the `citations.txt` file included in the archive."""
        return self.open_included_file('citations.txt').read()

    @property
    def rights(self):
        """The content of the `rights.txt` file included in the archive."""
        return self.open_included_file('rights.txt').read()
