from pathlib import Path
import threading
from decimal import Decimal, InvalidOperation
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse, FileResponse
from pydantic import BaseModel, Field
from app.catalog import Catalog
from app.orders import Orders
from app.limits import RateLimiter, BodyLimitMiddleware
from app.conversations import ConversationStore
from app.actions import next_actions, resolve_action
from app.assistant import StoreAssistant
from app.openrouter import OpenRouter
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
app = FastAPI(title='Empório da Música')
conversations = ConversationStore()
rate_limiter=RateLimiter()
CHAT_RATE=20
ORDER_RATE=5
chat_slots=threading.BoundedSemaphore(4)
app.add_middleware(BodyLimitMiddleware,max_bytes=16000)

@app.middleware('http')
async def protect_requests(request,call_next):
    limit=CHAT_RATE if request.url.path in ('/api/chat','/api/catalog/search') else ORDER_RATE if request.url.path=='/api/orders/verify' else None
    if request.method=='POST' and limit is not None:
        actor=request.client.host if request.client else 'unknown'
        allowed,retry=rate_limiter.allow(request.url.path+':'+actor,limit)
        if not allowed:
            return JSONResponse({'detail':'Limite de consultas atingido. Aguarde um pouco antes de tentar novamente.'},status_code=429,headers={'Retry-After':str(retry)})
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    return response

class Message(BaseModel):
    message: str = Field(default='', max_length=2000)
    action_id: str | None = Field(default=None,max_length=32)
    conversation_id: str | None = Field(default=None,max_length=64)

@app.get('/', response_class=HTMLResponse)
def index():
    return (ROOT / 'app/static/index.html').read_text(encoding='utf-8')

@app.post('/api/chat')
def reply(message: Message):
    token=conversations.open(message.conversation_id)
    busy=conversations.acquire(token)
    if busy is None:
        raise HTTPException(409,'Aguarde a resposta anterior antes de enviar outra mensagem.')
    if not chat_slots.acquire(blocking=False):
        busy.release()
        raise HTTPException(429,'O atendimento está ocupado. Tente em alguns instantes.',headers={'Retry-After':'5'})
    try:
        state=conversations.state(token)
        text=resolve_action(message.action_id,state) if message.action_id else message.message
        assistant=StoreAssistant(OpenRouter(), Catalog(ROOT / 'data'),state=state)
        result=assistant.reply(text,history=conversations.history(token))
        result['actions']=next_actions(result)
        state={'preferences':assistant.chat.preferences,'product_ids':list(assistant.chat.products)[:16] or assistant.chat.recent_product_ids,'allowed_actions':[action['id'] for action in result['actions']]}
        conversations.append(token,text,result['message'],state)
        result['conversation_id']=token
        return result
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except RuntimeError as exc:
        if str(exc).startswith('Limite'):
            raise HTTPException(429,str(exc),headers={'Retry-After':'60' if str(exc).startswith('Limite de uso do modelo') else '5'}) from None
        raise HTTPException(503, 'Atendimento indisponível no momento. Tente mais tarde.') from None

    finally:
        busy.release()
        chat_slots.release()

class Reset(BaseModel):
    conversation_id: str = Field(min_length=1,max_length=64)

@app.post('/api/conversation/reset',status_code=204)
def reset_conversation(body: Reset):
    conversations.reset(body.conversation_id)
    return Response(status_code=204)


class OrderVerification(BaseModel):
    order_id: int = Field(gt=0,le=999999999999,strict=True)
    email: str = Field(min_length=3,max_length=254)

@app.post('/api/orders/verify')
def verify_order(body: OrderVerification):
    result=Orders(ROOT/'data').verify(body.order_id,body.email)
    if result['status']=='error':
        raise HTTPException(503,'Não foi possível consultar o pedido. Tente mais tarde.')
    if result['status']=='invalid':
        raise HTTPException(422,'Confira o número e o e-mail da compra.')
    return result


INSTRUMENT_ART={1:'guitarra',2:'baixo',3:'bateria',4:'teclado',5:'violao',6:'saxofone',7:'trompete',8:'violino',9:'ukulele'}
CATEGORY_LABELS={6:'Sopros de madeira',7:'Sopros de metal'}

@app.get('/assets/instruments.svg')
def instrument_art():
    return FileResponse(ROOT/'app/static/instruments.svg',media_type='image/svg+xml')

@app.get('/api/categories')
def category_options():
    result=Catalog(ROOT/'data').categories()
    if result['status']=='error':raise HTTPException(503,'Não foi possível carregar os instrumentos. Tente novamente.')
    order=[5,1,2,4,3,9,8,6,7]
    items=sorted(result['items'],key=lambda item:order.index(item['category_id']) if item['category_id'] in order else 99)
    return {'categories':[dict(item,label=CATEGORY_LABELS.get(item['category_id'],item['name']),illustration='/assets/instruments.svg#'+INSTRUMENT_ART.get(item['category_id'],'generico')) for item in items]}

class CatalogSelection(BaseModel):
    category_id: int = Field(gt=0,strict=True)
    max_price: str | None = Field(default=None,max_length=32)
    conversation_id: str | None = Field(default=None,max_length=64)

@app.post('/api/catalog/search')
def selected_catalog(selection: CatalogSelection):
    catalog=Catalog(ROOT/'data')
    categories=catalog.categories()
    if categories['status']=='error':raise HTTPException(503,'Não foi possível consultar os instrumentos agora.')
    category=next((item for item in categories['items'] if item['category_id']==selection.category_id),None)
    if category is None:raise HTTPException(422,'Escolha um instrumento da lista.')
    try:
        ceiling=Decimal(selection.max_price) if selection.max_price is not None else None
        if ceiling is not None:
            if not ceiling.is_finite() or not 0<ceiling<=10000000:raise ValueError('Invalid budget')
            ceiling=ceiling.quantize(Decimal('0.01'))
            if ceiling<=0:raise ValueError('Invalid budget')
    except (InvalidOperation,ValueError):
        raise HTTPException(422,'Informe um valor válido ou escolha a opção sem limite de preço.') from None
    token=conversations.open(selection.conversation_id)
    busy=conversations.acquire(token)
    if busy is None:raise HTTPException(409,'Aguarde a consulta anterior ou inicie uma nova conversa.')
    try:
        filters={'category_id':selection.category_id,'in_stock':True,'status':'active'}
        if ceiling is not None:filters['max_price']=str(ceiling)
        result=catalog.search(**filters,limit=4)
        if result['status']=='error':raise HTTPException(503,'Não foi possível consultar os produtos agora. Tente novamente.')
        if result['status']=='invalid':raise HTTPException(422,'Confira o instrumento e o valor escolhidos.')
        name=category['name'].lower()
        price=('R$ '+format(ceiling,',.2f').replace(',','_').replace('.',',').replace('_','.')) if ceiling is not None else None
        question=f'Quero ver {name}'+(' até '+price if price else ', sem um limite de preço definido')+'.'
        answer=('Estas são algumas opções de '+name+(' até '+price if price else '')+'.') if result['items'] else 'Não encontrei opções em estoque para essa busca. Você pode mudar o valor ou escolher outro instrumento.'
        response={'message':answer,'products':result['items'],'sources':[],'contacts':[],'conversation_id':token}
        response['actions']=next_actions(response)
        response['actions'].insert(0,{'id':'change_search','label':'Alterar busca','kind':'instrument_picker'})
        state={'preferences':filters,'product_ids':[p['product_id'] for p in result['items']], 'allowed_actions':[action['id'] for action in response['actions'] if action['id'] in ('compare','cheaper','contact','policy_details','categories','hours')]}
        conversations.append(token,question,answer,state)
        return response
    finally:busy.release()


@app.get('/assets/{name}')
def client_asset(name: str):
    media={'chat.css':'text/css','chat.js':'application/javascript'}
    if name not in media:raise HTTPException(404)
    return FileResponse(ROOT/'app/static'/name,media_type=media[name])
