"""LangChain chat model over the configured bounded Chat Completions transport.

The transport owns credentials, model allowlist enforcement, HTTP errors and retries.
This adapter owns standard messages and tool-call correlation, not HTTP policy.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.tool import ToolCall
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import Field

from app.provider import SYSTEM


def history_messages(history: list[dict]) -> list[BaseMessage]:
    return [
        (AIMessage if item.get('role') in ('model', 'assistant') else HumanMessage)(
            content='\n'.join(part['text'] for part in item.get('parts', []) if 'text' in part))
        for item in history
    ]


def transport_contents(messages: list[BaseMessage]) -> list[dict]:
    """Keep document results in tool messages, including native provider IDs."""
    contents: list[dict] = []
    for message in messages:
        if isinstance(message, SystemMessage):
            continue
        if isinstance(message, ToolMessage):
            part = {'functionResponse': {'name': message.name or '',
                    'response': json.loads(str(message.content))}}
            if contents and contents[-1].get('_tool_results'):
                contents[-1]['parts'].append(part)
            else:
                contents.append({'role': 'user', 'parts': [part], '_tool_results': True})
        elif isinstance(message, AIMessage) and message.tool_calls:
            native = message.response_metadata.get('native') or {
                'role': 'assistant', 'content': message.content or None,
                'tool_calls': [{'id': call['id'], 'type': 'function', 'function': {
                    'name': call['name'], 'arguments': json.dumps(call['args'], ensure_ascii=False)}}
                    for call in message.tool_calls]}
            contents.append({'role': 'model', 'parts': [], '_openrouter_message': native})
        else:
            contents.append({'role': 'model' if isinstance(message, AIMessage) else 'user',
                             'parts': [{'text': message.content}]})
    return contents


class StoreChatModel(BaseChatModel):
    transport: Any = Field(exclude=True, repr=False)

    @property
    def _llm_type(self) -> str:
        return 'emporio-chat-completions'

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        if tool_choice is not None:
            raise ValueError('Tool choice is controlled by the store graph.')
        return self.bind(tools=[convert_to_openai_tool(tool)['function'] for tool in tools], **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        system = next((str(m.content) for m in messages if isinstance(m, SystemMessage)), SYSTEM)
        contents = transport_contents(messages)
        if len(json.dumps(contents, ensure_ascii=False).encode('utf-8')) > 24000:
            raise RuntimeError('Limite de contexto atingido. Inicie outro assunto.')
        # Do not send system prompts as user messages; retain the existing transport contract.
        options = {'system': system} if system != SYSTEM else {}
        response = self.transport.generate(contents, kwargs.get('tools', []), **options)
        native = response.get('_openrouter_message', {})
        native_calls = native.get('tool_calls', [])
        tool_calls: list[ToolCall] = []
        for part in response.get('parts', []):
            if 'functionCall' in part:
                call = part['functionCall']
                position = len(tool_calls)
                call_id = native_calls[position]['id'] if position < len(native_calls) else 'call-' + uuid4().hex
                args = call.get('args', {})
                if not isinstance(args, dict):
                    raise RuntimeError('Argumentos de ferramenta inválidos.')
                tool_calls.append({'name': call.get('name', ''), 'args': args, 'id': call_id})
        text = '\n'.join(part['text'] for part in response.get('parts', []) if 'text' in part)
        answer = AIMessage(content=text, tool_calls=tool_calls,
                           response_metadata={'native': native} if native else {})
        return ChatResult(generations=[ChatGeneration(message=answer)])
