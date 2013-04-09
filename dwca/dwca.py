# -*- coding: utf-8 -*-

from tempfile import mkdtemp
from zipfile import ZipFile
from shutil import rmtree
from BeautifulSoup import BeautifulStoneSoup
import codecs
import os


class DwCALine:
    def __str__(self):
        txt = ""
        try:
            txt += 'Line #' + self.id + "\n"
        except AttributeError:
            pass

        try:
            txt += 'Core id: ' + self.core_id + "\n"
        except AttributeError:
            pass

        txt += "\nElements:\n"
        for k, v in self.linedata.items():
            txt += "\t" + k + ' : ' + v + "\n"

        return txt

    def from_core(self):
        """Returns Boolean value"""
        return self._line_type_core

    def from_extension(self):
        """Returns Boolean value"""
        return not self.from_core()


    def get(self, attr_name):
        return self.linedata[attr_name]

    def __init__(self, line, is_core_type, metadata, unzipped_folder=None):
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
        self._line_type_core = is_core_type

        if self.from_core():
            meta = metadata.core
        else:
            meta = metadata

        separator = meta['fieldsterminatedby'].decode("string-escape")

        # fields is list of the line's content
        fields = line.split(separator)

        # TODO: Consistency chek ?? fields length should be :
        # num of fields described in core_meta + 2 (id and \n)

        # If core, we have an id; if extension a coreid
        # TODO: ensure in the norm this is always true
        if self.from_core():
            self.id = fields[int(meta.id['index'])]
        else:
            self.core_id = fields[int(meta.coreid['index'])]

        self.linedata = {}

        for f in meta.findAll('field'):
            # if field by default, we can find its value directly in <field>
            # attribute
            if f.has_key('default'):
                self.linedata[f['term']] = f['default']
            else:
                # else, we have to look in core file
                self.linedata[f['term']] = fields[int(f['index'])]

        # Core line: we also need to store related (extension) lines in the
        # extensions attribute

        self.extensions = []

        if self.from_core():
            for ext_meta in metadata.findAll('extension'):
                csv = DwCACSVIterator(ext_meta, unzipped_folder)
                for l in csv.lines():
                    tmp = DwCALine(l, False, ext_meta)
                    if tmp.core_id == self.id:
                        self.extensions.append(tmp)


class DwCAReader:
    # Define __enter__ and __exit__ to be used with the 'with' statement
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __init__(self, path):
        """Opens the file, reads all metadata and store it in self.meta
        (BeautifulStoneSoup obj.) Also already open the core file so we've
        a file descriptor for further access."""
        self.archive_path = path
        self._unzipped_folder = self._unzip()

        self._metaxml = self._parse_metaxml_file()

        # Load the (scientific) metadata file and store its representation
        # in metadata attribute for future use.
        self.metadata = self._parse_metadata_file()
        self.core_type = self._get_core_type()

        self._datafile = DwCACSVIterator(self._metaxml.core,
                                         self._unzipped_folder)

    def _create_temporary_folder(self):
        return mkdtemp()[1]

    def _parse_metadata_file(self):
        """Loads the archive (scientific) Metadata file, parse it with
        BeautifulSoup and return its content"""

        # This method should be called only after ._metaxml attribute is set
        # because the name/path to metadat file is stored in the "metadata"
        # attribute of the "archive" tag
        metadata_file = self._get_metadata_filename()
        return self._parse_xml_included_file(metadata_file)

    def _parse_metaxml_file(self):
        """Loads the meta.xml, parse it with BeautifulSoup and return its
        content"""
        return self._parse_xml_included_file('meta.xml')

    def _parse_xml_included_file(self, relative_path):
        """Loads, parse with BeautifulSoup and returns XML file located
        at relative_path"""
        xml_path = os.path.join(self._unzipped_folder, relative_path)
        xml_string = open(xml_path).read()
        return BeautifulStoneSoup(xml_string)

    def _unzip(self):
        unzipped_folder = self._create_temporary_folder()
        #TODO: check content of file!!!! It may, for example contains
        #absolute path (see zipfile doc)
        ZipFile(self.archive_path, 'r').extractall(unzipped_folder)
        return unzipped_folder

    def close(self):
        self._cleanup_temporary_folder()

    def _cleanup_temporary_folder(self):
        rmtree(self._unzipped_folder, False)

    def _get_core_type(self):
        return self._metaxml.core['rowtype']

    def core_contains_term(self, term_url):
        """Takes a tdwg URL as a parameter and check if field exists for
        this concept in the core file"""
        fields = self._metaxml.core.findAll('field')
        for i in fields:
            if i['term'] == term_url:
                return True
        return False  # If we end up there, the term was not found.

    def _get_metadata_filename(self):
        return self._metaxml.archive['metadata']

    def each_line(self):
        for line in self._datafile.lines():
            yield DwCALine(line, True, self._metaxml, self._unzipped_folder)


# Simple, internal use class used to iterate on a DwcA-enclosed CSV file
# It initializes itself with the <core> or <extension> section of meta.xml
class DwCACSVIterator:
    def __init__(self, metadata_section, unzipped_folder):
        # metadata_section: <core> or <extension> section of metaxml for
        # the file we want to iterate on
        self._metadata_section = metadata_section
        self._unzipped_folder = unzipped_folder

        self._reset_line_iterator()

        self._core_fhandler = codecs.open(self._get_filepath(),
                                          mode='r',
                                          encoding=self._get_encoding(),
                                          errors='replace')

    def lines(self):
        for line in self._core_fhandler:
            self._line_pointer += 1

            if (self._line_pointer <= self._get_lines_to_ignore()):
                continue
            else:
                yield line

    def _get_filepath(self):
        # TODO: Replace by os.path.join
        return (self._unzipped_folder + '/' +
                self._metadata_section.files.location.string)

    def _get_encoding(self):
        return self._metadata_section['encoding']

    def _reset_line_iterator(self):
        self._line_pointer = 0

    def _get_lines_to_ignore(self):
        try:
            return int(self._metadata_section['ignoreheaderlines'])
        except KeyError:
            return 0
