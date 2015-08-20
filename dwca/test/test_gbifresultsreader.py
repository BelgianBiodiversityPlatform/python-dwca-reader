# -*- coding: utf-8 -*-

import unittest

import xml.etree.ElementTree as ET

from dwca.read import GBIFResultsReader
from dwca.darwincore.utils import qualname as qn

from .helpers import GBIF_RESULTS_PATH, MISSINGMETA_PATH


class TestGBIFResultsReader(unittest.TestCase):
    """Unit tests for GBIFResultsReader class."""

    CITATIONS_CONTENT = """Please cite this data as follows, and pay attention
 to the rights documented in the rights.txt: blablabla"""

    RIGHTS_CONTENT = """Dataset: Collection Pisces SMF
Rights as supplied: Not supplied"""

    def test_dwcareader_features(self):
        """Ensure we didn't break inherited basic DwCAReader features."""
        with GBIFResultsReader(GBIF_RESULTS_PATH) as results_dwca:
            self.assertEqual(158, len(results_dwca.rows))
            self.assertEqual('http://rs.tdwg.org/dwc/terms/Occurrence',
                             results_dwca.descriptor.core.type)

            row1 = results_dwca.rows[0]
            self.assertEqual('Tetraodontidae', row1.data[qn('family')])
            self.assertEqual([], row1.extensions)

    # Specific GBIFResultsReader feature
    def test_citations_access(self):
        """Check the content of citations.txt is accessible."""
        with GBIFResultsReader(GBIF_RESULTS_PATH) as results_dwca:
            self.assertEqual(self.CITATIONS_CONTENT, results_dwca.citations)

    def test_rights_access(self):
        """Check the content of rights.txt is accessible."""
        with GBIFResultsReader(GBIF_RESULTS_PATH) as results_dwca:
            self.assertEqual(self.RIGHTS_CONTENT, results_dwca.rights)

    def test_source_metadata(self):
        with GBIFResultsReader(GBIF_RESULTS_PATH) as results:
            # We have 23 EML files in dataset/
            self.assertEqual(23, len(results.source_metadata))
            # Assert a key is present
            self.assertTrue('eccf4b09-f0c8-462d-a48c-41a7ce36815a' in
                            results.source_metadata)

            self.assertFalse('incorrect-UUID' in results.source_metadata)

            # Assert it's the correct EML file (content!)
            sm = results.source_metadata
            metadata = sm['eccf4b09-f0c8-462d-a48c-41a7ce36815a']

            self.assertIsInstance(metadata, ET.Element)

            # Assert we can read basic fields from EML:
            self.assertEqual(metadata.find('dataset').find('creator').find('individualName')
                             .find('givenName').text,
                             'Rob')

    def test_row_source_metadata(self):
        with GBIFResultsReader(GBIF_RESULTS_PATH) as results:
            first_row = results.get_row_by_id('607759330')
            m = first_row.source_metadata

            self.assertIsInstance(m, ET.Element)

            v = (m.find('dataset').find('creator').find('individualName')
                  .find('givenName').text)

            self.assertEqual(v, 'Stanley')

            last_row = results.get_row_by_id('782700656')
            m = last_row.source_metadata

            self.assertIsInstance(m, ET.Element)
            v = m.find('dataset').find('language').text
            self.assertEqual(v, 'en')

    def test_row_source_missing_metadata(self):
        with GBIFResultsReader(MISSINGMETA_PATH) as results:
            # We have source metadata, but not for all datasets/line...
            # We sould have None in this cases
            first_row = results.get_row_by_id('607759330')
            self.assertEqual(None, first_row.source_metadata)
