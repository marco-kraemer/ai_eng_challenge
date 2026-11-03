"""Optional legacy OpenRouter provider; only free models, no paid fallback."""
import os
import httpx  # Kept as the patch point for existing transport contract tests.
from app.chat_transport import ChatCompletionsTransport


class OpenRouter(ChatCompletionsTransport):
    endpoint = 'https://openrouter.ai/api/v1/chat/completions'
    provider_name = 'OpenRouter'

    def __init__(self, api_key=None, model=None):
        super().__init__(os.getenv('OPENROUTER_API_KEY', '') if api_key is None else api_key,
                         model or os.getenv('OPENROUTER_MODEL', 'openrouter/free'))

    def validate(self):
        if not self.api_key or not (self.model == 'openrouter/free' or self.model.endswith(':free')):
            raise RuntimeError('Configure uma chave e um modelo gratuito no servidor.')

    def request_body(self, messages, tools):
        return {**super().request_body(messages, tools),
                'provider': {'require_parameters': True}, 'max_tokens': 2048}
