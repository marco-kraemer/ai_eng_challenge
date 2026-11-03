"""Catalog scope is a complete snapshot shared by UI, tools and conversations."""
from decimal import Decimal
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.catalog import Catalog
from app.catalog_flow import catalog_reply
from app.chat import Chat
from app.conversations import ConversationStore
from app.limits import RateLimiter
from app.web import app


def text(value):
    return {'parts': [{'text': value}]}


def call(**args):
    return {'parts': [{'functionCall': {'name': 'search_catalog', 'args': args}}]}


class CategoryScopeTests(unittest.TestCase):
    def test_rejected_offer_cannot_be_recreated_by_a_second_search(self):
        store = ConversationStore()
        provider = Mock()
        decision = {'intent': 'store', 'catalog_search': None, 'dismiss_budget_offer': True}
        provider.generate.side_effect = [text(json.dumps(decision)), call(category_id=2, max_price='500'), text('Tudo bem, deixamos essa proposta de lado.')]
        with patch('app.web.conversations', store), patch('app.web.rate_limiter', RateLimiter()), patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
            first = client.post('/api/catalog/search', json={'category_id': 2, 'max_price': '500'}).json()
            response = client.post('/api/chat', json={'message': 'Esse aumento não serve, deixa para outra hora.', 'conversation_id': first['conversation_id']})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(store.state(first['conversation_id'])['pending_budget'], {})
        self.assertNotIn('recovery', response.json())

    def test_plan_distinguishes_new_scope_from_explicit_previous_reference(self):
        from app.query_plan import parse_route
        categories = Catalog(Path('data')).categories()['items']
        previous = {'category_id': 3, 'max_price': '1000'}
        for reference, ids in [('all', []), ('previous', [3]), ('named', [5, 9])]:
            decision = {'intent': 'store', 'catalog_search': {'category_scope': reference,
                'category_ids': [5, 9], 'max_price': '1000', 'in_stock': True}}
            _, plan = parse_route(json.dumps(decision), categories, previous)
            actual = [plan['category_id']] if 'category_id' in plan else plan['category_ids']
            self.assertEqual(actual, ids)

    def test_previous_reference_can_use_history_when_no_search_has_happened(self):
        from app.query_plan import parse_route
        categories = Catalog(Path('data')).categories()['items']
        decision = {'intent': 'store', 'catalog_search': {'category_scope': 'previous', 'category_ids': [5]}}
        _, plan = parse_route(json.dumps(decision), categories, {})
        self.assertEqual(plan['category_id'], 5)
        _, plan = parse_route(json.dumps(decision), categories, {'category_ids': []})
        self.assertEqual(plan['category_ids'], [])

    def test_structured_scope_plan_is_executed_once_and_cannot_be_overwritten(self):
        store = ConversationStore()
        provider = Mock()
        plan = {'intent': 'store', 'catalog_search': {'category_ids': [], 'max_price': '1000', 'query': None, 'min_price': None, 'in_stock': True}}
        provider.generate.side_effect = [text(json.dumps(plan)), call(category_id=2), text('Veja as opções consultadas.')]
        with patch('app.web.conversations', store), patch('app.web.rate_limiter', RateLimiter()), patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
            first = client.post('/api/catalog/search', json={'category_id': 3, 'max_price': '1000'}).json()
            response = client.post('/api/chat', json={'message': 'Me dê instrumentos até mil.', 'conversation_id': first['conversation_id']})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data['search']['category_ids'], [])
        self.assertEqual({p['category_id'] for p in data['products']}, {5, 9})
        self.assertEqual(store.state(first['conversation_id'])['preferences']['category_ids'], [])
        classifier_options = provider.generate.call_args_list[0].kwargs
        self.assertEqual(classifier_options['response_format']['type'], 'json_schema')

    def test_union_and_all_categories_filter_before_pagination(self):
        catalog = Catalog(Path('data'))
        for ids in ([5, 9], []):
            result = catalog.search(category_ids=ids, max_price='1000', limit=4)
            self.assertEqual(result['status'], 'found')
            self.assertEqual({p['category_id'] for p in result['items']}, {5, 9})
            self.assertTrue(all(Decimal(p['price_brl']) <= 1000 for p in result['items']))
        self.assertEqual(catalog.search(category_id=5, category_ids=[9])['status'], 'invalid')
        for ids in ([True], ['5'], [5, 5], [0]):
            self.assertEqual(catalog.search(category_ids=ids)['status'], 'invalid')

    def test_listing_every_category_is_normalized_to_all(self):
        catalog = Catalog(Path('data'))
        ids = [category['category_id'] for category in catalog.categories()['items']]
        response, _, state = catalog_reply(catalog, None, '1000', category_ids=ids)
        self.assertEqual(response['search']['category_ids'], [])
        self.assertEqual(response['search']['label'], 'Todos os instrumentos')
        self.assertEqual(state['preferences']['category_ids'], [])

    def test_shared_response_has_matching_scope_and_real_recovery_price(self):
        catalog = Catalog(Path('data'))
        for ids, label in (([5, 9], 'Violões e Ukuleles'), ([], 'Todos os instrumentos')):
            response, _, state = catalog_reply(catalog, None, '10', category_ids=ids)
            self.assertEqual(response['search']['category_ids'], ids)
            self.assertEqual(response['search']['label'], label)
            self.assertEqual(response['recovery']['price_brl'], '159.90')
            self.assertEqual(state['pending_budget']['category_ids'], ids)
            selection = response['actions'][0]['selection'] if response['actions'][0]['id'] == 'raise_budget' else response['actions'][1]['selection']
            self.assertEqual(selection['category_ids'], ids)
            confirmed, _, _ = catalog_reply(catalog, None, selection['max_price'], category_ids=selection['category_ids'])
            self.assertTrue(confirmed['products'])

    def test_api_supports_multiple_or_all_and_rejects_ambiguous_scope(self):
        with patch('app.web.conversations', ConversationStore()), patch('app.web.rate_limiter', RateLimiter()), TestClient(app) as client:
            for body in ({'category_ids': [5, 9]}, {'category_ids': []}):
                response = client.post('/api/catalog/search', json={**body, 'max_price': '1000'})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['search']['category_ids'], body['category_ids'])
                self.assertEqual({p['category_id'] for p in response.json()['products']}, {5, 9})
            for body in ({'category_id': 5, 'category_ids': [9]}, {'category_ids': [999]}, {'category_ids': [True]}, {'category_ids': [5, 5]}):
                response = client.post('/api/catalog/search', json=body)
                self.assertEqual(response.status_code, 422, response.text)

    def test_schema_describes_scope_and_agent_receives_current_category_ids(self):
        provider = Mock(); provider.generate.return_value = text('Como posso ajudar?')
        chat = Chat(provider, Catalog(Path('data')))
        schema = chat.tools['search_catalog'].args_schema.model_json_schema()
        self.assertIn('category_ids', schema['properties'])
        self.assertIn('categoria', schema['properties']['category_id'].get('description', '').lower())
        chat.reply('Quero trocar de instrumento.')
        contents = str(provider.generate.call_args.args[0])
        for category in Catalog(Path('data')).categories()['items']:
            self.assertIn(category['name'], contents)

    def test_new_search_replaces_old_category_offer_and_metadata(self):
        store = ConversationStore()
        provider = Mock()
        provider.generate.side_effect = [text('store'), call(category_id=5, max_price='1000'), text('Veja os violões.'),
            text('store'), call(category_ids=[], max_price='1000'), text('Veja instrumentos de todas as categorias.'),
            text('store'), call(category_ids=[5, 9], max_price='1000'), text('Veja violões e ukuleles.')]
        with patch('app.web.conversations', store), patch('app.web.rate_limiter', RateLimiter()), patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
            initial = client.post('/api/catalog/search', json={'category_id': 3, 'max_price': '1000'}).json()
            token = initial['conversation_id']
            self.assertTrue(store.state(token)['pending_budget'])
            for message, ids in [('quero violão, não tenho muito dinheiro', [5]), ('me dê instrumentos até R$ 1.000', []), ('quero violões e ukuleles até mil', [5, 9])]:
                result = client.post('/api/chat', json={'conversation_id': token, 'message': message})
                self.assertEqual(result.status_code, 200, result.text)
                data = result.json()
                self.assertEqual(data['search']['category_ids'], ids)
                self.assertTrue(data['products'])
                self.assertFalse(store.state(token)['pending_budget'])
                if ids:
                    self.assertTrue(all(p['category_id'] in ids for p in data['products']))
                else:
                    self.assertNotIn('category_id', store.state(token)['preferences'])
