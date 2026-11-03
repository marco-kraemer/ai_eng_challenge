import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.catalog import Catalog
from app.web import app
from app.limits import RateLimiter

class CatalogNameSearchTests(unittest.TestCase):
    def test_name_model_case_and_separator_variations_find_exact_model(self):
        catalog=Catalog(Path('data'))
        for query in ('Takamine GD20','takamine gd-20',' GD 20 TAKAMINE ','GD20'):
            result=catalog.search(query=query)
            self.assertEqual(result['status'],'found',query)
            self.assertEqual([p['product_id'] for p in result['items']],[95])
            self.assertEqual(result['items'][0]['price_brl'],'2199.00')
        self.assertEqual(catalog.search(query='YAMAHA c-40')['items'][0]['product_id'],81)
        self.assertEqual(catalog.search(query='takamine eletrico gc5ce')['items'][0]['product_id'],100)

    def test_search_respects_filters_and_does_not_substitute_unknown_model(self):
        catalog=Catalog(Path('data'))
        self.assertEqual(catalog.search(query='Takamine GD20',max_price='1000')['status'],'not_found')
        self.assertEqual(catalog.search(query='Takamine GD20',category_id=1)['status'],'not_found')
        self.assertEqual(catalog.search(query='Takamine GD2000')['status'],'not_found')
        self.assertEqual(catalog.search(query='Modelo inexistente 99999')['status'],'not_found')
        first=catalog.search(query='Takamine',limit=1)
        second=catalog.search(query='Takamine',limit=1,offset=first['next_offset'])
        self.assertNotEqual(first['items'][0]['product_id'],second['items'][0]['product_id'])

    def test_empty_symbol_only_and_invalid_query_are_rejected(self):
        catalog=Catalog(Path('data'))
        for query in ('','  ','---',123,'x'*201):
            self.assertEqual(catalog.search(query=query)['status'],'invalid')
        self.assertEqual(catalog.search()['status'],'found')

    def test_chat_api_uses_name_tool_and_returns_product_beyond_first_page(self):
        provider=Mock()
        provider.generate.side_effect=[
            {'parts':[{'text':'store'}]},
            {'parts':[{'functionCall':{'name':'search_catalog','args':{'query':'Takamine GD20'}}}]},
            {'parts':[{'text':'Encontrei o Takamine GD20. Confira o preço e a disponibilidade no card.'}]},
        ]
        with patch('app.web.rate_limiter',RateLimiter()),patch('app.web.build_provider',return_value=provider),TestClient(app) as client:
            response=client.post('/api/chat',json={'message':'Quanto custa o Takamine GD20?'})
        self.assertEqual(response.status_code,200)
        self.assertEqual([p['product_id'] for p in response.json()['products']],[95])
        self.assertEqual(response.json()['products'][0]['price_brl'],'2199.00')
        self.assertEqual(provider.generate.call_count,3)
