import unittest
import xml.etree.ElementTree as ET
from array import array

from dwca.descriptors import DataFileDescriptor
from dwca.files import CSVDataFile
from dwca.read import DwCAReader
from .helpers import sample_data_path
import pytest


class TestCSVDataFile(unittest.TestCase):
    def test_get_line_at_position_raises_indexerror(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            with pytest.raises(IndexError):
                dwca.core_file.get_row_by_position(10000)

    def test_string_representation(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            extension_files = dwca.extension_files

            assert "taxon.txt" == str(dwca.core_file)
            assert "description.txt" == str(extension_files[0])
            assert "vernacularname.txt" == str(extension_files[1])

        # Also check with a simple archive
        with DwCAReader(sample_data_path("dwca-simple-csv.zip")) as dwca:
            assert "0008333-160118175350007.csv" == str(dwca.core_file)

    def test_coreid_index(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            extension_files = dwca.extension_files

            core_txt = dwca.core_file
            description_txt = extension_files[0]
            vernacular_txt = extension_files[1]

            expected_core = {'1': array('L', [0]), '2': array('L', [1]), '3': array('L', [2]), '4': array('L', [3])}
            assert core_txt.coreid_index == expected_core

            expected_vernacular = {"1": array('L', [0, 1, 2]), "2": array('L', [3])}
            assert vernacular_txt.coreid_index == expected_vernacular

            expected_description = {"1": array('L', [0, 1]), "4": array('L', [2])}
            assert description_txt.coreid_index == expected_description

            with pytest.raises(AttributeError):
                dwca.corefile.coreid_index

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

        descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )
        data_file = CSVDataFile(sample_data_path("dwca-simple-dir"), descriptor)

        assert data_file.file_descriptor == descriptor

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

        descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )
        data_file = CSVDataFile(sample_data_path("dwca-simple-dir"), descriptor)

        assert data_file.lines_to_ignore == 1

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

        descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )
        data_file = CSVDataFile(sample_data_path("dwca-simple-dir"), descriptor)

        assert data_file.lines_to_ignore == 3

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

        descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )
        data_file = CSVDataFile(sample_data_path("dwca-simple-dir"), descriptor)

        data_file.close()

        with pytest.raises(ValueError):
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

        descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )
        data_file = CSVDataFile(sample_data_path("dwca-simple-dir"), descriptor)

        for row in data_file:
            assert isinstance(row, str)
