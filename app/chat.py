"""Bounded model/tool loop with an explicit read-only registry."""
import csv
from typing import Any, Protocol
from app.catalog import Catalog

class Provider(Protocol):
    def generate(self, contents: list, tools: list) -> dict: ...

TOOLS = [
    {'name': 'search_catalog', 'description': 'Consultar produtos atuais com filtros e paginação.',
     'parameters': {'type': 'object', 'properties': {
         'category_id': {'type': 'integer'}, 'min_price': {'type': 'string'},
         'max_price': {'type': 'string'}, 'in_stock': {'type': 'boolean'},
         'status': {'type': 'string', 'enum': ['active', 'inactive']},
         'limit': {'type': 'integer'}, 'offset': {'type': 'integer'}}}},
    {'name': 'list_categories', 'description': 'Listar categorias e seus identificadores.',
     'parameters': {'type': 'object', 'properties': {}}},
]

class Chat:
    def __init__(self, provider: Provider, catalog: Catalog):
        self.provider = provider
        self.catalog = catalog

    def dispatch(self, name: str, args: dict) -> dict:
        if name == 'search_catalog':
            try:
                return self.catalog.search(**args)
            except TypeError:
                return {'status': 'invalid', 'items': []}
        if name == 'list_categories' and not args:
            try:
                with (self.catalog.directory / 'categories.csv').open(encoding='utf-8-sig') as stream:
                    return {'status': 'found', 'items': list(csv.DictReader(stream))[:30]}
            except OSError:
                return {'status': 'error', 'items': []}
        return {'status': 'invalid', 'items': []}

    def reply(self, message: str) -> str:
        if not message.strip() or len(message) > 2000:
            raise ValueError('Envie uma mensagem de 1 a 2000 caracteres.')
        contents: list[dict[str, Any]] = [{'role': 'user', 'parts': [{'text': message}]}]
        for _ in range(4):
            content = self.provider.generate(contents, TOOLS)
            calls = [p['functionCall'] for p in content.get('parts', []) if 'functionCall' in p]
            if not calls:
                return '\n'.join(p['text'] for p in content.get('parts', []) if 'text' in p) or 'Não consegui responder. Tente novamente.'
            if len(calls) > 3:
                raise RuntimeError('Limite de consultas atingido.')
            contents.append(dict(content, role='model'))
            results = []
            for call in calls:
                args = call.get('args', {})
                result = self.dispatch(call.get('name', ''), args) if isinstance(args, dict) else {'status': 'invalid'}
                results.append({'functionResponse': {'name': call.get('name', ''), 'response': result}})
            contents.append({'role': 'user', 'parts': results})
        raise RuntimeError('Limite de consultas atingido. Refine a pergunta.')
