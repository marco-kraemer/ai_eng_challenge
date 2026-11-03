"""Shared bounded Chat Completions transport; provider configuration is explicit."""
import json
import logging
from typing import Any
import httpx
from app.provider import SYSTEM
from app.telemetry import streaming_enabled, emit, first_token

class ChatCompletionsTransport:
    endpoint: str
    provider_name: str

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.last_model = None
        self.tool_calls = 0

    def validate(self):
        raise NotImplementedError

    def request_body(self, messages, tools):
        return {'model': self.model, 'messages': messages,
                **({'tools': [{'type': 'function', 'function': tool} for tool in tools]} if tools else {})}

    def generate(self, contents, tools, *, system=SYSTEM, response_format=None):
        self.validate()
        messages: list[dict[str, Any]] = [{'role': 'system', 'content': system}]
        pending_ids: list[str] = []
        for content in contents:
            if '_openrouter_message' in content:
                native = content['_openrouter_message']
                messages.append(native)
                pending_ids = [call['id'] for call in native.get('tool_calls', [])]
                continue
            for part in content.get('parts', []):
                if 'text' in part:
                    messages.append({'role': 'assistant' if content.get('role') in ('model','assistant') else 'user', 'content': part['text']})
                elif 'functionResponse' in part:
                    if not pending_ids:
                        raise RuntimeError('Resposta de ferramenta sem chamada correspondente.')
                    messages.append({'role': 'tool', 'tool_call_id': pending_ids.pop(0),
                                     'content': json.dumps(part['functionResponse']['response'], ensure_ascii=False)})
        try:
            for attempt in range(2):
                try:
                    body = self.request_body(messages, tools)
                    if response_format is not None:
                        body['response_format'] = response_format
                    if streaming_enabled() and response_format is None:
                        response = self.stream_completion(body)
                    else:
                        response = httpx.post(self.endpoint,
                            headers={'Authorization': f'Bearer {self.api_key}'},
                            json=body, timeout=60)
                    if response.status_code==429:
                        logging.getLogger(type(self).__module__).warning('%s request failed (429)', self.provider_name)
                        raise RuntimeError('Limite de uso do modelo atingido. Aguarde e tente mais tarde.')
                    if response.status_code in (502,503,504) and attempt==0:
                        continue
                    response.raise_for_status()
                    break
                except (httpx.TimeoutException,httpx.ConnectError):
                    if streaming_enabled():
                        emit('answer_reset')
                    if attempt==1:raise
            payload = response.json()
            native = payload['choices'][0]['message']
            self.last_model = payload.get('model')
            parts = []
            for call in native.get('tool_calls', []):
                args = json.loads(call['function']['arguments'])
                if not isinstance(args, dict):
                    raise ValueError('Invalid arguments')
                parts.append({'functionCall': {'name': call['function']['name'], 'args': args}})
                self.tool_calls += 1
            if native.get('content'):
                parts.append({'text': native['content']})
            return {'parts': parts, '_openrouter_message': native, '_usage': payload.get('usage'), '_model': payload.get('model')}
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            detail=exc.response.status_code if isinstance(exc,httpx.HTTPStatusError) else type(exc).__name__
            logging.getLogger(type(self).__module__).warning('%s request failed (%s)', self.provider_name, detail)
            raise RuntimeError(f'{self.provider_name} indisponível. Confira configuração e cota ou tente mais tarde.') from None

    def stream_completion(self, body):
        native: dict = {'role': 'assistant', 'content': ''}
        calls: dict = {}
        model = None; usage = None; finished = False; emitted = False
        with httpx.stream('POST', self.endpoint, headers={'Authorization': f'Bearer {self.api_key}'},
                json={**body, 'stream': True, 'stream_options': {'include_usage': True}}, timeout=60) as response:
            if response.status_code != 200:
                response.read()
                return response
            for line in response.iter_lines():
                if not line.startswith('data:'):
                    continue
                data = line[5:].strip()
                if data == '[DONE]':
                    break
                chunk = json.loads(data)
                model = chunk.get('model') or model
                usage = chunk.get('usage') or usage
                for choice in chunk.get('choices', []):
                    reason = choice.get('finish_reason')
                    if reason in ('length', 'content_filter'):
                        raise ValueError('Incomplete generation')
                    finished = finished or reason in ('stop', 'tool_calls')
                    delta = choice.get('delta') or {}
                    for part in delta.get('tool_calls', []):
                        if emitted:
                            emit('answer_reset'); emitted = False
                        call = calls.setdefault(part['index'], {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}})
                        call['id'] += part.get('id') or ''
                        call['function']['name'] += (part.get('function') or {}).get('name') or ''
                        call['function']['arguments'] += (part.get('function') or {}).get('arguments') or ''
                    text = delta.get('content')
                    if isinstance(text, str):
                        native['content'] += text
                        if not calls and text:
                            first_token(); emit('delta', text=text); emitted = True
            if not finished:
                raise ValueError('Incomplete stream')
        if calls:
            native['tool_calls'] = [calls[i] for i in sorted(calls)]
        return httpx.Response(200, json={'model': model, 'usage': usage, 'choices': [{'message': native}]},
            request=httpx.Request('POST', self.endpoint))
