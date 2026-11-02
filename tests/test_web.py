import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.web import app

class WebTests(unittest.TestCase):
    def test_chat_page_and_unavailable_provider(self):
        with patch('app.web.OpenRouter') as provider, TestClient(app) as client:
            provider.return_value.generate.side_effect = RuntimeError('unavailable')
            response = client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn('Empório', response.text)
            self.assertEqual(client.post('/api/chat', json={'message': ''}).status_code, 422)
            self.assertEqual(client.post('/api/chat', json={'message': 'Olá'}).status_code, 503)
