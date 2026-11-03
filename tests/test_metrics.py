import unittest
from unittest.mock import patch
import httpx

from app.metrics import usage_metrics, aggregate
from app.telemetry import turn
from app.langchain_model import StoreChatModel
from app.openai_provider import OpenAI
from langchain_core.messages import HumanMessage


class MetricsTests(unittest.TestCase):
    def test_guided_catalog_measures_zero_llm_calls(self):
        from fastapi.testclient import TestClient
        from app.web import app
        with patch('app.telemetry.export_runs') as export, TestClient(app) as client:
            response = client.post('/api/catalog/search', json={'category_id': 5, 'max_price': '600'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('trace_id', response.json())
        self.assertEqual(export.call_args.args[0][0]['extra']['metadata']['llm_calls'], 0)
    def test_cached_tokens_are_not_charged_twice(self):
        m = usage_metrics({'prompt_tokens': 1000, 'completion_tokens': 100,
            'prompt_tokens_details': {'cached_tokens': 500}}, 'gpt-4.1-mini-2025-04-14')
        self.assertEqual(m['input_tokens'], 1000)
        self.assertAlmostEqual(m['cost_usd'], .00041)
        self.assertIsNone(usage_metrics(None, 'gpt-4.1-mini')['cost_usd'])
        self.assertIsNone(usage_metrics({'prompt_tokens': 1, 'completion_tokens': 2}, 'unknown')['cost_usd'])

    def test_provider_usage_is_attached_to_actual_turn(self):
        response = httpx.Response(200, json={'model': 'gpt-4.1-mini', 'choices': [{'message': {'content': 'Olá'}}],
            'usage': {'prompt_tokens': 20, 'completion_tokens': 5}}, request=httpx.Request('POST', OpenAI.endpoint))
        with patch('httpx.post', return_value=response), patch('app.telemetry.export_runs'):
            with turn('session') as trace:
                StoreChatModel(transport=OpenAI(api_key='test'), cache=False).invoke([HumanMessage(content='Oi')])
        self.assertEqual(trace.metrics['llm_calls'], 1)
        self.assertEqual(trace.metrics['input_tokens'], 20)
        self.assertEqual(trace.metrics['output_tokens'], 5)
        self.assertGreater(trace.metrics['cost_usd'], 0)

    def test_aggregate_separates_missing_usage_and_infrastructure_errors(self):
        r = aggregate([{'seconds': 1, 'passed': True, 'status': 200, 'metrics': {'cost_usd': .001}},
            {'seconds': 3, 'passed': False, 'status': 429, 'metrics': {'cost_usd': None}},
            {'seconds': 2, 'passed': False, 'status': 200, 'metrics': {'cost_usd': 0}}])
        self.assertEqual(r['latency_median_seconds'], 2)
        self.assertEqual(r['latency_p95_seconds'], 3)
        self.assertEqual(r['infrastructure_errors'], 1)
        self.assertEqual(r['semantic_failures'], 1)
        self.assertEqual(r['unknown_cost_turns'], 1)
