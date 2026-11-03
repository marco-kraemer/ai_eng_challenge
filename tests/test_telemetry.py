import concurrent.futures
import json
import os
import unittest
from unittest.mock import patch

from app.telemetry import turn, span, current_turn


class TelemetryTests(unittest.TestCase):
    def test_http_response_correlates_sanitized_faq_trace(self):
        from fastapi.testclient import TestClient
        from app.web import app
        with patch('app.telemetry.export_runs') as export, TestClient(app) as client:
            response = client.post('/api/chat', json={'message': 'Qual é o endereço da loja?'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['trace_id'], export.call_args.args[0][0]['id'])
        self.assertIn('faq', [run['name'] for run in export.call_args.args[0]])
    def test_trace_hides_free_text_and_exports_hierarchy(self):
        with patch.dict(os.environ, {'LANGSMITH_API_KEY': 'test-only'}), patch('app.telemetry.export_runs') as export:
            with turn('private-session-token') as trace:
                with span('search_catalog', 'tool', category_id=5, max_price='600', query='secret@example.com', api_key='sk-secret'):
                    pass
            runs = export.call_args.args[0]
        serialized = json.dumps(runs, default=str)
        for secret in ('private-session-token', 'secret@example.com', 'sk-secret'):
            self.assertNotIn(secret, serialized)
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[1]['parent_run_id'], runs[0]['id'])
        self.assertEqual(runs[1]['extra']['metadata']['category_id'], 5)
        self.assertEqual(runs[0]['id'], trace.id)
        self.assertIsNone(current_turn())

    def test_export_failure_never_changes_response(self):
        with patch('app.telemetry.export_runs', side_effect=RuntimeError('private-secret')):
            with turn('session') as trace:
                with span('classify'):
                    pass
        self.assertEqual(trace.status, 'ok')

    def test_concurrent_contexts_are_isolated(self):
        def task(value):
            with turn(value) as trace:
                with span('classify'):
                    self.assertIs(current_turn(), trace)
                return trace.id, trace.records[0]['extra']['metadata']['thread_id']
        with patch('app.telemetry.export_runs'), concurrent.futures.ThreadPoolExecutor(2) as pool:
            rows = list(pool.map(task, ['first', 'second']))
        self.assertNotEqual(rows[0], rows[1])
