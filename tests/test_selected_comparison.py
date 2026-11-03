import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.web import app
from app.limits import RateLimiter

class SelectedComparisonTests(unittest.TestCase):
    def setUp(self):
        p=patch('app.web.rate_limiter',RateLimiter());p.start();self.addCleanup(p.stop)
    def test_selected_ids_are_compared_without_model(self):
        with patch('app.web.OpenRouter') as provider,TestClient(app) as client:
            response=client.post('/api/catalog/compare',json={'product_ids':[81,82],'max_price':'600'})
        self.assertEqual(response.status_code,200)
        data=response.json()
        self.assertTrue(data['comparison'])
        self.assertIn('preços de tabela',data['message'])
        self.assertEqual([p['product_id'] for p in data['products']],[81,82])
        self.assertEqual(data['products'][1]['budget_difference_brl'],'249.00')
        provider.assert_not_called()
    def test_invalid_or_duplicate_selection_is_rejected(self):
        with TestClient(app) as client:
            for ids in ([81],[81,81],[81,82,83,84,85],[True,82]):
                self.assertEqual(client.post('/api/catalog/compare',json={'product_ids':ids}).status_code,422)
            self.assertEqual(client.post('/api/catalog/compare',json={'product_ids':[81,82],'max_price':'NaN'}).status_code,422)
