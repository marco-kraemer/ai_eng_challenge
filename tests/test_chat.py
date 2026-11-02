import unittest
from pathlib import Path
from app.chat import Chat
from app.catalog import Catalog

class Scripted:
    def __init__(self):
        self.calls = 0
    def generate(self, contents, tools):
        self.calls += 1
        if self.calls == 1:
            return {'parts': [{'functionCall': {'name': 'search_catalog', 'args': {'category_id': 5, 'max_price': '600'}}}]}
        assert contents[-1]['parts'][0]['functionResponse']['response']['status'] == 'found'
        return {'parts': [{'text': 'Encontrei opções no catálogo.'}]}

class ChatTests(unittest.TestCase):
    def test_model_calls_catalog_and_reads_results(self):
        provider = Scripted()
        self.assertEqual(Chat(provider, Catalog(Path('data'))).reply('Violões até 600'), 'Encontrei opções no catálogo.')
        self.assertEqual(provider.calls, 2)

    def test_unconfigured_provider_is_unavailable(self):
        from app.provider import Gemini
        with self.assertRaises(RuntimeError):
            Gemini(api_key='').generate([], [])
