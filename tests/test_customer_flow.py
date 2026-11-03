import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.web import app
from app.actions import next_actions, resolve_action

class CustomerFlowTests(unittest.TestCase):
    def test_category_picker_uses_real_categories_without_model(self):
        with patch('app.web.OpenRouter') as provider,TestClient(app) as client:
            response=client.get('/api/categories')
        self.assertEqual(response.status_code,200)
        categories=response.json()['categories']
        from app.catalog import Catalog
        from pathlib import Path
        self.assertEqual({c['category_id'] for c in categories}, {c['category_id'] for c in Catalog(Path('data')).available_categories()['items']})
        guitar=next(c for c in categories if c['category_id']==5)
        self.assertEqual(guitar['name'],'Violões')
        self.assertIn('violao',guitar['illustration'])
        provider.assert_not_called()

    def test_selected_instrument_and_budget_search_catalog_directly(self):
        with patch('app.web.OpenRouter') as provider,TestClient(app) as client:
            response=client.post('/api/catalog/search',json={'category_id':5,'max_price':'600.00'})
        self.assertEqual(response.status_code,200)
        data=response.json()
        self.assertTrue(data['products'])
        for product in data['products']:
            self.assertEqual(product['category_id'],5)
            self.assertLessEqual(float(product['price_brl']),600)
            self.assertGreater(product['stock_quantity'],0)
        self.assertTrue(data['conversation_id'])
        provider.assert_not_called()

    def test_no_budget_is_not_replaced_with_default_price_or_instrument(self):
        with patch('app.web.OpenRouter') as provider,TestClient(app) as client:
            response=client.post('/api/catalog/search',json={'category_id':1})
            invalid=client.post('/api/catalog/search',json={'category_id':5,'max_price':'NaN'})
        self.assertEqual(response.status_code,200)
        self.assertTrue(all(p['category_id']==1 for p in response.json()['products']))
        self.assertEqual(invalid.status_code,422)
        provider.assert_not_called()

    def test_customer_actions_have_no_staff_draft(self):
        actions=next_actions({'sources':[{'id':'s2-0'}],'products':[]})
        self.assertNotIn('draft',[a['id'] for a in actions])
        self.assertNotIn('atendente',str(actions).lower())
        with self.assertRaises(ValueError):resolve_action('draft',{'allowed_actions':['draft']})
