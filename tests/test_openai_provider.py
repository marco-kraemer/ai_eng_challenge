import os
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app.catalog import Catalog
from app.chat import Chat
from app.llm import build_provider
from app.openai_provider import OpenAI


class OpenAIProviderTests(unittest.TestCase):
    def test_default_provider_uses_saved_key_name_and_never_falls_back(self):
        with patch.dict(os.environ, {'OPEN_AI_KEY': 'private-test', 'OPENROUTER_API_KEY': 'other'}, clear=True):
            provider = build_provider()
            self.assertIsInstance(provider, OpenAI)
            self.assertEqual(provider.api_key, 'private-test')
            self.assertEqual(provider.model, 'gpt-4.1-mini')
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'other'}, clear=True), patch('httpx.post') as post:
            with self.assertRaisesRegex(RuntimeError, 'OPEN_AI_KEY'):
                build_provider().generate([], [])
            post.assert_not_called()

    def test_tool_round_trip_uses_openai_and_preserves_call_ids(self):
        requests = []
        def post(url, **kwargs):
            self.assertEqual(url, 'https://api.openai.com/v1/chat/completions')
            body = kwargs['json']; requests.append(body)
            self.assertEqual(body['model'], 'gpt-4.1-mini')
            self.assertEqual(body['max_completion_tokens'], 2048)
            self.assertFalse(body['store'])
            self.assertNotIn('provider', body)
            if len(requests) == 1:
                message = {'content': None, 'tool_calls': [{'id': 'openai-call', 'type': 'function',
                    'function': {'name': 'search_catalog', 'arguments': '{"category_id":5,"max_price":"600"}'}}]}
            else:
                self.assertEqual(body['messages'][-1]['tool_call_id'], 'openai-call')
                self.assertIn('599.90', body['messages'][-1]['content'])
                message = {'content': 'Aqui estão os violões até R$ 600.'}
            return httpx.Response(200, json={'model': 'gpt-4.1-mini', 'choices': [{'message': message}]}, request=httpx.Request('POST', url))
        with patch('httpx.post', side_effect=post):
            provider = OpenAI(api_key='test')
            chat = Chat(provider, Catalog(Path('data')))
            self.assertIn('600', chat.reply('Violões até 600'))
            self.assertTrue(chat.products)
        self.assertEqual(len(requests), 2)

    def test_unapproved_model_never_spends(self):
        with patch('httpx.post') as post:
            with self.assertRaises(RuntimeError):
                OpenAI(api_key='test', model='expensive-unapproved').generate([], [])
            post.assert_not_called()

    def test_auth_and_quota_failures_do_not_retry_or_expose_secrets(self):
        for status in (401, 429):
            with self.subTest(status=status):
                response = httpx.Response(status, json={'error': {'message': 'private-test'}},
                    request=httpx.Request('POST', 'https://api.openai.com/v1/chat/completions'))
                with patch('httpx.post', return_value=response) as post:
                    with self.assertRaises(RuntimeError) as error:
                        OpenAI(api_key='private-test').generate([], [])
                    self.assertNotIn('private-test', str(error.exception))
                    self.assertEqual(post.call_count, 1)

    def test_unknown_provider_is_rejected_and_legacy_requires_explicit_selection(self):
        from app.openrouter import OpenRouter
        with patch.dict(os.environ, {'LLM_PROVIDER': 'openrouter'}, clear=True):
            self.assertIsInstance(build_provider(), OpenRouter)
        with patch.dict(os.environ, {'LLM_PROVIDER': 'typo'}, clear=True):
            with self.assertRaises(ValueError):
                build_provider()

    def test_http_chat_uses_configured_provider_for_classification(self):
        from fastapi.testclient import TestClient
        from app.web import app
        provider = OpenAI(api_key='test')
        response = httpx.Response(200, json={'choices': [{'message': {'content': 'identity'}}]},
            request=httpx.Request('POST', provider.endpoint))
        with patch('app.web.build_provider', return_value=provider), patch('httpx.post', return_value=response) as post, TestClient(app) as client:
            result = client.post('/api/chat', json={'message': 'Quem é você?'})
        self.assertEqual(result.status_code, 200)
        self.assertIn('Tom', result.json()['message'])
        self.assertEqual(post.call_args.args[0], provider.endpoint)

