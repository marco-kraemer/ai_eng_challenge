"""Direct OpenAI API with the approved model and no provider/model fallback."""
import os
from app.chat_transport import ChatCompletionsTransport


class OpenAI(ChatCompletionsTransport):
    endpoint = 'https://api.openai.com/v1/chat/completions'
    provider_name = 'OpenAI'

    def __init__(self, api_key=None, model=None):
        key = os.getenv('OPEN_AI_KEY') or os.getenv('OPENAI_API_KEY') or ''
        super().__init__(key if api_key is None else api_key,
                         model or os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))

    def validate(self):
        if not self.api_key or self.model not in ('gpt-4.1-mini', 'gpt-4.1-mini-2025-04-14'):
            raise RuntimeError('Configure OPEN_AI_KEY e OPENAI_MODEL=gpt-4.1-mini no servidor.')

    def request_body(self, messages, tools):
        return {**super().request_body(messages, tools), 'max_completion_tokens': 2048, 'store': False}
