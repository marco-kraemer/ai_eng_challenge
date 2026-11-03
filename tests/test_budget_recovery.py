import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.web import app
from app.limits import RateLimiter
from app.catalog import Catalog
from pathlib import Path
from decimal import Decimal

class BudgetRecoveryTests(unittest.TestCase):
    def setUp(self):
        p=patch('app.web.rate_limiter',RateLimiter());p.start();self.addCleanup(p.stop)
    def test_budget_miss_suggests_actual_cheapest_without_expanding_search(self):
        with patch('app.web.build_provider') as provider,TestClient(app) as client:
            data=client.post('/api/catalog/search',json={'category_id':5,'max_price':'10'}).json()
            self.assertEqual(data['products'],[])
            self.assertEqual(data['recovery']['reason'],'budget')
            minimum=data['recovery']['price_brl']
            eligible=Catalog(Path('data')).search(category_id=5,limit=10)['items']
            self.assertEqual(Decimal(minimum),min(Decimal(p['price_brl']) for p in eligible))
            self.assertIn('Quer ver',data['message'])
            self.assertEqual(data['search']['max_price'],'10.00')
            self.assertNotIn('hours',[a['id'] for a in data['actions']])
            action=next(a for a in data['actions'] if a.get('kind')=='catalog_search')
            confirmed=client.post('/api/catalog/search',json=action['selection']).json()
            self.assertTrue(confirmed['products'])
            provider.assert_not_called()
    def test_category_without_stock_does_not_offer_higher_budget(self):
        with TestClient(app) as client:
            data=client.post('/api/catalog/search',json={'category_id':8,'max_price':'100'}).json()
        self.assertEqual(data['products'],[])
        self.assertEqual(data['recovery']['reason'],'unavailable')
        self.assertNotIn('catalog_search',[a.get('kind') for a in data['actions']])
    def test_data_failure_is_not_a_budget_miss(self):
        with patch('app.catalog.Catalog.search',return_value={'status':'error','items':[]}),TestClient(app) as client:
            self.assertEqual(client.post('/api/catalog/search',json={'category_id':5,'max_price':'10'}).status_code,503)
