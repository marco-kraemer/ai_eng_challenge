from contextlib import contextmanager
import json
import unittest
from unittest.mock import patch
import httpx
from app.openai_provider import OpenAI
from app.telemetry import event_sink


class TransportStreamTests(unittest.TestCase):
    def test_real_provider_deltas_arrive_before_completion_with_usage(self):
        events = []
        @contextmanager
        def stream(*args, **kwargs):
            self.assertTrue(kwargs['json']['stream'])
            response = httpx.Response(200, request=httpx.Request('POST', OpenAI.endpoint))
            def lines():
                yield 'data: ' + json.dumps({'model': 'gpt-4.1-mini', 'choices': [{'delta': {'content': 'Olá '}}]})
                self.assertEqual(events[-1], {'type': 'delta', 'text': 'Olá '})
                yield 'data: ' + json.dumps({'choices': [{'delta': {'content': 'amigo.'}, 'finish_reason': 'stop'}]})
                yield 'data: ' + json.dumps({'choices': [], 'usage': {'prompt_tokens': 20, 'completion_tokens': 5}})
                yield 'data: [DONE]'
            response.iter_lines = lines
            yield response
        with event_sink(events.append), patch('httpx.stream', side_effect=stream), patch('httpx.post', side_effect=AssertionError('Must use provider streaming')):
            result = OpenAI(api_key='test').generate([], [])
        self.assertEqual(result['parts'][0]['text'], 'Olá amigo.')
        self.assertEqual(result['_usage']['prompt_tokens'], 20)

    def test_structured_planner_never_streams_to_customer(self):
        response = httpx.Response(200, json={'choices': [{'message': {'content': '{"intent":"store"}'}}]}, request=httpx.Request('POST', OpenAI.endpoint))
        events = []
        with event_sink(events.append), patch('httpx.stream') as stream, patch('httpx.post', return_value=response):
            OpenAI(api_key='test').generate([], [], response_format={'type': 'json_object'})
        stream.assert_not_called()
        self.assertEqual(events, [])
