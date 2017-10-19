# -*- coding: utf-8 -*-

import unittest
import xml.etree.ElementTree as ET
import sys

from dwca.read import DwCAReader
from dwca.files import CSVDataFile
from dwca.descriptors import DataFileDescriptor

from .helpers import MULTIEXTENSIONS_ARCHIVE_PATH, DIRECTORY_ARCHIVE_PATH


class TestCSVDataFile(unittest.TestCase):
    def test_coreid_index(self):
        with DwCAReader(MULTIEXTENSIONS_ARCHIVE_PATH) as dwca:
            extension_files = dwca._extensionfiles

            description_txt = extension_files[0]
            vernacular_txt = extension_files[1]

            expected_vernacular = {
                '1': [0, 1, 2],
                '2': [3]
            }
            self.assertEqual(vernacular_txt.coreid_index, expected_vernacular)

            expected_description = {
                '1': [0, 1],
                '4': [2]
            }
            self.assertEqual(description_txt.coreid_index, expected_description)

            with self.assertRaises(AttributeError):
                dwca._corefile.coreid_index

    def test_file_descriptor_attribute(self):
        """The instance of DataFileDescriptor passed to the constructor is available in .file_descriptor"""

        metaxml_section = r"""
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/locality"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
        </core>
        """

        descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))
        data_file = CSVDataFile(DIRECTORY_ARCHIVE_PATH, descriptor)

        self.assertEqual(data_file.file_descriptor, descriptor)

    def test_lines_to_ignore_attribute(self):
        """.lines_to_ignore works as documented"""

        metaxml_section = r"""
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/locality"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
        </core>
        """

        descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))
        data_file = CSVDataFile(DIRECTORY_ARCHIVE_PATH, descriptor)

        self.assertEqual(data_file.lines_to_ignore, 1)

        metaxml_section = r"""
                <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="3" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
                    <files>
                        <location>occurrence.txt</location>
                    </files>
                    <id index="0" />
                    <field index="1" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
                    <field index="2" term="http://rs.tdwg.org/dwc/terms/locality"/>
                    <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
                    <field index="4" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
                </core>
                """

        descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))
        data_file = CSVDataFile(DIRECTORY_ARCHIVE_PATH, descriptor)

        self.assertEqual(data_file.lines_to_ignore, 3)

    def test_close(self):
        metaxml_section = r"""
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files><location>occurrence.txt</location></files>
            <id index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/locality"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
        </core>
        """

        descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))
        data_file = CSVDataFile(DIRECTORY_ARCHIVE_PATH, descriptor)

        data_file.close()

        with self.assertRaises(ValueError):
            # It's not possible anymore to access the data because file has been closed.
            data_file.get_row_by_position(1)

    def test_iterate(self):
        metaxml_section = r"""
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files><location>occurrence.txt</location></files>
                <id index="0" />
                <field index="1" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
                <field index="2" term="http://rs.tdwg.org/dwc/terms/locality"/>
                <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
                <field index="4" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
            </core>
         """

        descriptor = DataFileDescriptor.make_from_metafile_section(ET.fromstring(metaxml_section))
        data_file = CSVDataFile(DIRECTORY_ARCHIVE_PATH, descriptor)

        for row in data_file:
            if sys.version_info[0] == 2:
                self.assertIsInstance(row, unicode)
            elif sys.version_info[0] == 3:
                self.assertIsInstance(row, str)



