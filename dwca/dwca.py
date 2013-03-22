# -*- coding: utf-8 -*-

from tempfile import mkdtemp
from zipfile import ZipFile
from shutil import rmtree
from BeautifulSoup import BeautifulStoneSoup
import codecs
import os
import xml.etree.ElementTree as xml


class DwCALine:
    def __str__(self):
        txt = 'Line #' + self.id + "\n"
        txt += "\nCore elements:\n"
        for k, v in self.coredata.items():
            txt += "\t" + k + ' : ' + v + "\n"

        return txt

    def get(self, attr_name):
        return self.coredata[attr_name]

    def to_xml(self):
        e = xml.Element('line')
        e.attrib['id'] = self.id
        c = xml.SubElement(e, 'coreelements')
        for k, v in self.coredata.items():
            ce = xml.SubElement(c, 'elem')
            ce.attrib['url'] = k
            ce.attrib['shortname'] = k.split('/')[-1]
            ce.attrib['value'] = v

        return e

    def __init__(self, core_line, core_meta):
        # Core line is the data as returned from for...in file
        # core_meta is a beautifulsoup object containing the <core> node
        # (and content) from the metaxml
        separator = core_meta['fieldsterminatedby'].decode("string-escape")

        # fields is list of the line's content
        fields = core_line.split(separator)

        # TODO: Consistency chek ?? fields length should be :
        # num of fields described in core_meta + 2 (id and \n)

        self.id = fields[int(core_meta.id['index'])]

        self.coredata = {}
        self.extensionsdata = {}  # For future use

        for f in core_meta.findAll('field'):
            # if field by default, we can find its value directly in <field>
            # attribute
            if f.has_key('default'):
                self.coredata[f['term']] = f['default']
            else:
                # else, we have to look in core file
                self.coredata[f['term']] = fields[int(f['index'])]


class DwCAReader:
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

        self._core_fhandler = codecs.open(self._get_core_filename(),
                                          mode='r',
                                          encoding=self._get_core_encoding(),
                                          errors='replace')

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

    def cleanup_temporary_folder(self):
        #TODO: directory empty but still seems to be present
        #(and undeletable if I add rmdir on the next line, investigate.
        rmtree(self._unzipped_folder, False)

    def get_core_type(self):
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

    def _get_core_filename(self):
        return (self._unzipped_folder + '/' +
                self._metaxml.core.files.location.string)

    def _get_core_encoding(self):
        return self._metaxml.core['encoding']

    def reset_line_iterator(self):
        self._core_fhandler.seek(0)

    def each_line(self):
        for line in self._core_fhandler:
            yield DwCALine(line, self._metaxml.core)
