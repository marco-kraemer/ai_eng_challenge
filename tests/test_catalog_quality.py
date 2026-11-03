from pathlib import Path
import unittest
from app.catalog import Catalog


class CatalogQualityTests(unittest.TestCase):
    def test_conflicting_key_counts_are_flagged_in_search_and_comparison(self):
        catalog = Catalog(Path('data'))
        product = catalog.search(query='Korg Synth 1')['items'][0]
        self.assertTrue(product.get('warnings'))
        self.assertIn('88', product['warnings'][0])
        self.assertIn('61', product['warnings'][0])
        compared = catalog.compare([142, 81])['items']
        self.assertEqual(product['warnings'], compared[0]['warnings'])
        self.assertFalse(compared[1].get('warnings'))
