"""Bounded, ephemeral conversations. Tokens are kept only in the open page."""
from __future__ import annotations
import copy
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, TypedDict

class ConversationContext(TypedDict, total=False):
    preferences: dict
    product_ids: list[int]
    allowed_actions: list[str]
    topic: str
    purchase_channel: str
    pending_budget: dict
    pending_question: str


def append_turn(messages: list[dict], user: str, answer: str):
    """Apply the same privacy and history bounds to local and shared sessions."""
    for role, text in [('user', user), ('model', answer)]:
        text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[e-mail omitido]', text)
        messages.append({'role': role, 'parts': [{'text': text[:2000]}]})
    while len(messages) > 12 or sum(len(m['parts'][0]['text']) for m in messages) > 8000:
        del messages[:2]


@dataclass
class Conversation:
    touched: float
    messages: list[dict] = field(default_factory=list)
    state: dict = field(default_factory=dict)
    busy: threading.Lock = field(default_factory=threading.Lock)

class ConversationStore:
    def __init__(self, max_sessions=100, ttl=900, clock: Callable[[], float]=time.monotonic):
        self.max_sessions = max_sessions
        self.ttl = ttl
        self.clock = clock
        self.sessions: dict[str, Conversation] = {}
        self.lock = threading.RLock()

    def open(self, token: str | None) -> str:
        with self.lock:
            now = self.clock()
            for key in list(self.sessions):
                if now-self.sessions[key].touched >= self.ttl:
                    del self.sessions[key]
            if token in self.sessions:
                self.sessions[token].touched = now
                return token
            if len(self.sessions) >= self.max_sessions:
                del self.sessions[min(self.sessions,key=lambda key:self.sessions[key].touched)]
            token = secrets.token_urlsafe(32)
            self.sessions[token] = Conversation(now)
            return token

    def history(self, token: str) -> list[dict]:
        with self.lock:
            return copy.deepcopy(self.sessions[token].messages) if token in self.sessions else []

    def state(self, token: str) -> dict:
        with self.lock:
            return copy.deepcopy(self.sessions[token].state) if token in self.sessions else {}

    def append(self, token: str, user: str, answer: str, state: dict | None=None):
        with self.lock:
            if token not in self.sessions:
                return
            conversation = self.sessions[token]
            append_turn(conversation.messages, user, answer)
            conversation.state = copy.deepcopy(state or {})
            conversation.touched = self.clock()

    def reset(self, token: str):
        with self.lock:
            self.sessions.pop(token,None)

    def acquire(self, token: str) -> threading.Lock | None:
        with self.lock:
            conversation = self.sessions.get(token)
            if conversation is not None and conversation.busy.acquire(blocking=False):
                return conversation.busy
            return None
