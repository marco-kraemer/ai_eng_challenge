import unittest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.web import app, conversations
from app.limits import RateLimiter
from test_open_budget import call, text


class PendingBudgetTests(unittest.TestCase):
    def setUp(self):
        p = patch('app.web.rate_limiter', RateLimiter())
        p.start()
        self.addCleanup(p.stop)

    def test_model_interprets_confirmation_and_selects_offered_budget(self):
        for confirmation in ('quero', 'fechou, pode trazer essas opções', 'vamos nessa'):
            with self.subTest(confirmation=confirmation), patch('app.web.build_provider') as provider, TestClient(app) as client:
                offered = client.post('/api/catalog/search', json={'category_id': 2, 'max_price': '500'}).json()
                price = offered['recovery']['price_brl']
                provider.return_value.generate.side_effect = [
                    text('store'), call('search_catalog', category_id=2, max_price=price), text('Veja os baixos disponíveis.'),
                ]
                response = client.post('/api/chat', json={'message': confirmation, 'conversation_id': offered['conversation_id']})
                self.assertEqual(response.status_code, 200, response.text)
                data = response.json()
                self.assertTrue(data['products'])
                self.assertEqual(data['search']['max_price'], price)
                state = conversations.state(data['conversation_id'])
                self.assertFalse(state.get('pending_budget'))
                self.assertEqual(state['preferences']['max_price'], price)
                agent_context = str(provider.return_value.generate.call_args_list[1].args[0])
                self.assertIn('pending_budget', agent_context)
                self.assertIn(price, agent_context)
                self.assertEqual(provider.return_value.generate.call_count, 3)

    def test_model_dismisses_offer_without_raising_budget(self):
        provider = Mock()
        provider.generate.side_effect = [text('store'), call('dismiss_budget_offer'), text('Tudo bem, mantive seu limite anterior.')]
        with patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
            offer = client.post('/api/catalog/search', json={'category_id': 2, 'max_price': '500'}).json()
            response = client.post('/api/chat', json={'message': 'esse aumento não serve pra mim', 'conversation_id': offer['conversation_id']})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['products'], [])
        state = conversations.state(offer['conversation_id'])
        self.assertEqual(state['preferences']['max_price'], '500.00')
        self.assertFalse(state.get('pending_budget'))
        self.assertEqual(provider.generate.call_count, 3)

    def test_model_extracts_new_budget_instead_of_accepting_offer(self):
        provider = Mock()
        provider.generate.side_effect = [text('store'), call('search_catalog', category_id=2, max_price='2000'), text('Não encontrei baixos nesse valor.')]
        with patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
            offer = client.post('/api/catalog/search', json={'category_id': 2, 'max_price': '500'}).json()
            data = client.post('/api/chat', json={'message': 'consigo esticar até dois mil reais', 'conversation_id': offer['conversation_id']}).json()
        self.assertEqual(data['search']['max_price'], '2000.00')
        self.assertEqual(data['products'], [])
        self.assertEqual(conversations.state(offer['conversation_id'])['preferences']['max_price'], '2000.00')

    def test_reset_removes_pending_offer(self):
        provider = Mock(); provider.generate.return_value = text('offtopic')
        with patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
            offer = client.post('/api/catalog/search', json={'category_id': 2, 'max_price': '500'}).json()
            client.post('/api/conversation/reset', json={'conversation_id': offer['conversation_id']})
            result = client.post('/api/chat', json={'message': 'quero', 'conversation_id': offer['conversation_id']}).json()
            self.assertNotEqual(result['conversation_id'], offer['conversation_id'])
            self.assertEqual(result['products'], [])
            self.assertEqual(provider.generate.call_count, 1)

    def test_mixed_confirmation_does_not_bypass_scope_and_session_is_isolated(self):
        provider = Mock(); provider.generate.return_value = text('offtopic')
        with patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
            offer = client.post('/api/catalog/search', json={'category_id': 2, 'max_price': '500'}).json()
            data = client.post('/api/chat', json={'message': 'sim, me ensine Python', 'conversation_id': offer['conversation_id']}).json()
            self.assertEqual(data['products'], [])
            self.assertIn('fora do meu atendimento', data['message'])
            self.assertEqual(provider.generate.call_count, 1)
            client.post('/api/chat', json={'message': 'quero'})
            self.assertEqual(provider.generate.call_count, 2)
