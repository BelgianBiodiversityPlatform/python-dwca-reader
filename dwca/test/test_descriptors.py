import os
import unittest
import xml.etree.ElementTree as ET
import zipfile

import pytest

from dwca.darwincore.utils import qualname as qn
from dwca.descriptors import DataFileDescriptor, ArchiveDescriptor
from dwca.exceptions import InvalidArchive
from dwca.read import DwCAReader
from .helpers import sample_data_path


class TestDataFileDescriptor(unittest.TestCase):
    """Unit tests for DataFileDescriptor class."""

    def test_init_from_file(self):
        """Ensure a DataFileDescriptor can be constructed directly from a CSV file.

        This is necessary for archives sans metafile.
        """
        with zipfile.ZipFile(sample_data_path("dwca-simple-csv.zip"), "r") as archive:
            datafile_path = archive.extract("0008333-160118175350007.csv")

            d = DataFileDescriptor.make_from_file(datafile_path)
            # Check basic metadata with the file
            assert d.raw_element is None
            assert d.represents_corefile
            assert not d.represents_extension
            assert d.type is None
            assert d.file_location == "0008333-160118175350007.csv"
            assert d.file_encoding == "utf-8"
            assert d.lines_terminated_by == "\n"
            assert d.fields_terminated_by == "\t"
            assert d.fields_enclosed_by == '"'

            # Some checks on fields...

            # A few fields are checked
            expected_fields = (
                {"default": None, "index": 0, "term": "gbifid"},
                {"default": None, "index": 3, "term": "kingdom"},
            )

            for ef in expected_fields:
                assert ef in d.fields

            # In total, there are 42 fields in this data file
            assert len(d.fields) == 42

            # No fields should have a default value (there's no metafile to set it!)
            for f in d.fields:
                assert f["default"] is None

            # Ensure .terms is also set:
            assert len(d.terms) == 42

            # Cleanup extracted file
            os.remove(datafile_path)

    def test_lines_to_ignore(self):
        # With explicit "0"
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )

        assert core_descriptor.lines_to_ignore == 0

        # With explicit 1
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )

        assert core_descriptor.lines_to_ignore == 1

        # Implicit 0 (when nothing stated)
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )

        assert core_descriptor.lines_to_ignore == 0

    def test_file_details(self):
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
            <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/locality"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )

        assert core_descriptor.file_location == "occurrence.txt"
        assert core_descriptor.file_encoding == "utf-8"
        # TODO: Also test .lines_terminated_by and .fields_terminated_by
        # (this seems a bit tricky, and it's already tested indirectly - many things would fail
        # without them)

    def test_fields(self):
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
            <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/locality"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )

        # .fields is supposed to return a list of dicts like those
        expected_fields = (
            {
                "term": "http://rs.tdwg.org/dwc/terms/country",
                "index": None,
                "default": "Belgium",
            },
            {
                "term": "http://rs.tdwg.org/dwc/terms/scientificName",
                "index": 1,
                "default": None,
            },
        )

        for ef in expected_fields:
            assert ef in core_descriptor.fields

        assert len(core_descriptor.fields) == 5

    def test_headers_simplecases(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            descriptor = dwca.descriptor

            # With core file...
            expected_headers_core = [
                "id",
                "http://rs.tdwg.org/dwc/terms/order",
                "http://rs.tdwg.org/dwc/terms/class",
                "http://rs.tdwg.org/dwc/terms/kingdom",
                "http://rs.tdwg.org/dwc/terms/phylum",
                "http://rs.tdwg.org/dwc/terms/genus",
                "http://rs.tdwg.org/dwc/terms/family",
            ]

            assert descriptor.core.headers == expected_headers_core

            # And with a first extension...
            expected_headers_description_ext = [
                "coreid",
                "http://purl.org/dc/terms/type",
                "http://purl.org/dc/terms/language",
                "http://purl.org/dc/terms/description",
            ]

            desc_ext_descriptor = next(
                d
                for d in dwca.descriptor.extensions
                if d.type == "http://rs.gbif.org/terms/1.0/Description"
            )

            assert desc_ext_descriptor.headers == expected_headers_description_ext

            # And another one
            expected_headers_vernacular_ext = [
                "coreid",
                "http://rs.tdwg.org/dwc/terms/countryCode",
                "http://purl.org/dc/terms/language",
                "http://rs.tdwg.org/dwc/terms/vernacularName",
            ]

            vern_ext_descriptor = next(
                d
                for d in dwca.descriptor.extensions
                if d.type == "http://rs.gbif.org/terms/1.0/VernacularName"
            )

            assert vern_ext_descriptor.headers == expected_headers_vernacular_ext

    def test_headers_defaultvalue(self):
        """Ensure headers work properly when confronted to default values (w/o column in file)"""
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
            <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/locality"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )

        expected_headers_core = [
            "id",
            "http://rs.tdwg.org/dwc/terms/scientificName",
            "http://rs.tdwg.org/dwc/terms/basisOfRecord",
            "http://rs.tdwg.org/dwc/terms/family",
            "http://rs.tdwg.org/dwc/terms/locality",
        ]

        assert core_descriptor.headers == expected_headers_core

    def test_short_headers(self):
        metaxml_section = """
                <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
                ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
                    <files>
                        <location>occurrence.txt</location>
                    </files>
                    <id index="0" />
                    <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
                    <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
                    <field index="2" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
                    <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
                    <field index="4" term="http://rs.tdwg.org/dwc/terms/locality"/>
                </core>
                """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )

        expected_short_headers_core = [
            "id",
            "scientificName",
            "basisOfRecord",
            "family",
            "locality",
        ]

        assert core_descriptor.short_headers == expected_short_headers_core

    def test_headers_unordered(self):
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Taxon">
            <files>
                <location>taxon.txt</location>
            </files>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/phylum"/>
            <id index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/order"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/class"/>
            <field index="6" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/kingdom"/>
            <field index="5" term="http://rs.tdwg.org/dwc/terms/genus"/>
        </core>
        """
        core_descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )

        expected_headers_core = [
            "id",
            "http://rs.tdwg.org/dwc/terms/order",
            "http://rs.tdwg.org/dwc/terms/class",
            "http://rs.tdwg.org/dwc/terms/kingdom",
            "http://rs.tdwg.org/dwc/terms/phylum",
            "http://rs.tdwg.org/dwc/terms/genus",
            "http://rs.tdwg.org/dwc/terms/family",
        ]

        assert core_descriptor.headers == expected_headers_core

    def test_exposes_raw_element_tag(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            assert isinstance(dwca.descriptor.core.raw_element, ET.Element)

    def test_content_raw_element_tag(self):
        """Test the content of raw_element seems decent."""
        ext_section = """
        <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n"
        fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/Description">
            <files><location>description.txt</location></files>
            <coreid index="0" />
            <field index="1" term="http://purl.org/dc/terms/type"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://purl.org/dc/terms/description"/>
        </extension>
        """

        ext_descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(ext_section)
        )

        assert ext_descriptor.raw_element.tag == "extension"
        assert ext_descriptor.raw_element.get("encoding") == "utf-8"
        assert len(ext_descriptor.raw_element.findall("field")) == 3

    def test_tell_if_represents_core(self):
        # 1. Test with core
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            core_descriptor = dwca.descriptor.core
            assert core_descriptor.represents_corefile
            assert not core_descriptor.represents_extension

        ext_section = """
        <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n"
        fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/Description">
            <files><location>description.txt</location></files>
            <coreid index="0" />
            <field index="1" term="http://purl.org/dc/terms/type"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://purl.org/dc/terms/description"/>
        </extension>
        """

        # 2. And with extension
        ext_descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(ext_section)
        )
        assert not ext_descriptor.represents_corefile
        assert ext_descriptor.represents_extension

    def test_exposes_coreid_index_of_extensions(self):
        ext_section = """
        <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/Description">
            <files><location>description.txt</location></files>
            <coreid index="0" />
            <field index="1" term="http://purl.org/dc/terms/type"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://purl.org/dc/terms/description"/>
        </extension>
        """

        ext_descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(ext_section)
        )

        assert ext_descriptor.coreid_index == 0

        # ... but it doesn't have .id_index (only for core!)
        assert ext_descriptor.id_index is None

    def test_exposes_id_index_of_core(self):
        metaxml_section = """
        <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
        ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files>
                <location>occurrence.txt</location>
            </files>
            <id index="0" />
            <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
            <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/basisOfRecord"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/family"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/locality"/>
        </core>
        """

        core_descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(metaxml_section)
        )

        assert core_descriptor.id_index == 0

        # ... but it doesn't have .coreid_index (only for extensions!)
        assert core_descriptor.coreid_index is None

    def test_exposes_core_type(self):
        """Test that it exposes the Archive Core Type as type"""

        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            coredescriptor = dwca.descriptor.core
            # dwca-simple-test-archive.zip should be of Occurrence type
            assert coredescriptor.type == "http://rs.tdwg.org/dwc/terms/Occurrence"
            # Check that shortcuts also work
            assert coredescriptor.type == qn("Occurrence")

    def test_exposes_core_terms(self):
        with DwCAReader(sample_data_path("dwca-star-test-archive.zip")) as star_dwca:
            # The Core file contains the following rows
            # <field index="1" term="http://rs.tdwg.org/dwc/terms/family"/>
            # <field index="2" term="http://rs.tdwg.org/dwc/terms/phylum"/>
            # <field index="3" term="http://rs.tdwg.org/dwc/terms/order"/>
            # <field index="4" term="http://rs.tdwg.org/dwc/terms/genus"/>
            # <field index="5" term="http://rs.tdwg.org/dwc/terms/kingdom"/>
            # <field index="6" term="http://rs.tdwg.org/dwc/terms/class"/>

            # It also contains an id column (should not appear here)
            # There's an extension with 3 fields, should not appear here.

            # Assert correct size
            descriptor = star_dwca.descriptor
            assert 6 == len(descriptor.core.terms)

            # Assert correct content (should be a set, so unordered)
            fields = set(
                [
                    "http://rs.tdwg.org/dwc/terms/kingdom",
                    "http://rs.tdwg.org/dwc/terms/order",
                    "http://rs.tdwg.org/dwc/terms/class",
                    "http://rs.tdwg.org/dwc/terms/genus",
                    "http://rs.tdwg.org/dwc/terms/family",
                    "http://rs.tdwg.org/dwc/terms/phylum",
                ]
            )

            assert fields == descriptor.core.terms


class TestDataFileDescriptorEquality(unittest.TestCase):
    """Unit tests for DataFileDescriptor equality and hashing.

    Descriptors compare by value (the data file layout they describe) rather than by object
    identity, so descriptors built twice from the same archive - by two DwCAReader instances,
    for example - compare equal.
    """

    CORE_SECTION = """
    <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy=""
    ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
        <files>
            <location>occurrence.txt</location>
        </files>
        <id index="0" />
        <field index="1" term="http://rs.tdwg.org/dwc/terms/scientificName"/>
        <field default="Belgium" term="http://rs.tdwg.org/dwc/terms/country"/>
    </core>
    """

    def _make(self, section=None):
        return DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(section if section is not None else self.CORE_SECTION)
        )

    def test_descriptors_from_identical_sections_are_equal(self):
        one = self._make()
        two = self._make()

        assert one is not two
        # raw_element is an ET.Element, which compares by identity: these two are distinct
        # objects, so equality can only hold if raw_element is left out of the comparison.
        assert one.raw_element is not two.raw_element
        assert one == two
        assert not (one != two)
        assert hash(one) == hash(two)
        assert len({one, two}) == 1

    def test_descriptors_of_the_same_archive_read_twice_are_equal(self):
        path = sample_data_path("dwca-2extensions.zip")

        with DwCAReader(path) as one, DwCAReader(path) as two:
            assert one.descriptor.core == two.descriptor.core

            for ext_one, ext_two in zip(
                one.descriptor.extensions, two.descriptor.extensions
            ):
                assert ext_one == ext_two

    def test_core_and_extension_descriptors_differ(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            core = dwca.descriptor.core

            for extension in dwca.descriptor.extensions:
                assert core != extension

    def test_descriptors_differing_by_ignored_header_lines_differ(self):
        one = self._make()
        two = self._make(
            self.CORE_SECTION.replace('ignoreHeaderLines="0"', 'ignoreHeaderLines="1"')
        )

        # Everything but the number of header lines to skip is identical here. That number
        # lives in raw_element, which is excluded from the comparison, so it's only taken into
        # account through the lines_to_ignore property.
        assert one.lines_to_ignore != two.lines_to_ignore
        assert one != two

    def test_descriptors_differing_by_fields_differ(self):
        one = self._make()
        two = self._make(
            self.CORE_SECTION.replace(
                'term="http://rs.tdwg.org/dwc/terms/scientificName"',
                'term="http://rs.tdwg.org/dwc/terms/locality"',
            )
        )

        assert one != two

    def test_descriptors_differing_by_file_location_differ(self):
        one = self._make()
        two = self._make(
            self.CORE_SECTION.replace("occurrence.txt", "other_occurrences.txt")
        )

        assert one != two

    def test_comparison_with_other_types_returns_false(self):
        descriptor = self._make()

        assert descriptor != "not a descriptor"
        assert descriptor != 42
        assert descriptor != None  # noqa: E711 - we're testing __eq__, not identity
        assert not (descriptor == "not a descriptor")


class TestArchiveDescriptor(unittest.TestCase):
    """Unit tests for ArchiveDescriptor class."""

    def test_exposes_coredescriptor(self):
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as basic_dwca:
            assert isinstance(basic_dwca.descriptor.core, DataFileDescriptor)

    def test_exposes_extensions_2ext(self):
        all_metaxml = """
        <archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="eml.xml">
          <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Taxon">
            <files>
              <location>taxon.txt</location>
            </files>
            <id index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/order"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/class"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/kingdom"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/phylum"/>
            <field index="5" term="http://rs.tdwg.org/dwc/terms/genus"/>
            <field index="6" term="http://rs.tdwg.org/dwc/terms/family"/>
          </core>
          <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/Description">
            <files>
              <location>description.txt</location>
            </files>
            <coreid index="0" />
            <field index="1" term="http://purl.org/dc/terms/type"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://purl.org/dc/terms/description"/>
          </extension>
          <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/VernacularName">
            <files>
              <location>vernacularname.txt</location>
            </files>
            <coreid index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/countryCode"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/vernacularName"/>
          </extension>
        </archive>
        """

        d = ArchiveDescriptor(all_metaxml)
        expected_extensions_files = ("description.txt", "vernacularname.txt")
        for ext in d.extensions:
            assert ext.file_location in expected_extensions_files

        assert len(d.extensions) == 2

    # Test the files_to_ignore optional argument work as expected
    def test_exposes_extensions_2ext_ignore(self):
        all_metaxml = """
        <archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="eml.xml">
          <core encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.tdwg.org/dwc/terms/Taxon">
            <files>
              <location>taxon.txt</location>
            </files>
            <id index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/order"/>
            <field index="2" term="http://rs.tdwg.org/dwc/terms/class"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/kingdom"/>
            <field index="4" term="http://rs.tdwg.org/dwc/terms/phylum"/>
            <field index="5" term="http://rs.tdwg.org/dwc/terms/genus"/>
            <field index="6" term="http://rs.tdwg.org/dwc/terms/family"/>
          </core>
          <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/Description">
            <files>
              <location>description.txt</location>
            </files>
            <coreid index="0" />
            <field index="1" term="http://purl.org/dc/terms/type"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://purl.org/dc/terms/description"/>
          </extension>
          <extension encoding="utf-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" ignoreHeaderLines="1" rowType="http://rs.gbif.org/terms/1.0/VernacularName">
            <files>
              <location>vernacularname.txt</location>
            </files>
            <coreid index="0" />
            <field index="1" term="http://rs.tdwg.org/dwc/terms/countryCode"/>
            <field index="2" term="http://purl.org/dc/terms/language"/>
            <field index="3" term="http://rs.tdwg.org/dwc/terms/vernacularName"/>
          </extension>
        </archive>
        """

        d = ArchiveDescriptor(all_metaxml, files_to_ignore="description.txt")

        assert len(d.extensions) == 1
        assert d.extensions[0].file_location == "vernacularname.txt"

    def test_exposes_extensions_none(self):
        all_metaxml = """
        <archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="eml.xml">
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
        </archive>
        """
        d = ArchiveDescriptor(all_metaxml)
        assert len(d.extensions) == 0

    def test_exposes_extensions_type(self):
        vn = "http://rs.gbif.org/terms/1.0/VernacularName"
        td = "http://rs.gbif.org/terms/1.0/Description"

        # This archive has no extension, we should get an empty list
        with DwCAReader(sample_data_path("dwca-simple-test-archive.zip")) as dwca:
            descriptor = dwca.descriptor
            assert [] == descriptor.extensions_type

        # This archive only contains the VernacularName extension
        with DwCAReader(sample_data_path("dwca-star-test-archive.zip")) as dwca:
            descriptor = dwca.descriptor
            assert descriptor.extensions_type[0] == vn
            assert 1 == len(descriptor.extensions_type)

        # TODO: test with more complex archive
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            descriptor = dwca.descriptor
            # 2 extensions are in use : vernacular names and taxon descriptions
            assert 2 == len(descriptor.extensions_type)
            # USe of frozenset to lose ordering
            supposed_extensions = frozenset([vn, td])
            assert supposed_extensions == frozenset(descriptor.extensions_type)

    def test_exposes_metadata_filename(self):
        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            descriptor = dwca.descriptor

            assert descriptor.metadata_filename == "eml.xml"


class TestHeadersIndexZero(unittest.TestCase):
    def test_column_at_index_zero_is_not_dropped(self):
        """A metafile-less archive has no id_index, so column 0 comes only from fields."""
        with DwCAReader(sample_data_path("dwca-simple-csv.zip")) as dwca:
            descriptor = dwca.core_file.file_descriptor

            assert len(descriptor.fields) == len(descriptor.headers)
            assert "gbifid" == descriptor.headers[0]


class TestFieldPlan(unittest.TestCase):
    def _descriptor(self, fields_xml, tag="core", id_tag='<id index="0" />'):
        section = """
        <{tag} encoding="utf-8" fieldsTerminatedBy="\\t" linesTerminatedBy="\\n" \
fieldsEnclosedBy="" ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files><location>occurrence.txt</location></files>
            {id_tag}
            {fields}
        </{tag}>
        """.format(
            tag=tag, id_tag=id_tag, fields=fields_xml
        )
        return DataFileDescriptor.make_from_metafile_section(ET.fromstring(section))

    def test_contiguous_columns(self):
        descriptor = self._descriptor(
            '<field index="0" term="http://x/a"/>'
            '<field index="1" term="http://x/b"/>'
        )

        assert {"http://x/a": "1", "http://x/b": "Borneo"} == (
            descriptor.field_plan.build_data(["1", "Borneo"])
        )

    def test_columns_out_of_order_and_with_gaps(self):
        descriptor = self._descriptor(
            '<field index="2" term="http://x/a"/>'
            '<field index="0" term="http://x/b"/>'
        )

        assert {"http://x/a": "third", "http://x/b": "first"} == (
            descriptor.field_plan.build_data(["first", "second", "third"])
        )

    def test_single_column(self):
        descriptor = self._descriptor('<field index="1" term="http://x/a"/>')

        assert {"http://x/a": "Borneo"} == descriptor.field_plan.build_data(
            ["1", "Borneo"]
        )

    def test_default_only_field_has_no_column(self):
        descriptor = self._descriptor(
            '<field index="0" term="http://x/a"/>'
            '<field term="http://x/country" default="Belgium"/>'
        )

        assert {"http://x/a": "1", "http://x/country": "Belgium"} == (
            descriptor.field_plan.build_data(["1"])
        )

    def test_default_fills_an_empty_cell(self):
        """A field can have both a column and a default (issue #80)."""
        descriptor = self._descriptor(
            '<field index="0" term="http://x/a"/>'
            '<field index="1" term="http://x/b" default="fallback"/>'
        )

        assert "Borneo" == descriptor.field_plan.build_data(["1", "Borneo"])["http://x/b"]
        assert "fallback" == descriptor.field_plan.build_data(["1", ""])["http://x/b"]

    def test_missing_value_without_default_becomes_empty_string(self):
        descriptor = self._descriptor(
            '<field index="0" term="http://x/a"/>'
            '<field index="1" term="http://x/b"/>'
        )

        assert "" == descriptor.field_plan.build_data(["1", ""])["http://x/b"]

    def test_key_order_follows_the_metafile(self):
        """Row.data key order is visible through str(row), so it must not drift."""
        descriptor = self._descriptor(
            '<field index="0" term="http://x/a"/>'
            '<field term="http://x/country" default="Belgium"/>'
            '<field index="1" term="http://x/b"/>'
        )

        assert ["http://x/a", "http://x/country", "http://x/b"] == list(
            descriptor.field_plan.build_data(["1", "Borneo"])
        )

    def test_row_with_too_few_columns_raises(self):
        descriptor = self._descriptor('<field index="3" term="http://x/a"/>')

        with pytest.raises(InvalidArchive):
            descriptor.field_plan.build_data(["1", "Borneo"])

    def test_the_plan_is_cached(self):
        descriptor = self._descriptor('<field index="0" term="http://x/a"/>')

        assert descriptor.field_plan is descriptor.field_plan


class TestTermGetter(unittest.TestCase):
    def _plan(self, fields_xml):
        section = """
        <core encoding="utf-8" fieldsTerminatedBy="\\t" linesTerminatedBy="\\n" fieldsEnclosedBy="" ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
            <files><location>occurrence.txt</location></files>
            <id index="0" />
            {fields}
        </core>
        """.format(
            fields=fields_xml
        )
        descriptor = DataFileDescriptor.make_from_metafile_section(
            ET.fromstring(section)
        )
        return descriptor.field_plan

    def test_returns_values_in_the_requested_order(self):
        plan = self._plan(
            '<field index="0" term="http://x/a"/>'
            '<field index="1" term="http://x/b"/>'
            '<field index="2" term="http://x/c"/>'
        )
        getter = plan.term_getter(["http://x/c", "http://x/a"])

        assert ("third", "first") == getter(["first", "second", "third"])

    def test_a_single_term_still_yields_a_tuple(self):
        plan = self._plan('<field index="1" term="http://x/b"/>')
        getter = plan.term_getter(["http://x/b"])

        assert ("second",) == getter(["first", "second"])

    def test_no_terms(self):
        plan = self._plan('<field index="0" term="http://x/a"/>')
        getter = plan.term_getter([])

        assert () == getter(["first"])

    def test_a_term_may_be_requested_twice(self):
        plan = self._plan('<field index="0" term="http://x/a"/>')
        getter = plan.term_getter(["http://x/a", "http://x/a"])

        assert ("first", "first") == getter(["first"])

    def test_default_only_term_yields_the_constant(self):
        plan = self._plan(
            '<field index="0" term="http://x/a"/>'
            '<field term="http://x/country" default="Belgium"/>'
        )
        getter = plan.term_getter(["http://x/country", "http://x/a"])

        assert ("Belgium", "first") == getter(["first"])

    def test_default_fills_an_empty_cell(self):
        plan = self._plan(
            '<field index="0" term="http://x/a"/>'
            '<field index="1" term="http://x/b" default="fallback"/>'
        )
        getter = plan.term_getter(["http://x/b"])

        assert ("value",) == getter(["first", "value"])
        assert ("fallback",) == getter(["first", ""])

    def test_missing_value_without_default_becomes_empty_string(self):
        plan = self._plan(
            '<field index="0" term="http://x/a"/>'
            '<field index="1" term="http://x/b" default=""/>'
        )
        getter = plan.term_getter(["http://x/b"])

        assert ("",) == getter(["first", ""])

    def test_unknown_terms_are_named_in_the_error(self):
        plan = self._plan('<field index="0" term="http://x/a"/>')

        with pytest.raises(ValueError) as excinfo:
            plan.term_getter(["http://x/missing", "http://x/a", "http://x/gone"])

        message = str(excinfo.value)
        assert "http://x/missing" in message
        assert "http://x/gone" in message
        assert "http://x/a" not in message

    def test_short_row_raises_invalid_archive(self):
        plan = self._plan(
            '<field index="0" term="http://x/a"/>'
            '<field index="4" term="http://x/e"/>'
        )
        getter = plan.term_getter(["http://x/e"])

        with pytest.raises(InvalidArchive):
            getter(["first", "second"])

    def test_terms_may_be_a_one_shot_iterable(self):
        # term_getter() used to iterate `terms` three times internally (missing, indexes,
        # defaults). A generator is exhausted after the first pass, which silently made
        # every later pass - and therefore every returned tuple - empty.
        plan = self._plan(
            '<field index="0" term="http://x/a"/>'
            '<field index="1" term="http://x/b"/>'
        )
        expected = ("second", "first")

        terms_list = ["http://x/b", "http://x/a"]
        assert expected == plan.term_getter(t for t in terms_list)(["first", "second"])

        # A tuple and a set of a single term must still work (the normalisation must not
        # break non-list iterables that already worked before).
        assert expected == plan.term_getter(tuple(terms_list))(["first", "second"])
        assert ("second",) == plan.term_getter({"http://x/b"})(["first", "second"])
