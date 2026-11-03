"""Explicit provider selection. Missing credentials never trigger a fallback."""
import os
from app.chat_transport import ChatCompletionsTransport
from app.openai_provider import OpenAI
from app.openrouter import OpenRouter


def build_provider() -> ChatCompletionsTransport:
    provider = os.getenv('LLM_PROVIDER', 'openai')
    if provider == 'openai':
        return OpenAI()
    if provider == 'openrouter':
        return OpenRouter()
    raise ValueError('LLM_PROVIDER deve ser openai ou openrouter.')
