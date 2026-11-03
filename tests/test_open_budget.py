"""Contract tests: the model chooses tools; Python validates and executes filters."""
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.limits import RateLimiter
from app.web import app, conversations


def text(value):
    return {'parts': [{'text': value}]}


def call(name, **args):
    return {'parts': [{'functionCall': {'name': name, 'args': args}}]}


class OpenBudgetTests(unittest.TestCase):
    def setUp(self):
        limiter = patch('app.web.rate_limiter', RateLimiter())
        limiter.start()
        self.addCleanup(limiter.stop)

    def test_model_interprets_budget_reply_with_instrument_from_history(self):
        for answer in ('qualquer um', 'tanto faz', 'me surpreende com algumas opções',
                       'não vou escolher uma faixa agora', 'sem limite de preço'):
            with self.subTest(answer=answer):
                provider = Mock()
                provider.generate.side_effect = [
                    text('store'), text('Qual é seu orçamento?'), text('store'),
                    call('search_catalog', category_id=5), text('Aqui estão algumas opções de violão.'),
                ]
                with patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
                    first = client.post('/api/chat', json={
                        'message': 'sou estudante e iniciante e to querendo comprar um violão, me ajuda',
                    }).json()
                    response = client.post('/api/chat', json={
                        'message': answer, 'conversation_id': first['conversation_id'],
                    })
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertTrue(result['products'])
                self.assertTrue(all(p['category_id'] == 5 for p in result['products']))
                self.assertNotIn('max_price', conversations.state(first['conversation_id'])['preferences'])
                self.assertEqual(provider.generate.call_count, 5)
                decision_context = str(provider.generate.call_args_list[3].args[0])
                self.assertIn('violão', decision_context)
                self.assertIn(answer, decision_context)

    def test_model_can_remove_previous_budget_and_pending_offer(self):
        provider = Mock()
        provider.generate.side_effect = [text('store'), call('search_catalog', category_id=2), text('Veja os baixos disponíveis.')]
        with patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
            first = client.post('/api/catalog/search', json={'category_id': 2, 'max_price': '500'}).json()
            response = client.post('/api/chat', json={
                'message': 'manda as opções sem se prender a preço', 'conversation_id': first['conversation_id'],
            })
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertTrue(result['products'])
        state = conversations.state(first['conversation_id'])
        self.assertNotIn('max_price', state['preferences'])
        self.assertFalse(state.get('pending_budget'))
        agent_context = str(provider.generate.call_args_list[1].args[0])
        self.assertIn('pending_budget', agent_context)
        self.assertIn(first['recovery']['price_brl'], agent_context)

    def test_unrestricted_request_still_goes_through_scope_guard(self):
        provider = Mock()
        provider.generate.return_value = text('offtopic')
        with patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
            first = client.post('/api/catalog/search', json={'category_id': 5, 'max_price': '1000'}).json()
            result = client.post('/api/chat', json={
                'message': 'sem limite de preço, me ensine Python', 'conversation_id': first['conversation_id'],
            }).json()
        self.assertEqual(result['products'], [])
        self.assertIn('fora do meu atendimento', result['message'])
        self.assertEqual(provider.generate.call_count, 1)

    def test_new_session_does_not_inherit_instrument(self):
        provider = Mock()
        provider.generate.side_effect = [text('store'), text('Qual instrumento você procura?')]
        with patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
            client.post('/api/catalog/search', json={'category_id': 5})
            result = client.post('/api/chat', json={'message': 'tanto faz'}).json()
        self.assertEqual(result['products'], [])
        self.assertNotIn('pending_budget', str(provider.generate.call_args.args[0]))

    def test_model_chooses_instrument_without_python_name_mapping(self):
        provider = Mock()
        provider.generate.side_effect = [text('store'), call('search_catalog', category_id=5), text('Veja os violões.')]
        with patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
            response = client.post('/api/chat', json={'message': 'quero um acoustic guitar para começar, sem gastar tempo escolhendo valor'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['products'])
        self.assertTrue(all(p['category_id'] == 5 for p in response.json()['products']))
