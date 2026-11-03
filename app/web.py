from pathlib import Path
from typing import Annotated
import ipaddress
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse, FileResponse
from pydantic import BaseModel, Field
from app.catalog import Catalog
from app.catalog_flow import catalog_reply, INSTRUMENT_ART, CATEGORY_LABELS
from app.orders import Orders
from app.limits import RateLimiter, BodyLimitMiddleware
from app.conversations import ConversationStore
from app.actions import next_actions, resolve_action
from app.assistant import StoreAssistant
from app.llm import build_provider
from app.runtime import build_backends
from app.redis_state import StorageUnavailable
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
app = FastAPI(title='Empório da Música')
conversations, rate_limiter, chat_slots = build_backends()
CHAT_RATE=20
ORDER_RATE=5
app.add_middleware(BodyLimitMiddleware,max_bytes=16000)


@app.exception_handler(StorageUnavailable)
async def storage_unavailable(request, exc):
    return JSONResponse({'detail': 'Atendimento temporariamente indisponível. Tente novamente em instantes.'}, status_code=503)


def client_actor(request):
    if os.getenv('VERCEL') == '1':
        forwarded = request.headers.get('x-vercel-forwarded-for') or request.headers.get('x-forwarded-for', '')
        try:
            return str(ipaddress.ip_address(forwarded.strip()))
        except ValueError:
            pass
    return request.client.host if request.client else 'unknown'


@app.middleware('http')
async def protect_requests(request,call_next):
    limit=CHAT_RATE if request.url.path in ('/api/chat','/api/catalog/search','/api/catalog/compare') else ORDER_RATE if request.url.path=='/api/orders/verify' else None
    if request.method=='POST' and limit is not None:
        actor=client_actor(request)
        try:
            allowed,retry=await run_in_threadpool(rate_limiter.allow, request.url.path+':'+actor, limit)
        except StorageUnavailable:
            return JSONResponse({'detail':'Atendimento temporariamente indisponível. Tente novamente em instantes.'}, status_code=503, headers={'Cache-Control':'no-store'})
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


@app.get('/api/health')
def health():
    return {'status': 'ok'}

@app.post('/api/chat')
def reply(message: Message):
    token=conversations.open(message.conversation_id)
    busy=conversations.acquire(token)
    if busy is None:
        raise HTTPException(409,'Aguarde a resposta anterior antes de enviar outra mensagem.')
    try:
        available = chat_slots.acquire(blocking=False)
    except StorageUnavailable:
        busy.release()
        raise
    if not available:
        busy.release()
        raise HTTPException(429,'O atendimento está ocupado. Tente em alguns instantes.',headers={'Retry-After':'5'})
    try:
        state=conversations.state(token)
        text=resolve_action(message.action_id,state) if message.action_id else message.message
        assistant=StoreAssistant(build_provider(), Catalog(ROOT / 'data'),state=state)
        result=assistant.reply(text,history=conversations.history(token))
        result.setdefault('actions',next_actions(result))
        state=assistant.context()
        state['allowed_actions']=[action['id'] for action in result['actions']]
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



@app.get('/assets/instruments.svg')
def instrument_art():
    return FileResponse(ROOT/'app/static/instruments.svg',media_type='image/svg+xml')

@app.get('/api/categories')
def category_options():
    result=Catalog(ROOT/'data').available_categories()
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
    token=conversations.open(selection.conversation_id)
    busy=conversations.acquire(token)
    if busy is None:raise HTTPException(409,'Aguarde a consulta anterior ou inicie uma nova conversa.')
    try:
        response,question,state=catalog_reply(Catalog(ROOT/'data'),selection.category_id,selection.max_price)
        response['conversation_id']=token
        conversations.append(token,question,response['message'],state)
        return response
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from None
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)) from None
    finally:busy.release()


class ProductComparison(BaseModel):
    product_ids: list[Annotated[int, Field(strict=True, gt=0)]] = Field(min_length=2, max_length=4)
    max_price: str | None = Field(default=None, max_length=32)
    conversation_id: str | None = Field(default=None, max_length=64)


@app.post('/api/catalog/compare')
def selected_comparison(selection: ProductComparison):
    if len(set(selection.product_ids)) != len(selection.product_ids):
        raise HTTPException(422, 'Selecione instrumentos diferentes para comparar.')
    catalog=Catalog(ROOT/'data')
    result=catalog.compare(selection.product_ids, selection.max_price)
    if result['status']=='invalid':raise HTTPException(422,'Confira os instrumentos e o orçamento.')
    if result['status']=='error':raise HTTPException(503,'Não foi possível comparar agora. Tente novamente.')
    if result['status']!='found' or any(p['status']!='active' or p['stock_quantity']<=0 for p in result['items']):
        raise HTTPException(409,'Uma opção não está mais disponível. Faça uma nova busca para comparar.')
    token=conversations.open(selection.conversation_id)
    busy=conversations.acquire(token)
    if busy is None:raise HTTPException(409,'Aguarde a consulta anterior.')
    try:
        response={'message':'Compare as características e os preços de tabela atuais das opções escolhidas.',
                  'products':result['items'],'sources':[],'contacts':[],'comparison':True,'conversation_id':token}
        response['actions']=[{'id':'change_search','label':'Escolher outros instrumentos','kind':'instrument_picker'}]
        state=conversations.state(token)
        preferences=dict(state.get('preferences',{}))
        if selection.max_price is not None:preferences['max_price']=selection.max_price
        state.pop('pending_budget',None)
        state.update({'topic':'products','product_ids':selection.product_ids,'preferences':preferences,'allowed_actions':[]})
        conversations.append(token,'Comparar os instrumentos selecionados.',response['message'],state)
        return response
    finally:busy.release()


@app.get('/assets/{name}')
def client_asset(name: str):
    media={'chat.css':'text/css','chat.js':'application/javascript'}
    if name not in media:raise HTTPException(404)
    return FileResponse(ROOT/'app/static'/name,media_type=media[name])
