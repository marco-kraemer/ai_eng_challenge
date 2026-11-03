"""Bounded model → tools → model graph, using LangChain messages throughout."""
from __future__ import annotations

import json
from typing import TypedDict

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError


class AgentState(TypedDict):
    messages: list[BaseMessage]
    rounds: int
    answer: str


def build_agent_graph(model, tools):
    bound = model.bind_tools(list(tools.values()))

    def generate(state: AgentState):
        if state['rounds'] >= 4:
            raise RuntimeError('Limite de consultas atingido. Refine a pergunta.')
        message = bound.invoke(state['messages'], config={'callbacks': []})
        if len(message.tool_calls) > 3:
            raise RuntimeError('Limite de consultas atingido.')
        return {'messages': state['messages'] + [message], 'rounds': state['rounds'] + 1,
                'answer': str(message.content) or 'Não consegui responder. Tente novamente.'}

    def run_tools(state: AgentState):
        message = state['messages'][-1]
        assert isinstance(message, AIMessage)
        results = []
        for call in message.tool_calls:
            selected = tools.get(call['name'])
            try:
                result = selected.invoke(call['args']) if selected else {'status': 'invalid', 'items': []}
            except ValidationError:
                result = {'status': 'invalid', 'items': []}
            results.append(ToolMessage(content=json.dumps(result, ensure_ascii=False),
                                       tool_call_id=call['id'], name=call['name']))
        return {'messages': state['messages'] + results}

    def next_step(state: AgentState):
        message = state['messages'][-1]
        return 'tools' if isinstance(message, AIMessage) and message.tool_calls else END

    graph = StateGraph(AgentState)
    graph.add_node('model', generate)
    graph.add_node('tools', run_tools)
    graph.add_edge(START, 'model')
    graph.add_conditional_edges('model', next_step, {'tools': 'tools', END: END})
    graph.add_edge('tools', 'model')
    return graph.compile()
