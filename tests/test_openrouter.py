import unittest
from unittest.mock import patch
from pathlib import Path
import httpx
from app.openrouter import OpenRouter
from app.chat import Chat
from app.catalog import Catalog

class OpenRouterTests(unittest.TestCase):
    def test_round_trip_preserves_call_id(self):
        requests = []
        def post(url, **kwargs):
            requests.append(kwargs['json'])
            if len(requests) == 1:
                message = {'content': None, 'tool_calls': [{'id': 'call-1', 'type': 'function', 'function': {'name': 'search_catalog', 'arguments': '{"category_id":5,"max_price":"600"}'}}]}
            else:
                tool_message = kwargs['json']['messages'][-1]
                self.assertEqual(tool_message['tool_call_id'], 'call-1')
                self.assertIn('599.90', tool_message['content'])
                message = {'content': 'Há opções até R$ 600.'}
            return httpx.Response(200, json={'choices': [{'message': message}]}, request=httpx.Request('POST', url))
        with patch('app.openrouter.httpx.post', side_effect=post):
            answer = Chat(OpenRouter(api_key='test-key'), Catalog(Path('data'))).reply('Violão até 600')
        self.assertIn('600', answer)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]['model'], 'openrouter/free')
        self.assertTrue(requests[0]['provider']['require_parameters'])

    def test_paid_model_and_missing_key_are_rejected(self):
        for kwargs in ({'api_key': ''}, {'api_key': 'test', 'model': 'paid/model'}):
            with self.assertRaises(RuntimeError):
                OpenRouter(**kwargs).generate([], [])

    def test_provider_error_and_malformed_arguments_are_safe(self):
        for status, data in [(429, {'error': 'quota'}), (200, {'choices': [{'message': {'tool_calls': [{'id': 'x', 'function': {'name': 'search_catalog', 'arguments': 'bad json'}}]}}]})]:
            response = httpx.Response(status, json=data, request=httpx.Request('POST', 'https://openrouter.ai'))
            with patch('app.openrouter.httpx.post', return_value=response):
                with self.assertRaises(RuntimeError):
                    OpenRouter(api_key='test').generate([], [])
