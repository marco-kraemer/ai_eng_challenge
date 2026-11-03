"""Public identity and model instructions must describe the same virtual attendant."""
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
from fastapi.testclient import TestClient

from app.assistant import StoreAssistant
from app.catalog import Catalog
from app.chat import Chat
from app.openrouter import OpenRouter
from app.web import app


class PersonaTests(unittest.TestCase):
    def test_identity_introduces_tom_and_discloses_ai(self):
        provider = Mock()
        provider.generate.return_value = {'parts': [{'text': 'identity'}]}
        response = StoreAssistant(provider, Catalog(Path('data'))).reply('Quem é você?')
        self.assertIn('Tom', response['message'])
        self.assertIn('Empório da Música', response['message'])
        self.assertIn('inteligência artificial', response['message'])
        self.assertEqual(provider.generate.call_count, 1)

    def test_interface_identifies_the_virtual_attendant(self):
        with TestClient(app) as client:
            page = client.get('/')
        self.assertIn('Tom · Assistente virtual', page.text)

    def test_persona_reaches_model_as_system_instructions(self):
        response = httpx.Response(200, json={'choices': [{'message': {'content': 'Posso te ajudar a escolher.'}}]},
                                  request=httpx.Request('POST', 'https://openrouter.ai'))
        with patch('app.openrouter.httpx.post', return_value=response) as post:
            Chat(OpenRouter(api_key='test'), Catalog(Path('data'))).reply('Quero começar a tocar.')
        system = post.call_args.kwargs['json']['messages'][0]
        self.assertEqual(system['role'], 'system')
        self.assertIn('Você é Tom', system['content'])
        self.assertIn('inteligência artificial', system['content'])
