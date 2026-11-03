import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.web import app

EVIDENCE = {'status': 'found', 'items': [{'id': 'hours', 'title': 'Horários', 'pages': [2],
            'text': 'Segunda a sexta, 09:00 às 18:00.', 'section': '2'}], 'warnings': ['confirme exceções']}


class GraphPolicyTests(unittest.TestCase):
    def test_policy_intent_forces_retrieval_before_generation(self):
        provider = Mock()
        def generate(contents, tools, **options):
            if options.get('response_format'):
                return {'parts': [{'text': 'policies'}]}
            payload = contents[-1]['parts'][0]['functionResponse']['response']
            self.assertEqual(payload, EVIDENCE)
            return {'parts': [{'text': 'De segunda a sexta, das 9h às 18h. Manual, p. 2.'}]}
        provider.generate.side_effect = generate
        with patch('app.web.build_provider', return_value=provider), patch('app.chat.get_policy_index') as index, TestClient(app) as client:
            index.return_value.search.return_value = EVIDENCE
            response = client.post('/api/chat', json={'message': 'Que horas vocês abrem em datas especiais?'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('9h', response.json()['message'])
        self.assertEqual(response.json()['sources'][0]['id'], 'hours')
        index.return_value.search.assert_called_once()
        self.assertEqual(provider.generate.call_count, 2)

    def test_missing_or_failed_evidence_does_not_ask_model_to_invent_answer(self):
        for status, expected in [('not_found', 'encontrei'), ('error', 'consultar')]:
            provider = Mock()
            provider.generate.return_value = {'parts': [{'text': 'policies'}]}
            with patch('app.web.build_provider', return_value=provider), patch('app.chat.get_policy_index') as index, TestClient(app) as client:
                index.return_value.search.return_value = {'status': status, 'items': [], 'warnings': []}
                response = client.post('/api/chat', json={'message': 'Vocês oferecem aulas?'})
            self.assertEqual(response.status_code, 200)
            self.assertIn(expected, response.json()['message'])
            self.assertEqual(response.json()['sources'], [])
            self.assertEqual(provider.generate.call_count, 1)

    def test_return_channel_is_retained_in_retrieval_query(self):
        provider = Mock()
        provider.generate.side_effect = [
            {'parts': [{'text': 'return_channel'}]},
            {'parts': [{'text': 'policies'}]},
            {'parts': [{'text': 'Vou explicar a devolução online conforme o manual.'}]},
        ]
        with patch('app.web.build_provider', return_value=provider), patch('app.chat.get_policy_index') as index, TestClient(app) as client:
            index.return_value.search.return_value = EVIDENCE
            first = client.post('/api/chat', json={'message': 'Posso devolver um violão?'}).json()
            second = client.post('/api/chat', json={'action_id': 'online', 'conversation_id': first['conversation_id']})
        self.assertEqual(second.status_code, 200)
        query = index.return_value.search.call_args.args[0]
        self.assertIn('devolver', query)
        self.assertIn('online', query)
        self.assertLessEqual(len(query), 500)
