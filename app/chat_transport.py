"""Shared bounded Chat Completions transport; provider configuration is explicit."""
import json
import logging
from typing import Any
import httpx
from app.provider import SYSTEM

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

    def generate(self, contents, tools, *, system=SYSTEM):
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
                    response = httpx.post(self.endpoint,
                        headers={'Authorization': f'Bearer {self.api_key}'},
                        json=self.request_body(messages, tools), timeout=60)
                    if response.status_code==429:
                        logging.getLogger(type(self).__module__).warning('%s request failed (429)', self.provider_name)
                        raise RuntimeError('Limite de uso do modelo atingido. Aguarde e tente mais tarde.')
                    if response.status_code in (502,503,504) and attempt==0:
                        continue
                    response.raise_for_status()
                    break
                except (httpx.TimeoutException,httpx.ConnectError):
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
            return {'parts': parts, '_openrouter_message': native}
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            detail=exc.response.status_code if isinstance(exc,httpx.HTTPStatusError) else type(exc).__name__
            logging.getLogger(type(self).__module__).warning('%s request failed (%s)', self.provider_name, detail)
            raise RuntimeError(f'{self.provider_name} indisponível. Confira configuração e cota ou tente mais tarde.') from None
