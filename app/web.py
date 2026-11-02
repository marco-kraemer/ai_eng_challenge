from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from app.catalog import Catalog
from app.orders import Orders
from app.conversations import ConversationStore
from app.actions import next_actions, resolve_action
from app.assistant import StoreAssistant
from app.openrouter import OpenRouter
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
app = FastAPI(title='Empório da Música')
conversations = ConversationStore()

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
    try:
        state=conversations.state(token)
        text=resolve_action(message.action_id,state) if message.action_id else message.message
        assistant=StoreAssistant(OpenRouter(), Catalog(ROOT / 'data'),state=state)
        result=assistant.reply(text,history=conversations.history(token))
        if message.action_id=='draft':
            if result.get('sources') or result.get('products'):
                result['draft']=result['message']
                result['message']='Preparei uma sugestão de resposta. Revise as condições e as fontes antes de encaminhar ao cliente.'
            else:
                result['message']='Não consegui confirmar as fontes para preparar essa mensagem. Consulte a informação novamente antes de encaminhar uma resposta ao cliente.'
        result['actions']=next_actions(result)
        state={'preferences':assistant.chat.preferences,'product_ids':list(assistant.chat.products)[:16] or assistant.chat.recent_product_ids,'allowed_actions':[action['id'] for action in result['actions']]}
        conversations.append(token,text,result.get('draft',result['message']),state)
        result['conversation_id']=token
        return result
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except RuntimeError:
        raise HTTPException(503, 'Atendimento indisponível no momento. Tente mais tarde.') from None

    finally:
        busy.release()

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
