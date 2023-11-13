from dwca.read import DwCAReader
from dwca.rows import CoreRow
from dwca.star_record import StarRecordIterator
from .helpers import sample_data_path
import unittest

class TestStarRecordIterator(unittest.TestCase):

    def test_inner_join(self):

        expected_inner_join = frozenset({
            frozenset({('1', 0, 'Description'), ('1', 0, 'Taxon'), ('1', 0, 'VernacularName')}),
            frozenset({('1', 0, 'Description'), ('1', 0, 'Taxon'), ('1', 1, 'VernacularName')}),
            frozenset({('1', 0, 'Description'), ('1', 0, 'Taxon'), ('1', 2, 'VernacularName')}),
            frozenset({('1', 1, 'Description'), ('1', 0, 'Taxon'), ('1', 0, 'VernacularName')}),
            frozenset({('1', 1, 'Description'), ('1', 0, 'Taxon'), ('1', 1, 'VernacularName')}),
            frozenset({('1', 1, 'Description'), ('1', 0, 'Taxon'), ('1', 2, 'VernacularName')})
        })

        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            star_records = StarRecordIterator(dwca.extension_files + [dwca.core_file], how="inner")
            stars = []
            for star_record in star_records:
                rows = []
                for row in star_record:
                    rows.append((row.id if isinstance(row, CoreRow) else row.core_id, row.position, row.rowtype.split('/')[-1]))
                stars.append(frozenset(rows))

            assert frozenset(stars) == expected_inner_join
    
    def test_outer_join(self):

        expected_outer_join = frozenset({
            frozenset({('4', 2, 'Description'), ('4', 3, 'Taxon')}),
            frozenset({('1', 0, 'Description'), ('1', 0, 'Taxon'), ('1', 0, 'VernacularName')}),
            frozenset({('1', 0, 'Description'), ('1', 0, 'Taxon'), ('1', 1, 'VernacularName')}),
            frozenset({('1', 0, 'Description'), ('1', 0, 'Taxon'), ('1', 2, 'VernacularName')}),
            frozenset({('1', 1, 'Description'), ('1', 0, 'Taxon'), ('1', 0, 'VernacularName')}),
            frozenset({('1', 1, 'Description'), ('1', 0, 'Taxon'), ('1', 1, 'VernacularName')}),
            frozenset({('1', 1, 'Description'), ('1', 0, 'Taxon'), ('1', 2, 'VernacularName')}),
            frozenset({('3', 2, 'Taxon')}),
            frozenset({('2', 1, 'Taxon'), ('2', 3, 'VernacularName')}) 
        })

        with DwCAReader(sample_data_path("dwca-2extensions.zip")) as dwca:
            star_records = StarRecordIterator(dwca.extension_files + [dwca.core_file], how="outer")
            stars = []
            for star_record in star_records:
                rows = []
                for row in star_record:
                    rows.append((row.id if isinstance(row, CoreRow) else row.core_id, row.position, row.rowtype.split('/')[-1]))
                stars.append(frozenset(rows))

            assert frozenset(stars) == expected_outer_join
