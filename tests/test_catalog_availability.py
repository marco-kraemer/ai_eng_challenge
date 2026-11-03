import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.web import app
from app.catalog import Catalog

class AvailabilityTests(unittest.TestCase):
    def test_only_active_in_stock_categories_are_offered(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'categories.csv').write_text('category_id,name,description\n1,Guitarras,Uma\n2,Baixos,Outra\n3,Baterias,Outra\n')
            (root/'products.csv').write_text('product_id,category_id,status,stock_quantity,price_brl\n1,1,active,1,900\n2,2,active,0,700\n3,3,inactive,3,500\n')
            catalog=Catalog(root)
            self.assertEqual([c['category_id'] for c in catalog.available_categories()['items']],[1])
            with patch('app.web.Catalog',return_value=catalog),patch('app.web.OpenRouter') as provider,TestClient(app) as client:
                response=client.get('/api/categories')
            self.assertEqual([c['category_id'] for c in response.json()['categories']],[1])
            provider.assert_not_called()

    def test_unreadable_products_is_error_not_empty_picker(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'categories.csv').write_text('category_id,name,description\n1,Guitarras,Uma\n')
            catalog=Catalog(root)
            with patch('app.web.Catalog',return_value=catalog),TestClient(app) as client:
                self.assertEqual(client.get('/api/categories').status_code,503)
