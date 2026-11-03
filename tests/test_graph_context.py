import unittest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.web import app
from app.limits import RateLimiter
from app.conversations import ConversationStore


class GraphContextTests(unittest.TestCase):
    def setUp(self):
        self.limiter = patch('app.web.rate_limiter', RateLimiter())
        self.limiter.start()
        self.addCleanup(self.limiter.stop)

    def test_guided_selection_then_comparison_uses_real_selected_ids_and_budget(self):
        provider = Mock()
        provider.generate.side_effect = [
            {'parts': [{'text': 'compare'}]},
            {'parts': [{'text': 'Aqui estão as diferenças das opções selecionadas.'}]},
        ]
        with patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
            selected = client.post('/api/catalog/search', json={'category_id': 5, 'max_price': '1000'}).json()
            ids = [item['product_id'] for item in selected['products']]
            compared = client.post('/api/chat', json={'action_id': 'compare', 'conversation_id': selected['conversation_id']})
        self.assertEqual(compared.status_code, 200)
        result = compared.json()
        self.assertEqual([item['product_id'] for item in result['products']], ids)
        self.assertTrue(all('budget_difference_brl' in item for item in result['products']))
        self.assertIn('Aqui estão', result['message'])
        self.assertIn('1000', str(provider.generate.call_args))
        self.assertEqual(provider.generate.call_count, 2)

    def test_typed_context_tracks_pending_question_and_modality_and_resets(self):
        from app.web import conversations
        evidence = {'status': 'found', 'items': [{'id': 'return', 'pages': [4], 'text': 'Compra online: sete dias.'}], 'warnings': []}
        provider = Mock()
        provider.generate.side_effect = [
            {'parts': [{'text': 'return_channel'}]},
            {'parts': [{'text': 'policies'}]},
            {'parts': [{'text': 'A regra da compra online está no manual.'}]},
        ]
        with patch('app.web.build_provider', return_value=provider), patch('app.chat.get_policy_index') as index, TestClient(app) as client:
            index.return_value.search.return_value = evidence
            first = client.post('/api/chat', json={'message': 'Posso devolver um violão?'}).json()
            token = first['conversation_id']
            self.assertEqual(conversations.state(token)['topic'], 'policies')
            self.assertIn('devolver', conversations.state(token)['pending_question'])
            client.post('/api/chat', json={'action_id': 'online', 'conversation_id': token})
            self.assertEqual(conversations.state(token)['purchase_channel'], 'online')
            self.assertEqual(conversations.state(token)['pending_question'], '')
            another = conversations.open(None)
            self.assertNotIn('purchase_channel', conversations.state(another))
            client.post('/api/conversation/reset', json={'conversation_id': token})
            self.assertEqual(conversations.state(token), {})

    def test_explicit_modality_is_saved_even_without_clarification(self):
        from app.web import conversations
        provider = Mock()
        provider.generate.side_effect = [
            {'parts': [{'text': 'policies'}]},
            {'parts': [{'text': 'A devolução online segue o manual.'}]},
        ]
        evidence = {'status': 'found', 'items': [{'id': 'return', 'pages': [4], 'text': 'Compra online: sete dias.'}], 'warnings': []}
        with patch('app.web.build_provider', return_value=provider), patch('app.chat.get_policy_index') as index, TestClient(app) as client:
            index.return_value.search.return_value = evidence
            response = client.post('/api/chat', json={'message': 'Comprei online e quero devolver meu violão.'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(conversations.state(response.json()['conversation_id'])['purchase_channel'], 'online')

    def test_expiry_discards_structured_graph_context(self):
        now = [0.0]
        store = ConversationStore(ttl=10, clock=lambda: now[0])
        token = store.open(None)
        store.append(token, 'Pergunta', 'Resposta', {'topic': 'policies', 'purchase_channel': 'online'})
        now[0] = 11
        renewed = store.open(token)
        self.assertNotEqual(token, renewed)
        self.assertEqual(store.state(renewed), {})
