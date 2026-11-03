"""Shared deterministic catalog flow for buttons and conversational confirmations."""
from decimal import Decimal, InvalidOperation
from app.catalog import Catalog
from app.actions import next_actions

INSTRUMENT_ART={1:'guitarra',2:'baixo',3:'bateria',4:'teclado',5:'violao',6:'saxofone',7:'trompete',8:'violino',9:'ukulele'}
CATEGORY_LABELS={6:'Sopros de madeira',7:'Sopros de metal'}


def catalog_reply(catalog: Catalog, category_id: int, max_price: str | None):
    categories=catalog.categories()
    if categories['status']=='error':raise RuntimeError('Não foi possível consultar os instrumentos agora.')
    category=next((item for item in categories['items'] if item['category_id']==category_id),None)
    if category is None:raise ValueError('Escolha um instrumento da lista.')
    try:
        ceiling=Decimal(max_price) if max_price is not None else None
        if ceiling is not None:
            if not ceiling.is_finite() or not 0<ceiling<=10000000:raise ValueError('Invalid budget')
            ceiling=ceiling.quantize(Decimal('0.01'))
            if ceiling<=0:raise ValueError('Invalid budget')
    except (InvalidOperation,ValueError):
        raise ValueError('Informe um valor válido ou escolha a opção sem limite de preço.') from None
    filters={'category_id':category_id,'in_stock':True,'status':'active'}
    if ceiling is not None:filters['max_price']=str(ceiling)
    result=catalog.search(**filters,limit=4)
    if result['status']=='error':raise RuntimeError('Não foi possível consultar os produtos agora. Tente novamente.')
    if result['status']=='invalid':raise ValueError('Confira o instrumento e o valor escolhidos.')
    name=category['name'].lower()
    price=('R$ '+format(ceiling,',.2f').replace(',','_').replace('.',',').replace('_','.')) if ceiling is not None else None
    question=f'Quero ver {name}'+(' até '+price if price else ', sem um limite de preço definido')+'.'
    answer=('Estas são algumas opções de '+name+(' até '+price if price else '')+'.') if result['items'] else 'Não encontrei opções em estoque para essa busca. Você pode mudar o valor ou escolher outro instrumento.'
    response={'message':answer,'products':result['items'],'sources':[],'contacts':[]}
    response['search']={'category_id':category_id, 'name':category['name'],
                        'label':CATEGORY_LABELS.get(category_id, category['name']),
                        'illustration':'/assets/instruments.svg#'+INSTRUMENT_ART.get(category_id,'generico'),
                        'max_price':str(ceiling) if ceiling is not None else None}
    response['actions']=next_actions(response)
    if not result['items']:
        response['actions']=[]
        alternative=catalog.cheapest_available(category_id)
        if alternative['status']=='error':raise RuntimeError('Não foi possível consultar os produtos agora. Tente novamente.')
        if alternative['items'] and ceiling is not None:
            minimum=alternative['items'][0]['price_brl']
            display='R$ '+format(Decimal(minimum),',.2f').replace(',','_').replace('.',',').replace('_','.')
            answer=f'Não encontrei {name} em estoque até {price}. O menor preço disponível é {display}. Quer ver opções até esse valor?'
            response['recovery']={'reason':'budget','price_brl':minimum}
            response['actions'].insert(0,{'id':'raise_budget','label':'Ver opções até '+display,'kind':'catalog_search',
                'selection':{'category_id':category_id,'max_price':minimum}})
        else:
            answer=f'Não há opções de {name} em estoque no momento. Quer escolher outro instrumento?'
            response['recovery']={'reason':'unavailable'}
        response['message']=answer

    response['actions'].insert(0,{'id':'change_search','label':'Alterar busca','kind':'instrument_picker'})
    state={'topic':'products','preferences':filters,'product_ids':[p['product_id'] for p in result['items']], 'allowed_actions':[action['id'] for action in response['actions'] if action['id'] in ('compare','cheaper','contact','policy_details','categories','hours')]}
    state['pending_budget']={'category_id':category_id,'max_price':response['recovery']['price_brl']} if response.get('recovery',{}).get('reason')=='budget' else {}
    return response, question, state
