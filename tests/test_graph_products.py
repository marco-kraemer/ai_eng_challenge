"""Customer journeys through the real LangGraph and LangChain integration."""
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from app.catalog import Catalog
from app.chat import Chat
from app.assistant import StoreAssistant, REFUSAL


class GraphProductTests(unittest.TestCase):
    def test_api_catalog_uses_compiled_graph_and_langchain_tools(self):
        from app.web import app
        provider = Mock()
        provider.generate.side_effect = [
            {'parts': [{'text': 'store'}]},
            {'parts': [{'functionCall': {'name': 'search_catalog', 'args': {'category_id': 5, 'max_price': '600'}}}]},
            {'parts': [{'text': 'Estas opções estão disponíveis.'}]},
        ]
        assistant = StoreAssistant(provider, Catalog(Path('data')))
        self.assertIsInstance(assistant.chat.model, BaseChatModel)
        self.assertTrue(all(isinstance(tool, BaseTool) for tool in assistant.chat.tools.values()))
        self.assertIn('classify', assistant.graph.get_graph().nodes)
        self.assertIn('tools', assistant.chat.graph.get_graph().nodes)
        with patch('app.web.StoreAssistant', return_value=assistant), patch('app.web.build_provider'), TestClient(app) as client:
            response = client.post('/api/chat', json={'message': 'Violão até 600'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['products'][0]['price_brl'], '599.90')

    def test_invalid_tool_arguments_never_reach_catalog(self):
        provider = Mock()
        provider.generate.side_effect = [
            {'parts': [{'functionCall': {'name': 'search_catalog', 'args': {'category_id': True, 'extra': 'bad'}}}]},
            {'parts': [{'text': 'Preciso de uma categoria válida.'}]},
        ]
        catalog = Mock()
        catalog.categories.return_value = {'status': 'found', 'items': []}
        chat = Chat(provider, catalog)
        chat.reply('Quero um instrumento')
        catalog.search.assert_not_called()
        result = provider.generate.call_args.args[0][-1]['parts'][0]['functionResponse']['response']
        self.assertEqual(result['status'], 'invalid')

    def test_refusal_traverses_only_scope_branch(self):
        provider = Mock()
        provider.generate.return_value = {'parts': [{'text': 'offtopic'}]}
        assistant = StoreAssistant(provider, Catalog(Path('data')))
        self.assertIn('refuse', assistant.graph.get_graph().nodes)
        self.assertEqual(assistant.reply('Ensina Python')['message'], REFUSAL)
        self.assertEqual(provider.generate.call_count, 1)
