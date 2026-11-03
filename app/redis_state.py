"""Shared ephemeral state through Upstash REST; atomic Redis scripts fence late writes."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import secrets
import threading
from urllib.parse import urlparse

import httpx

from app.conversations import append_turn


class StorageUnavailable(RuntimeError):
    pass


class RedisREST:
    def __init__(self, url: str, token: str, *, client: httpx.Client | None = None):
        parsed = urlparse(url)
        if not token or parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.query or parsed.fragment:
            raise RuntimeError('Configure UPSTASH_REDIS_REST_URL e UPSTASH_REDIS_REST_TOKEN válidos.')
        self._url = url.rstrip('/')
        self._token = token
        self._client = client or httpx.Client(timeout=5)

    def command(self, *args):
        try:
            response = self._client.post(self._url, json=list(args),
                                         headers={'Authorization': 'Bearer ' + self._token},
                                         timeout=5, follow_redirects=False)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or 'error' in payload or 'result' not in payload:
                raise ValueError('Invalid Redis response')
            return payload['result']
        except (httpx.HTTPError, ValueError, TypeError):
            raise StorageUnavailable('Não foi possível acessar o estado compartilhado. Tente novamente.') from None

    def eval(self, script: str, keys: list[str], *args):
        return self.command('EVAL', script, len(keys), *keys, *args)


OPEN = '''
local now = tonumber(redis.call('TIME')[1])
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
if redis.call('EXISTS', KEYS[1]) == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[2])
  redis.call('ZADD', KEYS[2], now + tonumber(ARGV[2]), ARGV[1])
  redis.call('EXPIRE', KEYS[2], ARGV[2])
  return 1
end
if ARGV[5] == '1' then return -1 end
if redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[3]) then return 0 end
redis.call('SET', KEYS[1], ARGV[4], 'EX', ARGV[2])
redis.call('ZADD', KEYS[2], now + tonumber(ARGV[2]), ARGV[1])
redis.call('EXPIRE', KEYS[2], ARGV[2])
return 1
'''
SAVE = '''
if redis.call('GET', KEYS[2]) ~= ARGV[1] or redis.call('EXISTS', KEYS[1]) == 0 then return 0 end
redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
redis.call('ZADD', KEYS[3], tonumber(redis.call('TIME')[1]) + tonumber(ARGV[3]), ARGV[4])
redis.call('EXPIRE', KEYS[3], ARGV[3])
return 1
'''
UNLOCK = '''
if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
return 0
'''
RESET = '''
redis.call('DEL', KEYS[1])
redis.call('ZREM', KEYS[2], ARGV[1])
return 1
'''
RATE = '''
local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - tonumber(ARGV[1]))
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then
  local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
  return {0, math.max(1, math.ceil(tonumber(ARGV[1]) - now + tonumber(oldest[2])))}
end
redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[1])
return {1, 0}
'''
CAPACITY = '''
local now = tonumber(redis.call('TIME')[1])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then return 0 end
redis.call('ZADD', KEYS[1], now + tonumber(ARGV[2]), ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[2])
return 1
'''


class RedisLease:
    def __init__(self, redis: RedisREST, key: str, owner: str):
        self.redis, self.key, self.owner = redis, key, owner

    def release(self):
        try:
            self.redis.eval(UNLOCK, [self.key], self.owner)
        except StorageUnavailable:
            # The bounded lease expires; do not mask the original request result.
            logging.getLogger(__name__).warning('Shared conversation lease release failed')


class RedisConversationStore:
    def __init__(self, redis: RedisREST, namespace: str, *, ttl=900, max_sessions=100, lease_seconds=330):
        self.redis, self.namespace = redis, namespace
        self.ttl, self.max_sessions, self.lease_seconds = ttl, max_sessions, lease_seconds
        self.prefix = 'emporio:{' + namespace + '}'
        self.index_key = self.prefix + ':sessions'
        self._owners = threading.local()

    def data_key(self, token: str):
        return self.prefix + ':conversation:' + token

    def lock_key(self, token: str):
        return self.prefix + ':lock:' + token

    def _valid(self, token):
        return isinstance(token, str) and bool(re.fullmatch(r'[A-Za-z0-9_-]{43}', token))

    def open(self, token: str | None) -> str:
        existing = isinstance(token, str) and self._valid(token)
        candidate = token if existing and token is not None else secrets.token_urlsafe(32)
        for _ in range(2):
            allowed = self.redis.eval(OPEN, [self.data_key(candidate), self.index_key], candidate, self.ttl,
                                      self.max_sessions, json.dumps({'messages': [], 'state': {}}), '1' if existing else '0')
            if allowed == 1:
                return candidate
            if allowed == -1:
                candidate, existing = secrets.token_urlsafe(32), False
                continue
            break
        raise StorageUnavailable('O atendimento está ocupado. Tente novamente em instantes.')

    def _read(self, token: str):
        raw = self.redis.command('GET', self.data_key(token)) if self._valid(token) else None
        if raw is None:
            return {'messages': [], 'state': {}}
        try:
            value = json.loads(raw)
            if not isinstance(value.get('messages'), list) or not isinstance(value.get('state'), dict):
                raise ValueError('Invalid session')
            return value
        except (ValueError, TypeError, AttributeError):
            raise StorageUnavailable('Não foi possível ler a conversa. Inicie uma nova conversa.') from None

    def history(self, token: str) -> list[dict]:
        return self._read(token)['messages']

    def state(self, token: str) -> dict:
        return self._read(token)['state']

    def append(self, token: str, user: str, answer: str, state: dict | None = None):
        owner = getattr(self._owners, 'owner', None) if getattr(self._owners, 'token', None) == token else None
        if not owner:
            raise StorageUnavailable('A consulta expirou. Tente novamente.')
        messages = self.history(token)
        append_turn(messages, user, answer)
        saved = self.redis.eval(SAVE, [self.data_key(token), self.lock_key(token), self.index_key], owner,
                                json.dumps({'messages': messages, 'state': state or {}}, ensure_ascii=False), self.ttl, token)
        if not saved:
            raise StorageUnavailable('A conversa foi reiniciada ou a consulta expirou. Tente novamente.')

    def reset(self, token: str):
        if self._valid(token):
            self.redis.eval(RESET, [self.data_key(token), self.index_key], token)

    def acquire(self, token: str) -> RedisLease | None:
        owner = secrets.token_urlsafe(24)
        if not self._valid(token) or not self.redis.command('SET', self.lock_key(token), owner, 'NX', 'EX', self.lease_seconds):
            return None
        self._owners.token, self._owners.owner = token, owner
        return RedisLease(self.redis, self.lock_key(token), owner)


class RedisRateLimiter:
    def __init__(self, redis: RedisREST, namespace: str, window=60):
        self.redis, self.prefix, self.window = redis, 'emporio:{' + namespace + '}:rate:', window

    def allow(self, key: str, limit: int) -> tuple[bool, int]:
        hashed = hashlib.sha256(key.encode()).hexdigest()
        allowed, retry = self.redis.eval(RATE, [self.prefix + hashed], self.window, limit, secrets.token_hex(16))
        return bool(allowed), int(retry)


class RedisCapacity:
    def __init__(self, redis: RedisREST, namespace: str, limit=4, lease_seconds=330):
        self.redis, self.key = redis, 'emporio:{' + namespace + '}:chat-slots'
        self.limit, self.lease_seconds = limit, lease_seconds
        self._owners = threading.local()

    def acquire(self, blocking=False) -> bool:
        owner = secrets.token_hex(16)
        acquired = self.redis.eval(CAPACITY, [self.key], self.limit, self.lease_seconds, owner)
        if acquired:
            self._owners.owner = owner
        return bool(acquired)

    def release(self):
        owner = getattr(self._owners, 'owner', None)
        if owner:
            try:
                self.redis.command('ZREM', self.key, owner)
            except StorageUnavailable:
                logging.getLogger(__name__).warning('Shared chat capacity release failed')
            finally:
                self._owners.owner = None
