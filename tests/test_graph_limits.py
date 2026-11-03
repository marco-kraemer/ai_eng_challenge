import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.assistant import StoreAssistant
from app.catalog import Catalog
from app.chat import Chat
from app.limits import RateLimiter
from app.web import app


class GraphLimitTests(unittest.TestCase):
    def test_large_context_is_rejected_before_classifier(self):
        provider = Mock()
        provider.generate.return_value = {'parts': [{'text': 'offtopic'}]}
        history = [{'role': 'user', 'parts': [{'text': 'x' * 30000}]}]
        with self.assertRaisesRegex(RuntimeError, 'Limite de contexto'):
            StoreAssistant(provider, Catalog(Path('data'))).reply('Oi', history=history)
        provider.generate.assert_not_called()

    def test_repeated_tool_requests_stop_after_four_generations(self):
        provider = Mock()
        provider.generate.return_value = {'parts': [{'functionCall': {'name': 'list_categories', 'args': {}}}]}
        with self.assertRaisesRegex(RuntimeError, 'Limite de consultas'):
            Chat(provider, Catalog(Path('data'))).reply('Quero instrumentos')
        self.assertEqual(provider.generate.call_count, 4)

    def test_more_than_three_tools_are_rejected_before_execution(self):
        provider = Mock()
        provider.generate.return_value = {'parts': [{'functionCall': {'name': 'search_catalog', 'args': {}}}] * 4}
        catalog = Mock()
        with self.assertRaisesRegex(RuntimeError, 'Limite de consultas'):
            Chat(provider, catalog).reply('Quero instrumentos')
        catalog.search.assert_not_called()

    def test_quota_error_survives_graph_as_http_429(self):
        provider = Mock()
        provider.generate.side_effect = RuntimeError('Limite de uso do modelo atingido. Aguarde e tente mais tarde.')
        with patch('app.web.rate_limiter', RateLimiter()), patch('app.web.OpenRouter', return_value=provider), TestClient(app) as client:
            response = client.post('/api/chat', json={'message': 'Oi'})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '60')
        self.assertIn('Limite de uso', response.json()['detail'])
        self.assertEqual(provider.generate.call_count, 1)

    def test_email_is_not_sent_to_model_or_saved_in_graph_context(self):
        from app.web import conversations
        provider = Mock()
        with patch('app.web.rate_limiter', RateLimiter()), patch('app.web.OpenRouter', return_value=provider), TestClient(app) as client:
            response = client.post('/api/chat', json={'message': 'Meu pedido foi feito com cliente@example.test'})
        data = response.json()
        self.assertTrue(data['order_verification_required'])
        provider.generate.assert_not_called()
        self.assertNotIn('cliente@example.test', str(conversations.history(data['conversation_id'])))
        self.assertNotIn('cliente@example.test', str(conversations.state(data['conversation_id'])))
