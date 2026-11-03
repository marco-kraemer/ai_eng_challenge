import json
import threading
import unittest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.web import app
from app.conversations import ConversationStore
from app.limits import RateLimiter


def packets(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]


class ChatStreamTests(unittest.TestCase):
    def test_recovery_uses_authoritative_message_without_streaming_model_rewrite(self):
        model = Mock()
        plan = {'intent': 'store', 'dismiss_budget_offer': False, 'catalog_search': {'category_scope': 'named', 'category_ids': [5], 'max_price': '10'}}
        model.generate.side_effect = [{'parts': [{'text': json.dumps(plan)}]},
            {'parts': [{'text': json.dumps({'category_ids': [5], 'general_catalog_request': None})}]}]
        with patch('app.web.build_provider', return_value=model), patch('app.telemetry.export_runs'), TestClient(app) as client:
            response = client.post('/api/chat/stream', json={'message': 'Quero violão até dez reais.'})
        events = packets(response)
        done = next(e['result'] for e in events if e['type'] == 'done')
        self.assertEqual(done['recovery']['price_brl'], '429.90')
        self.assertEqual(model.generate.call_count, 2)
    def setUp(self):
        self.store = ConversationStore()
        for target, value in [('conversations', self.store), ('rate_limiter', RateLimiter()), ('chat_slots', threading.BoundedSemaphore(4))]:
            context = patch('app.web.' + target, value); context.start(); self.addCleanup(context.stop)

    def test_stream_progress_and_atomic_final_reply(self):
        with patch('app.web.build_provider') as provider, patch('app.telemetry.export_runs'), TestClient(app) as client:
            r = client.post('/api/chat/stream', json={'message': 'Qual é o endereço da loja?'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/event-stream', r.headers['content-type'])
        events = packets(r)
        self.assertEqual(events[0]['type'], 'accepted')
        self.assertTrue(any(e['type'] == 'progress' for e in events))
        results = [e['result'] for e in events if e['type'] == 'done']
        self.assertEqual(len(results), 1)
        self.assertIn('Rua', results[0]['message'])
        self.assertEqual(len(self.store.history(results[0]['conversation_id'])), 2)
        provider.return_value.generate.assert_not_called()

    def test_midstream_quota_error_releases_lease_without_partial_history(self):
        model = Mock(); model.generate.side_effect = RuntimeError('Limite de uso do modelo atingido.')
        with patch('app.web.build_provider', return_value=model), patch('app.telemetry.export_runs'), TestClient(app) as client:
            r = client.post('/api/chat/stream', json={'message': 'Olá'})
        events = packets(r)
        error = next(e for e in events if e['type'] == 'error')
        self.assertEqual(error['status'], 429)
        token = events[0]['conversation_id']
        self.assertEqual(self.store.history(token), [])
        lease = self.store.acquire(token)
        self.assertIsNotNone(lease); lease.release()
        self.assertFalse(any(e['type'] == 'done' for e in events))
