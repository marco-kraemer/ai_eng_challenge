from pathlib import Path
from typing import Annotated
import ipaddress
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.catalog import Catalog
from app.catalog_flow import catalog_reply, INSTRUMENT_ART, CATEGORY_LABELS
from app.orders import Orders
from app.limits import RateLimiter, BodyLimitMiddleware
from app.conversations import ConversationStore
from app.actions import next_actions, resolve_action
from app.assistant import StoreAssistant
from app.llm import build_provider
from app.runtime import build_backends
from app.telemetry import turn, traced_request, event_sink, raise_if_cancelled, StreamCancelled
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
    limit=CHAT_RATE if request.url.path in ('/api/chat','/api/chat/stream','/api/catalog/search','/api/catalog/compare') else ORDER_RATE if request.url.path=='/api/orders/verify' else None
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

def acquire_chat(message: Message):
    if not message.action_id and not message.message.strip():
        raise HTTPException(422, 'Envie uma mensagem de 1 a 2000 caracteres.')
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
    return token, busy


@app.post('/api/chat')
def reply(message: Message):
    token, busy = acquire_chat(message)
    try:
        return answer_turn(message, token)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except RuntimeError as exc:
        if str(exc).startswith('Limite'):
            raise HTTPException(429,str(exc),headers={'Retry-After':'60' if str(exc).startswith('Limite de uso do modelo') else '5'}) from None
        raise HTTPException(503, 'Atendimento indisponível no momento. Tente mais tarde.') from None

    finally:
        busy.release()
        chat_slots.release()

def answer_turn(message: Message, token: str):
    with turn(token) as trace:
        state=conversations.state(token)
        text=resolve_action(message.action_id,state) if message.action_id else message.message
        assistant=StoreAssistant(build_provider(), Catalog(ROOT / 'data'),state=state)
        result=assistant.reply(text,history=conversations.history(token))
        result.setdefault('actions',next_actions(result))
        state=assistant.context()
        state['allowed_actions']=[action['id'] for action in result['actions']]
        raise_if_cancelled()
        conversations.append(token,text,result['message'],state)
        result['conversation_id']=token
        result['trace_id'] = trace.id
        return result


PUBLIC_PROGRESS = {
    'faq': 'Consultando informações da loja…', 'classify': 'Entendendo seu pedido…',
    'search_catalog': 'Consultando instrumentos…', 'search_policies': 'Consultando o manual da loja…',
    'retrieve_policies': 'Consultando o manual da loja…', 'compare_products': 'Comparando instrumentos…',
    'search_promotions': 'Consultando ofertas…', 'store_contacts': 'Consultando os contatos da loja…',
}


@app.post('/api/chat/stream')
def stream_reply(message: Message):
    import asyncio
    import queue
    import threading
    import json
    token, busy = acquire_chat(message)
    events: queue.Queue = queue.Queue(maxsize=256)
    cancelled = threading.Event()

    def publish(event):
        while not cancelled.is_set():
            try:
                events.put(event, timeout=.1)
                return
            except queue.Full:
                continue
        raise StreamCancelled('Request cancelled')

    def receive(event):
        if event['type'] == 'progress':
            publish({'type': 'progress', 'label': PUBLIC_PROGRESS.get(event['stage'], 'Preparando sua resposta…')})
        elif event['type'] in ('delta', 'answer_reset'):
            publish(event)

    def work():
        terminal = None
        try:
            with event_sink(receive, cancelled):
                result = answer_turn(message, token)
                terminal = {'type': 'done', 'result': result}
        except StreamCancelled:
            pass
        except Exception as error:
            status = 422 if isinstance(error, ValueError) else 429 if str(error).startswith('Limite') else 503
            detail = str(error) if status in (422, 429) else 'Atendimento indisponível no momento. Tente mais tarde.'
            terminal = {'type': 'error', 'status': status, 'detail': detail}
        finally:
            busy.release()
            chat_slots.release()
            if not cancelled.is_set():
                if terminal:
                    publish(terminal)
                publish(None)

    async def output():
        worker = threading.Thread(target=work, daemon=True)
        worker.start()
        try:
            yield 'data: ' + json.dumps({'type': 'accepted', 'conversation_id': token}) + '\n\n'
            while True:
                try:
                    event = await asyncio.to_thread(events.get, True, 1)
                except queue.Empty:
                    yield ': keep-alive\n\n'
                    continue
                if event is None:
                    break
                yield 'data: ' + json.dumps(event, ensure_ascii=False) + '\n\n'
        finally:
            cancelled.set()

    return StreamingResponse(output(), media_type='text/event-stream',
        headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})


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
@traced_request
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
    model_config = ConfigDict(extra='forbid')
    category_id: int | None = Field(default=None,gt=0,strict=True)
    category_ids: list[Annotated[int, Field(strict=True, gt=0)]] | None = Field(default=None,max_length=9)
    max_price: str | None = Field(default=None,max_length=32)
    conversation_id: str | None = Field(default=None,max_length=64)

    @model_validator(mode='after')
    def unique_scope(self):
        if self.category_id is not None and self.category_ids is not None:
            raise ValueError('Escolha uma categoria ou uma lista de categorias.')
        if self.category_ids is not None and len(set(self.category_ids)) != len(self.category_ids):
            raise ValueError('Escolha cada categoria apenas uma vez.')
        return self

@app.post('/api/catalog/search')
@traced_request
def selected_catalog(selection: CatalogSelection):
    token=conversations.open(selection.conversation_id)
    busy=conversations.acquire(token)
    if busy is None:raise HTTPException(409,'Aguarde a consulta anterior ou inicie uma nova conversa.')
    try:
        response,question,state=catalog_reply(Catalog(ROOT/'data'),selection.category_id,selection.max_price,category_ids=selection.category_ids)
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
@traced_request
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
    media={'chat.css':'text/css','chat.js':'application/javascript','stream.js':'application/javascript'}
    if name not in media:raise HTTPException(404)
    return FileResponse(ROOT/'app/static'/name,media_type=media[name])
