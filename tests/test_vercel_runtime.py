import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class VercelRuntimeTests(unittest.TestCase):
    def test_local_backend_is_preserved_but_vercel_requires_shared_storage(self):
        from app.runtime import build_backends
        from app.conversations import ConversationStore
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(build_backends()[0], ConversationStore)
        with patch.dict(os.environ, {'VERCEL': '1'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'UPSTASH'):
                build_backends()

    def test_vercel_selects_shared_backends_and_namespaces_preview(self):
        from app.runtime import build_backends
        from app.redis_state import RedisConversationStore, RedisRateLimiter, RedisCapacity
        env = {'VERCEL': '1', 'VERCEL_ENV': 'preview', 'VERCEL_GIT_COMMIT_REF': 'feature/test',
               'UPSTASH_REDIS_REST_URL': 'https://example.upstash.io', 'UPSTASH_REDIS_REST_TOKEN': 'private-test'}
        with patch.dict(os.environ, env, clear=True):
            sessions, limiter, slots = build_backends()
        self.assertIsInstance(sessions, RedisConversationStore)
        self.assertIsInstance(limiter, RedisRateLimiter)
        self.assertIsInstance(slots, RedisCapacity)
        self.assertNotIn('private-test', repr(sessions.redis))
        self.assertIn('preview', sessions.namespace)

    def test_vercel_cache_is_writable_and_seeded_without_modifying_bundle(self):
        from app.runtime import policy_cache_dir, seed_policy_cache
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundled = root/'bundle'; bundled.mkdir()
            (bundled/'embeddings').mkdir()
            (bundled/'policies').mkdir()
            (bundled/'embeddings'/'model.onnx').write_bytes(b'cached-model')
            target = root/'scratch'
            with patch.dict(os.environ, {'VERCEL': '1'}, clear=True):
                self.assertTrue(str(policy_cache_dir()).startswith('/tmp/'))
            seed_policy_cache(bundled, target)
            self.assertEqual((target/'embeddings'/'model.onnx').read_bytes(), b'cached-model')
            (target/'embeddings'/'model.onnx').write_bytes(b'updated-runtime')
            self.assertEqual((bundled/'embeddings'/'model.onnx').read_bytes(), b'cached-model')
            with self.assertRaisesRegex(RuntimeError, 'build'):
                seed_policy_cache(root/'missing', root/'other')

    def test_storage_failure_is_503_before_model_and_is_not_exposed(self):
        from fastapi.testclient import TestClient
        from app.web import app
        from app.redis_state import StorageUnavailable
        with patch('app.web.rate_limiter') as limiter, patch('app.web.OpenRouter') as provider, TestClient(app) as client:
            limiter.allow.side_effect = StorageUnavailable('Internal secret details')
            response = client.post('/api/chat', json={'message': 'oi'})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('secret', response.text)
        provider.assert_not_called()

    def test_capacity_failure_releases_conversation_lease(self):
        from fastapi.testclient import TestClient
        from app.web import app
        from app.redis_state import StorageUnavailable
        with patch('app.web.conversations') as sessions, patch('app.web.chat_slots') as capacity, TestClient(app) as client:
            capacity.acquire.side_effect = StorageUnavailable('unavailable')
            response = client.post('/api/chat', json={'message': 'oi'})
        self.assertEqual(response.status_code, 503)
        sessions.acquire.return_value.release.assert_called_once()

    def test_forwarded_ip_is_trusted_only_on_vercel(self):
        from starlette.requests import Request
        from app.web import client_actor
        request = Request({'type': 'http', 'client': ('127.0.0.1', 1234),
                           'headers': [(b'x-vercel-forwarded-for', b'203.0.113.10')]})
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(client_actor(request), '127.0.0.1')
        with patch.dict(os.environ, {'VERCEL': '1'}, clear=True):
            self.assertEqual(client_actor(request), '203.0.113.10')
