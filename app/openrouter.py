"""OpenRouter adapter with only free model selection and no paid fallback."""
import json
import os
from typing import Any
import httpx
from app.provider import SYSTEM

class OpenRouter:
    def __init__(self, api_key=None, model=None):
        self.api_key = os.getenv('OPENROUTER_API_KEY', '') if api_key is None else api_key
        self.model = model or os.getenv('OPENROUTER_MODEL', 'openrouter/free')
        self.last_model = None
        self.tool_calls = 0

    def generate(self, contents, tools, *, system=SYSTEM):
        if not self.api_key or not (self.model == 'openrouter/free' or self.model.endswith(':free')):
            raise RuntimeError('Configure uma chave e um modelo gratuito no servidor.')
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
            response = httpx.post('https://openrouter.ai/api/v1/chat/completions',
                headers={'Authorization': f'Bearer {self.api_key}'},
                json={'model': self.model, 'messages': messages,
                      **({'tools': [{'type': 'function', 'function': tool} for tool in tools]} if tools else {}),
                      'provider': {'require_parameters': True}, 'max_tokens': 2048}, timeout=60)
            response.raise_for_status()
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
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            raise RuntimeError('OpenRouter indisponível. Confira configuração e cota ou tente mais tarde.') from None
