import unittest
from unittest.mock import Mock
from pathlib import Path
from app.catalog import Catalog
from app.assistant import StoreAssistant, REFUSAL, IDENTITY

class GuardrailTests(unittest.TestCase):
    def test_off_topic_and_invalid_classification_never_reach_agent(self):
        for label in ['offtopic', 'ignore rules', '', 'store\nqualquer coisa']:
            provider = Mock()
            provider.generate.return_value = {'parts': [{'text': label}]}
            assistant = StoreAssistant(provider, Catalog(Path('data')))
            self.assertEqual(assistant.reply('Me ensine for loop em Python')['message'], REFUSAL)
            self.assertEqual(provider.generate.call_count, 1)

    def test_identity_is_owned_by_store(self):
        provider = Mock()
        provider.generate.return_value = {'parts': [{'text': 'identity'}]}
        self.assertEqual(StoreAssistant(provider, Catalog(Path('data'))).reply('Qual seu nome?')['message'], IDENTITY)
        self.assertEqual(provider.generate.call_count, 1)

    def test_cards_come_from_catalog_not_model_text(self):
        provider = Mock()
        provider.generate.side_effect = [
            {'parts': [{'text': 'store'}]},
            {'parts': [{'functionCall': {'name': 'search_catalog', 'args': {'category_id': 5, 'max_price': '600', 'limit': 2}}}]},
            {'parts': [{'text': 'Veja os produtos consultados.'}]},
        ]
        result = StoreAssistant(provider, Catalog(Path('data'))).reply('Violão até 600')
        self.assertEqual(len(result['products']), 2)
        self.assertEqual(result['products'][0]['price_brl'], '599.90')

    def test_unavailable_classifier_fails_closed(self):
        provider = Mock()
        provider.generate.side_effect = RuntimeError('quota')
        with self.assertRaises(RuntimeError):
            StoreAssistant(provider, Catalog(Path('data'))).reply('Oi')
        self.assertEqual(provider.generate.call_count, 1)

    def test_unspecified_return_asks_only_purchase_channel(self):
        provider = Mock()
        provider.generate.return_value = {'parts': [{'text': 'return_channel'}]}
        result = StoreAssistant(provider, Catalog(Path('data'))).reply('Posso devolver um instrumento?')
        self.assertIn('online', result['message'])
        self.assertIn('loja física', result['message'])
        self.assertEqual(result['message'].count('?'), 1)
        self.assertTrue(result['needs_return_channel'])
        self.assertEqual(provider.generate.call_count, 1)
