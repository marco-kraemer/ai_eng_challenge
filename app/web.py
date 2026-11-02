from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from app.catalog import Catalog
from app.assistant import StoreAssistant
from app.openrouter import OpenRouter
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
app = FastAPI(title='Empório da Música')

class Message(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

@app.get('/', response_class=HTMLResponse)
def index():
    return (ROOT / 'app/static/index.html').read_text(encoding='utf-8')

@app.post('/api/chat')
def reply(message: Message):
    try:
        return StoreAssistant(OpenRouter(), Catalog(ROOT / 'data')).reply(message.message)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except RuntimeError:
        raise HTTPException(503, 'Atendimento indisponível no momento. Tente mais tarde.') from None
