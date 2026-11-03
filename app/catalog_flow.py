"""Shared deterministic catalog flow for buttons and conversational confirmations."""
from decimal import Decimal, InvalidOperation
from app.catalog import Catalog
from app.actions import next_actions

INSTRUMENT_ART={1:'guitarra',2:'baixo',3:'bateria',4:'teclado',5:'violao',6:'saxofone',7:'trompete',8:'violino',9:'ukulele'}
CATEGORY_LABELS={6:'Sopros de madeira',7:'Sopros de metal'}


def catalog_reply(catalog: Catalog, category_id: int | None, max_price: str | None, *, category_ids: list[int] | None = None, limit: int = 4, offset: int = 0):
    categories=catalog.categories()
    if categories['status']=='error':raise RuntimeError('Não foi possível consultar os instrumentos agora.')
    if category_id is not None and category_ids is not None:
        raise ValueError('Escolha uma categoria ou uma lista de categorias.')
    ids = [category_id] if category_id is not None else list(category_ids or [])
    known = {item['category_id']: item for item in categories['items']}
    if any(type(i) is not int or i not in known for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Escolha instrumentos da lista.')
    if set(ids) == set(known):
        ids = []
    selected = [known[i] for i in ids]
    category = selected[0] if len(selected) == 1 else None
    names = [CATEGORY_LABELS.get(item['category_id'], item['name']) for item in selected]
    label = (' e '.join(names) if len(names) <= 2 else ', '.join(names[:-1]) + ' e ' + names[-1]) if names else 'Todos os instrumentos'
    scope = {'category_id': ids[0]} if len(ids) == 1 else {'category_ids': ids}
    try:
        ceiling=Decimal(max_price) if max_price is not None else None
        if ceiling is not None:
            if not ceiling.is_finite() or not 0<ceiling<=10000000:raise ValueError('Invalid budget')
            ceiling=ceiling.quantize(Decimal('0.01'))
            if ceiling<=0:raise ValueError('Invalid budget')
    except (InvalidOperation,ValueError):
        raise ValueError('Informe um valor válido ou escolha a opção sem limite de preço.') from None
    filters={**scope,'in_stock':True,'status':'active'}
    if ceiling is not None:filters['max_price']=str(ceiling)
    result=catalog.search(**filters,limit=limit,offset=offset)
    if result['status']=='error':raise RuntimeError('Não foi possível consultar os produtos agora. Tente novamente.')
    if result['status']=='invalid':raise ValueError('Confira o instrumento e o valor escolhidos.')
    name=label.lower() if ids else 'instrumentos'
    price=('R$ '+format(ceiling,',.2f').replace(',','_').replace('.',',').replace('_','.')) if ceiling is not None else None
    question=f'Quero ver {name}'+(' até '+price if price else ', sem um limite de preço definido')+'.'
    answer=('Estas são algumas opções de '+name+(' até '+price if price else '')+'.') if result['items'] else 'Não encontrei opções em estoque para essa busca. Você pode mudar o valor ou escolher outro instrumento.'
    response={'message':answer,'products':result['items'],'sources':[],'contacts':[]}
    response['search']={'category_id':ids[0] if len(ids) == 1 else None, 'category_ids': ids,
                        'categories': [{'category_id': item['category_id'], 'name': item['name'], 'label': CATEGORY_LABELS.get(item['category_id'], item['name']), 'illustration':'/assets/instruments.svg#'+INSTRUMENT_ART.get(item['category_id'],'generico')} for item in selected],
                        'name':category['name'] if category else label, 'label':label,
                        'illustration':'/assets/instruments.svg#'+(INSTRUMENT_ART.get(ids[0],'generico') if len(ids) == 1 else 'generico'),
                        'max_price':str(ceiling) if ceiling is not None else None}
    response['actions']=next_actions(response)
    if not result['items']:
        response['actions']=[]
        alternative=catalog.cheapest_available(**scope)
        if alternative['status']=='error':raise RuntimeError('Não foi possível consultar os produtos agora. Tente novamente.')
        if alternative['items'] and ceiling is not None:
            minimum=alternative['items'][0]['price_brl']
            display='R$ '+format(Decimal(minimum),',.2f').replace(',','_').replace('.',',').replace('_','.')
            answer=f'Não encontrei {name} em estoque até {price}. O menor preço disponível é {display}. Quer ver opções até esse valor?'
            response['recovery']={'reason':'budget','price_brl':minimum}
            response['actions'].insert(0,{'id':'raise_budget','label':'Ver opções até '+display,'kind':'catalog_search',
                'selection':{**scope,'max_price':minimum}})
        else:
            answer=f'Não há opções de {name} em estoque no momento. Quer escolher outro instrumento?'
            response['recovery']={'reason':'unavailable'}
        response['message']=answer

    response['actions'].insert(0,{'id':'change_search','label':'Alterar busca','kind':'instrument_picker'})
    state={'topic':'products','preferences':filters,'product_ids':[p['product_id'] for p in result['items']], 'allowed_actions':[action['id'] for action in response['actions'] if action['id'] in ('compare','cheaper','contact','policy_details','categories','hours')]}
    state['pending_budget']={**scope,'max_price':response['recovery']['price_brl']} if response.get('recovery',{}).get('reason')=='budget' else {}
    return response, question, state
