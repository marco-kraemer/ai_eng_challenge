"""Bounded model/tool loop with an explicit read-only registry."""
import csv
import logging
import json
from typing import Protocol
from app.catalog import Catalog
from app.catalog_flow import catalog_reply
from app.commerce import Promotions
from app.contacts import Contacts
from app.policy_service import get_policy_index
from app.langchain_model import StoreChatModel, history_messages
from app.langchain_tools import build_tools
from app.agent_graph import build_agent_graph
from app.telemetry import span, safe_metadata
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from app.provider import SYSTEM

class Provider(Protocol):
    def generate(self, contents: list, tools: list) -> dict: ...

TOOLS = [
    {'name': 'dismiss_budget_offer', 'description': 'Registrar que o cliente recusou a proposta pendente de aumentar o orçamento, preservando o limite anterior. Não consulta produtos nem muda preços.', 'parameters': {'type': 'object', 'properties': {}}},
    {'name':'store_contacts','description':'Consultar canais oficiais para concluir compra ou falar com a equipe. Extrai telefones/e-mails e divergências do manual; não envia mensagens, não transfere e não cria pedidos.', 'parameters':{'type':'object','properties':{'channel':{'type':'string','enum':['all','remote','store']}}}},
    {'name':'search_promotions','description':'Consultar ofertas ativas atuais e preço promocional calculado, sem acumular PIX. Não confundir promoções periódicas do manual com ofertas ativas.', 'parameters':{'type':'object','properties':{'product_id':{'type':'integer'},'category_id':{'type':'integer'},'max_price':{'type':'string'},'limit':{'type':'integer'},'offset':{'type':'integer'}}}},
    {'name':'compare_products','description':'Comparar 2 a 4 produtos pelo ID, relendo preços de tabela e especificações atuais; ofertas precisam de search_promotions. Calcula diferença acima do orçamento em Python.', 'parameters':{'type':'object','properties':{'product_ids':{'type':'array','items':{'type':'integer'}},'budget':{'type':'string'}},'required':['product_ids']}},
    {'name': 'search_policies',
     'description': 'Buscar evidências no manual da loja: horários de funcionamento/abertura, contatos, endereço, pagamentos, parcelamento, PIX, trocas, devoluções, garantia, frete e políticas. Obrigatória antes de responder fatos ou regras da loja. Não consulta preços, estoque ou pedidos individuais.',
     'parameters': {'type': 'object', 'properties': {
         'query': {'type': 'string', 'description': 'Pergunta completa em português, preservando modalidade online/presencial, cidade e condições já informadas. Até 500 caracteres.'}}, 'required': ['query']}},
    {'name': 'search_catalog', 'description': 'Consultar produtos atuais por nome, marca ou modelo (query) e filtros estruturados. Cada consulta define TODOS os filtros atuais: omitir min_price/max_price significa buscar SEM limite de preço e remover limites anteriores. Orçamento é opcional. Interprete o pedido com o histórico: se a pessoa não quer definir preço, consulte o instrumento já mencionado sem limites. Se aceitar uma oferta de orçamento pendente, use a categoria e o valor dessa oferta; se mudar de ideia, use a nova intenção. Ao citar um modelo específico, use query. Só informe produtos encontrados.',
     'parameters': {'type': 'object', 'properties': {
         'query': {'type': 'string', 'minLength': 1, 'maxLength': 200, 'description': 'Palavras do nome, marca ou modelo específico, por exemplo Takamine GD20. Não usar para tipo de instrumento: use category_id para categorias.'},
         'category_id': {'type': 'integer', 'description': 'ID da categoria de instrumento. Consulte list_categories se o ID ainda não foi informado pelas ferramentas ou pelo contexto; não adivinhe.'}, 'min_price': {'type': 'string'},
         'max_price': {'type': 'string'}, 'in_stock': {'type': 'boolean'},
         'status': {'type': 'string', 'enum': ['active', 'inactive']},
         'limit': {'type': 'integer'}, 'offset': {'type': 'integer'}}}},
    {'name': 'list_categories', 'description': 'Consultar categorias de instrumentos e seus IDs reais. Use antes de search_catalog quando o cliente indica um tipo de instrumento e você ainda não conhece o category_id. Escolha a categoria pelo significado do pedido, inclusive no histórico.',
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
        self.pending_budget = dict((state or {}).get('pending_budget') or {})
        self.catalog_response: dict = {}
        self.model = StoreChatModel(transport=provider, cache=False)
        self.tools = build_tools(self.observed_dispatch, TOOLS)
        self.graph = build_agent_graph(self.model, self.tools)

    def prepare_catalog_search(self, args: dict) -> dict:
        result = self.tools['search_catalog'].invoke(args)
        # The structured LLM plan owns this turn's scope. The answering model can
        # compare or retrieve policies, but cannot replace this search with another.
        self.prevent_catalog_replacement()
        return result

    def prevent_catalog_replacement(self):
        self.graph = build_agent_graph(self.model, {name: tool for name, tool in self.tools.items() if name != 'search_catalog'})

    def observed_dispatch(self, name: str, args: dict) -> dict:
        with span(name, 'retriever' if name == 'search_policies' else 'tool', **safe_metadata(args)) as record:
            result = self.dispatch(name, args)
            if record:
                record['extra']['metadata'].update(safe_metadata({'status': result.get('status'),
                    'product_count': len(result.get('items', []))}))
            return result

    def dispatch(self, name: str, args: dict) -> dict:
        if name == 'dismiss_budget_offer':
            if args:
                return {'status': 'invalid', 'items': []}
            self.pending_budget = {}
            return {'status': 'updated', 'preferences': dict(self.preferences), 'pending_budget': {}}
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
                # The LLM chooses filters. Share UI recovery/rendering for simple category searches.
                simple = (not set(args) - {'category_id', 'category_ids', 'max_price', 'in_stock', 'status', 'limit', 'offset'}
                          and args.get('in_stock', True) is True and args.get('status', 'active') == 'active')
                if simple:
                    response, _, context = catalog_reply(self.catalog, args.get('category_id'), args.get('max_price'),
                        category_ids=args.get('category_ids'), limit=args.get('limit', 4), offset=args.get('offset', 0))
                    result = {'status': 'found' if response['products'] else 'not_found', 'items': response['products'], 'search': response['search']}
                    self.catalog_response = response
                    self.preferences = dict(context['preferences'])
                    self.pending_budget = dict(context['pending_budget'])
                    if response.get('recovery'):
                        result['recovery'] = response['recovery']
                else:
                    result = self.catalog.search(**args)
                if result['status'] in ('found', 'not_found'):
                    if not simple:
                        self.preferences = {key:value for key,value in args.items() if key in {'category_id','category_ids','query','min_price','max_price','in_stock','status'}}
                        self.pending_budget = {}
                        self.catalog_response = {}
                    self.products = {}
                    for product in result['items']:
                        self.products[product['product_id']] = product
                    self.recent_product_ids = list(self.products)
                return result
            except (TypeError, ValueError):
                return {'status': 'invalid', 'items': []}
        if name == 'list_categories' and not args:
            try:
                with (self.catalog.directory / 'categories.csv').open(encoding='utf-8-sig') as stream:
                    return {'status': 'found', 'items': list(csv.DictReader(stream))[:30]}
            except OSError:
                return {'status': 'error', 'items': []}
        return {'status': 'invalid', 'items': []}

    def reply(self, message: str, history: list | None=None, *, policy_result: dict | None=None, policy_query: str="", initial_results: list[dict] | None=None) -> str:
        if not message.strip() or len(message) > 2000:
            raise ValueError('Envie uma mensagem de 1 a 2000 caracteres.')
        system = SYSTEM
        if policy_result and policy_result.get('warnings'):
            system += ('\nA consulta atual sinalizou divergência nas fontes. Comece explicando essa incerteza. '
                       'Não transforme condições conflitantes em uma regra única, exceção ou garantia. '
                       'Apresente separadamente o que cada trecho diz e peça confirmação à equipe. '
                       'Não afirme um mínimo, juros ou prazo definitivo no ponto divergente.')
        if any(product.get('warnings') for evidence in (initial_results or [])
               for product in evidence.get('result', {}).get('items', [])):
            system += ('\nHá conflito objetivo na ficha de produto consultada. Comece pelo aviso '
                       'e recomende confirmar ficha/modelo com a equipe. Não venda características '
                       'divergentes como certas nem acrescente benefícios não declarados na fonte.')
        messages = [SystemMessage(content=system), *history_messages(history or [])]
        # Supply the current taxonomy on every turn, including after a UI selection.
        # Category interpretation belongs to the LLM; IDs and names come from the CSV.
        taxonomy = self.catalog.categories()
        if taxonomy['status'] == 'found':
            messages.append(HumanMessage(content='Categorias atuais do catálogo (dados de referência, não preferências do cliente): '
                + json.dumps(taxonomy['items'], ensure_ascii=False)))
        if self.preferences or self.recent_product_ids or self.pending_budget:
            context = {'preferences': self.preferences, 'product_ids': self.recent_product_ids}
            if self.pending_budget:
                context['pending_budget'] = self.pending_budget
            messages.append(HumanMessage(content='Contexto estruturado de preferências (não substitui consulta atual): '+json.dumps(context,ensure_ascii=False)))
        messages.append(HumanMessage(content=message))
        initial_results = list(initial_results or [])
        if policy_result is not None:
            initial_results.append({'name': 'search_policies', 'args': {'query': policy_query}, 'result': policy_result})
        for position, evidence in enumerate(initial_results):
            # Prior deterministic graph steps are tool data, never system instructions.
            call_id = f'graph-evidence-{position}'
            messages.extend([
                AIMessage(content='', tool_calls=[{'name': evidence['name'], 'args': evidence['args'], 'id': call_id}]),
                ToolMessage(content=json.dumps(evidence['result'], ensure_ascii=False), tool_call_id=call_id, name=evidence['name'])])
        result = self.graph.invoke({'messages': messages, 'rounds': 0, 'answer': ''},
                                   config={'recursion_limit': 12, 'callbacks': []})
        return result['answer']
