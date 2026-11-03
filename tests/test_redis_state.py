"""Run against real Redis Lua: REDIS_TEST_CONTAINER=... python -m unittest ..."""
import json
import os
import subprocess
import unittest
from unittest.mock import patch

import httpx


@unittest.skipUnless(os.getenv('REDIS_TEST_CONTAINER'), 'Set REDIS_TEST_CONTAINER for real Redis integration')
class SharedStateTests(unittest.TestCase):
    def command(self, *args):
        result = subprocess.run(['docker', 'exec', os.environ['REDIS_TEST_CONTAINER'], 'redis-cli', '--json',
                                 *[str(a) for a in args]], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def setUp(self):
        from app.redis_state import RedisREST, RedisConversationStore
        def request(request):
            return httpx.Response(200, json={'result': self.command(*json.loads(request.content))})
        self.client = httpx.Client(transport=httpx.MockTransport(request))
        self.addCleanup(self.client.close)
        self.redis = RedisREST('https://test.upstash.io', 'private-token', client=self.client)
        import secrets
        self.namespace = 'test-' + secrets.token_hex(8)
        self.first = RedisConversationStore(self.redis, self.namespace)
        self.second = RedisConversationStore(self.redis, self.namespace)

    def save(self, store, token, question='Quero um violão', answer='Qual valor?', state=None):
        lease = store.acquire(token)
        self.assertIsNotNone(lease)
        try:
            store.append(token, question, answer, state or {'topic': 'products', 'preferences': {'category_id': 5}})
        finally:
            lease.release()

    def test_sse_keeps_redis_lease_and_capacity_on_the_execution_thread(self):
        from fastapi.testclient import TestClient
        from app.web import app
        from app.redis_state import RedisCapacity
        from app.limits import RateLimiter
        capacity = RedisCapacity(self.redis, self.namespace, limit=1)
        with patch('app.web.conversations', self.first), patch('app.web.chat_slots', capacity), patch('app.web.rate_limiter', RateLimiter()), patch('app.telemetry.export_runs'), TestClient(app) as client:
            token = None
            for _ in range(3):
                response = client.post('/api/chat/stream', json={'message': 'Qual é o endereço da loja?', 'conversation_id': token})
                self.assertEqual(response.status_code, 200)
                events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
                completed = [e for e in events if e['type'] == 'done']
                self.assertEqual(len(completed), 1, events)
                token = completed[0]['result']['conversation_id']
                self.assertEqual(self.command('ZCARD', capacity.key), 0)
            self.assertEqual(len(self.second.history(token)), 6)
            busy = self.second.acquire(token)
            try:
                response = client.post('/api/chat/stream', json={'message': 'Olá', 'conversation_id': token})
                self.assertEqual(response.status_code, 409)
                self.assertIn('application/json', response.headers['content-type'])
            finally:
                busy.release()

    def test_context_crosses_instances_is_bounded_and_reset_does_not_resurrect(self):
        token = self.first.open(None)
        self.save(self.first, token, question='compra com cliente@example.test')
        self.assertEqual(self.second.open(token), token)
        self.assertEqual(self.second.state(token)['preferences']['category_id'], 5)
        self.assertNotIn('cliente@example.test', str(self.second.history(token)))
        other = self.second.open(None)
        self.assertEqual(self.first.history(other), [])
        for _ in range(8):
            self.save(self.second, token, 'X'*2000, 'Y'*2000)
        self.assertLessEqual(sum(len(m['parts'][0]['text']) for m in self.first.history(token)), 8000)
        lease = self.first.acquire(token)
        self.second.reset(token)
        with self.assertRaises(RuntimeError):
            self.first.append(token, 'Late question', 'Late response')
        lease.release()
        self.assertEqual(self.second.state(token), {})
        self.assertNotEqual(self.second.open(token), token)

    def test_lock_owner_expiry_and_stale_write_protection(self):
        token = self.first.open(None)
        lease = self.first.acquire(token)
        self.assertIsNone(self.second.acquire(token))
        self.command('DEL', self.first.lock_key(token))  # Simulate lease expiry.
        replacement = self.second.acquire(token)
        self.assertIsNotNone(replacement)
        with self.assertRaises(RuntimeError):
            self.first.append(token, 'stale', 'stale')
        lease.release()  # Must not release the replacement owner.
        self.assertIsNone(self.first.acquire(token))
        self.second.append(token, 'valid', 'valid')
        replacement.release()
        self.assertIn('valid', str(self.first.history(token)))

    def test_ttl_expiry_discards_context_and_capacity_is_bounded(self):
        from app.redis_state import RedisConversationStore
        store = RedisConversationStore(self.redis, self.namespace, max_sessions=1)
        token = store.open(None)
        self.save(store, token)
        with self.assertRaises(RuntimeError):
            store.open(None)
        self.command('DEL', store.data_key(token))
        self.command('ZADD', store.index_key, 0, token)
        renewed = store.open(token)
        self.assertNotEqual(renewed, token)
        self.assertEqual(store.state(renewed), {})
        self.assertGreater(self.command('TTL', store.data_key(renewed)), 0)

    def test_rate_limit_and_chat_capacity_are_shared(self):
        from app.redis_state import RedisRateLimiter, RedisCapacity
        first = RedisRateLimiter(self.redis, self.namespace)
        second = RedisRateLimiter(self.redis, self.namespace)
        self.assertTrue(first.allow('chat:one', 1)[0])
        allowed, retry = second.allow('chat:one', 1)
        self.assertFalse(allowed)
        self.assertGreater(retry, 0)
        self.assertTrue(second.allow('chat:two', 1)[0])
        capacity1 = RedisCapacity(self.redis, self.namespace, limit=1)
        capacity2 = RedisCapacity(self.redis, self.namespace, limit=1)
        self.assertTrue(capacity1.acquire(blocking=False))
        self.assertFalse(capacity2.acquire(blocking=False))
        capacity1.release()
        self.assertTrue(capacity2.acquire(blocking=False))
        capacity2.release()

    def test_redis_failure_is_generic_and_rest_uses_post_authorization(self):
        from app.redis_state import RedisREST, StorageUnavailable
        requests = []
        def bad_response(request):
            requests.append(request)
            return httpx.Response(401, json={'error': 'internal secret'})
        with httpx.Client(transport=httpx.MockTransport(bad_response)) as client:
            redis = RedisREST('https://test.upstash.io', 'private-token', client=client)
            with self.assertRaises(StorageUnavailable) as error:
                redis.command('GET', 'key')
        self.assertNotIn('secret', str(error.exception))
        self.assertNotIn('private-token', repr(redis))
        self.assertEqual(requests[0].method, 'POST')
        self.assertEqual(requests[0].headers['authorization'], 'Bearer private-token')
        self.assertNotIn('private-token', str(requests[0].url))

    def test_http_followup_uses_state_written_by_another_instance(self):
        from unittest.mock import Mock
        from fastapi.testclient import TestClient
        from app.web import app
        from app.limits import RateLimiter
        provider = Mock()
        provider.generate.side_effect = [
            {'parts': [{'text': 'store'}]},
            {'parts': [{'functionCall': {'name': 'search_catalog', 'args': {'category_id': 2}}}]},
            {'parts': [{'text': 'Veja os baixos disponíveis.'}]},
        ]
        with patch('app.web.rate_limiter', RateLimiter()), TestClient(app) as client:
            with patch('app.web.conversations', self.first):
                first = client.post('/api/catalog/search', json={'category_id': 2, 'max_price': '500'}).json()
            with patch('app.web.conversations', self.second), patch('app.web.build_provider', return_value=provider):
                response = client.post('/api/chat', json={'message': 'tanto faz o preço agora', 'conversation_id': first['conversation_id']})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['conversation_id'], first['conversation_id'])
        self.assertTrue(response.json()['products'])
        self.assertNotIn('max_price', self.first.state(first['conversation_id'])['preferences'])
        self.assertIn(first['recovery']['price_brl'], str(provider.generate.call_args_list[1].args[0]))
