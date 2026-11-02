import unittest
from decimal import Decimal
from pathlib import Path
from app.catalog import Catalog

class CatalogTests(unittest.TestCase):
    def test_budget_stock_and_pagination(self):
        result = Catalog(Path('data')).search(category_id=5, max_price='600.00', in_stock=True, limit=2)
        self.assertEqual(result['status'], 'found')
        self.assertLessEqual(len(result['items']), 2)
        for item in result['items']:
            self.assertLessEqual(Decimal(item['price_brl']), Decimal('600'))
            self.assertGreater(item['stock_quantity'], 0)
            self.assertEqual(item['category_id'], 5)

    def test_invalid_and_empty_are_distinct(self):
        catalog = Catalog(Path('data'))
        self.assertEqual(catalog.search(max_price='-1')['status'], 'invalid')
        self.assertEqual(catalog.search(max_price='NaN')['status'], 'invalid')
        self.assertEqual(catalog.search(max_price='1')['status'], 'not_found')
        self.assertEqual(Catalog(Path('/nonexistent')).search()['status'], 'error')
