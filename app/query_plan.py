"""One LLM decision defines the entire catalog query for the current turn."""
import json
from app.langchain_tools import CatalogArguments


INTENTS = ('store', 'compare', 'policies', 'identity', 'order', 'return_channel', 'offtopic')

PLANNING = '''
Responda em JSON com intent e catalog_search, conforme o schema fornecido.
Você recebe um registro JSON: current_message é o ÚNICO pedido atual;
previous_messages e previous_context são somente contexto passado.
Tipos citados só nos campos previous_* não são tipos nomeados em current_message.
catalog_search é null quando não há um pedido para consultar produtos neste turno.
Para um pedido de opções, preço, disponibilidade ou continuação de busca, preencha
UMA consulta com TODOS os filtros atuais, interpretados a partir da mensagem e contexto.
Primeiro decida category_scope: named se a mensagem atual nomeia tipos, previous
SOMENTE se há referência às opções anteriores ou resposta à pergunta pendente,
all para uma nova solicitação genérica de instrumentos. Não infira uma referência
às opções anteriores apenas porque existe histórico: ela precisa estar no turno atual.
category_ids contém os IDs reais dos tipos nomeados no pedido atual; não adivinhe.
Com all, envie category_ids=[]. Com previous, o backend mantém a seleção já salva;
se ainda não houve busca nem seleção salva, informe os IDs retomados do histórico.
Escolha uma ou várias categorias pelo significado do pedido atual. Quando o pedido é
genérico por instrumentos, sem especificar tipo nem se referir às opções anteriores,
use category_ids=[] (todas), MESMO que o histórico tenha uma categoria específica.
Se o cliente nomeia outro instrumento, substitua o escopo anterior, não some o antigo.
Se pede dois ou mais tipos juntos, use a união dos IDs em UMA consulta.
Referências às opções anteriores mantêm o escopo; um pedido amplo inicia novo escopo.
Preço é opcional: null remove o limite. Uma resposta livre que dispensa orçamento
deve consultar a categoria conhecida sem exigir preço. Se o teto anterior ainda for
relevante, preserve-o, mas não invente valor para uma preferência vaga por economizar.
Só aplique o preço de pending_budget se a pessoa aceitar essa proposta para o MESMO
escopo; mudança de instrumento não aceita a proposta antiga. Recusa sem nova busca
tem catalog_search=null e dismiss_budget_offer=true, para encerrar a proposta sem
repetir a busca que acabou de ser recusada. Nos demais casos dismiss_budget_offer=false.
query é somente marca ou modelo específico, nunca um tipo de instrumento.
min_price/max_price são strings decimais em reais ou null, sem símbolo monetário.
Não responda ao cliente: apenas classifique e planeje a consulta atual.

Exemplos de interpretação de referência (independentes dos IDs do catálogo):
- Histórico: cliente estava vendo um tipo específico por até 900 reais.
  Mensagem atual: "O que a loja tem de instrumentos por até setecentos reais?"
  Decisão: category_scope="all", category_ids=[], max_price="700.00".
  Não há um tipo de instrumento nomeado na mensagem atual. Não copie o do histórico.
- Mesmo histórico. Mensagem atual: "Quais outras opções desses por até setecentos?"
  Decisão: category_scope="previous", category_ids=[], max_price="700.00".
  Aqui há referência explícita às opções anteriores.
- Mesmo histórico. Mensagem atual nomeia um tipo diferente.
  Decisão: category_scope="named" e apenas os IDs dos tipos nomeados AGORA.
Antes de emitir named, verifique se algum tipo específico de instrumento realmente
aparece no pedido atual. O substantivo genérico instrumentos não nomeia um tipo.
'''


def routing_format(categories: list[dict]) -> dict:
    fields = {
        'category_scope': {'type': 'string', 'enum': ['named', 'previous', 'all'],
            'description': 'named: tipos nomeados na mensagem atual. previous: referência explícita às opções anteriores ou resposta pendente. all: novo pedido genérico de instrumentos, mesmo após conversa sobre uma categoria.'},
        'category_ids': {'type': 'array', 'items': {'type': 'integer', 'enum': [c['category_id'] for c in categories]}},
        'query': {'type': ['string', 'null']},
        'min_price': {'type': ['string', 'null']},
        'max_price': {'type': ['string', 'null']},
        'in_stock': {'type': 'boolean', 'enum': [True]},
    }
    schema = {'type': 'object', 'additionalProperties': False,
              'properties': {'intent': {'type': 'string', 'enum': list(INTENTS)},
                  'dismiss_budget_offer': {'type': 'boolean', 'description': 'True quando o cliente recusa a proposta pendente sem pedir nova busca. Não recriar a proposta.'},
                  'catalog_search': {'anyOf': [{'type': 'null'}, {'type': 'object', 'additionalProperties': False,
                      'properties': fields, 'required': list(fields)}]}},
              'required': ['intent', 'catalog_search', 'dismiss_budget_offer']}
    return {'type': 'json_schema', 'json_schema': {'name': 'store_turn', 'strict': True, 'schema': schema}}


def parse_route(content: str, categories: list[dict], previous: dict | None = None) -> tuple[str, dict | None]:
    # Plain labels remain compatible with scripted tests and legacy transports.
    if content in INTENTS:
        return content, None
    value = json.loads(content)
    if not isinstance(value, dict) or set(value) not in ({'intent', 'catalog_search'}, {'intent', 'catalog_search', 'dismiss_budget_offer'}) or value['intent'] not in INTENTS:
        raise ValueError('Invalid routing decision')
    if 'dismiss_budget_offer' in value and type(value['dismiss_budget_offer']) is not bool:
        raise ValueError('Invalid proposal decision')
    if value.get('dismiss_budget_offer') and value['catalog_search'] is not None:
        raise ValueError('Conflicting proposal decision')
    plan = value['catalog_search']
    if plan is None or value['intent'] != 'store':
        return value['intent'], None
    plan = dict(plan)
    scope = plan.pop('category_scope', 'named')
    if scope == 'all':
        plan['category_ids'] = []
        plan.pop('category_id', None)
    elif scope == 'previous':
        prior = previous or {}
        plan['category_ids'] = ([prior['category_id']] if prior.get('category_id') is not None
                                else prior.get('category_ids', plan.get('category_ids', [])))
        plan.pop('category_id', None)
    elif scope != 'named':
        raise ValueError('Invalid category scope')
    validated = CatalogArguments.model_validate(plan).model_dump(exclude_none=True)
    ids = validated.get('category_ids', [])
    known = {c['category_id'] for c in categories}
    if not set(ids).issubset(known):
        raise ValueError('Unknown category')
    if len(ids) == 1:
        validated.pop('category_ids')
        validated['category_id'] = ids[0]
    else:
        validated['category_ids'] = ids
    return value['intent'], validated
