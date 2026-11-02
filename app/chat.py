"""Bounded model/tool loop with an explicit read-only registry."""
import csv
import logging
import json
from typing import Any, Protocol
from app.catalog import Catalog
from app.commerce import Promotions
from app.contacts import Contacts
from app.policy_service import get_policy_index

class Provider(Protocol):
    def generate(self, contents: list, tools: list) -> dict: ...

TOOLS = [
    {'name':'store_contacts','description':'Consultar canais oficiais para concluir compra ou falar com a equipe. Extrai telefones/e-mails e divergências do manual; não envia mensagens, não transfere e não cria pedidos.', 'parameters':{'type':'object','properties':{'channel':{'type':'string','enum':['all','remote','store']}}}},
    {'name':'search_promotions','description':'Consultar ofertas ativas atuais e preço promocional calculado, sem acumular PIX. Não confundir promoções periódicas do manual com ofertas ativas.', 'parameters':{'type':'object','properties':{'product_id':{'type':'integer'},'category_id':{'type':'integer'},'max_price':{'type':'string'},'limit':{'type':'integer'},'offset':{'type':'integer'}}}},
    {'name':'compare_products','description':'Comparar 2 a 4 produtos pelo ID, relendo preços de tabela e especificações atuais; ofertas precisam de search_promotions. Calcula diferença acima do orçamento em Python.', 'parameters':{'type':'object','properties':{'product_ids':{'type':'array','items':{'type':'integer'}},'budget':{'type':'string'}},'required':['product_ids']}},
    {'name': 'search_policies',
     'description': 'Buscar evidências no manual da loja: horários de funcionamento/abertura, contatos, endereço, pagamentos, parcelamento, PIX, trocas, devoluções, garantia, frete e políticas. Obrigatória antes de responder fatos ou regras da loja. Não consulta preços, estoque ou pedidos individuais.',
     'parameters': {'type': 'object', 'properties': {
         'query': {'type': 'string', 'description': 'Pergunta completa em português, preservando modalidade online/presencial, cidade e condições já informadas. Até 500 caracteres.'}}, 'required': ['query']}},
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
    def __init__(self, provider: Provider, catalog: Catalog, state: dict | None=None):
        self.provider = provider
        self.catalog = catalog
        self.products: dict[int, dict] = {}
        self.sources: dict[str, dict] = {}
        self.contacts: dict[str, dict] = {}
        self.preferences = dict((state or {}).get('preferences', {}))
        self.recent_product_ids = list((state or {}).get('product_ids', []))[:16]

    def dispatch(self, name: str, args: dict) -> dict:
        if name == 'store_contacts':
            if set(args)-{'channel'}:return {'status':'invalid','items':[]}
            result=Contacts(self.catalog.directory).lookup(args.get('channel','all'))
            if result['status']=='found':
                for source in result['items']:self.sources[source['id']]=source
                for contact in result['channels']:self.contacts[contact['kind']]=contact
            return result
        if name == 'search_promotions':
            if set(args)-{'product_id','category_id','max_price','limit','offset'}:
                return {'status':'invalid','items':[]}
            result=Promotions(self.catalog.directory).search(**args)
            if result['status']=='found':
                for product in result['items']:self.products[product['product_id']]=product
            return result
        if name == 'compare_products':
            if set(args)-{'product_ids','budget'} or 'product_ids' not in args:
                return {'status':'invalid','items':[]}
            result=self.catalog.compare(args['product_ids'],args.get('budget',self.preferences.get('max_price')))
            if result['status']=='found':
                for product in result['items']:
                    self.products[product['product_id']]=product
            return result
        if name == 'search_policies':
            if set(args) != {'query'} or not isinstance(args['query'], str) or not args['query'].strip() or len(args['query']) > 500:
                return {'status': 'invalid', 'items': [], 'warnings': []}
            try:
                result = get_policy_index(self.catalog.directory).search(args['query'])
                if result['status'] == 'found':
                    for source in result['items']:
                        self.sources[source['id']] = source
                return result
            except Exception as exc:
                logging.getLogger(__name__).error('Policy retrieval failed (%s)', type(exc).__name__)
                return {'status': 'error', 'items': [], 'warnings': []}
        if name == 'search_catalog':
            try:
                result = self.catalog.search(**args)
                if result['status'] == 'found':
                    self.preferences.update({key:value for key,value in args.items() if key in {'category_id','min_price','max_price','in_stock','status'}})
                    for product in result['items']:
                        self.products[product['product_id']] = product
                return result
            except TypeError:
                return {'status': 'invalid', 'items': []}
        if name == 'list_categories' and not args:
            try:
                with (self.catalog.directory / 'categories.csv').open(encoding='utf-8-sig') as stream:
                    return {'status': 'found', 'items': list(csv.DictReader(stream))[:30]}
            except OSError:
                return {'status': 'error', 'items': []}
        return {'status': 'invalid', 'items': []}

    def reply(self, message: str, history: list | None=None) -> str:
        if not message.strip() or len(message) > 2000:
            raise ValueError('Envie uma mensagem de 1 a 2000 caracteres.')
        contents: list[dict[str, Any]] = list(history or [])
        if self.preferences or self.recent_product_ids:
            contents.append({'role':'user','parts':[{'text':'Contexto estruturado de preferências (não substitui consulta atual): '+json.dumps({'preferences':self.preferences,'product_ids':self.recent_product_ids},ensure_ascii=False)}]})
        contents.append({'role':'user','parts':[{'text':message}]})
        for _ in range(4):
            if len(json.dumps(contents,ensure_ascii=False))>40000:
                raise RuntimeError('Limite de contexto atingido. Inicie outro assunto.')
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
