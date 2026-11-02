import unittest
from unittest.mock import Mock,patch
import httpx
from fastapi.testclient import TestClient
from app.limits import RateLimiter
from app.web import app
from app.openrouter import OpenRouter

class LimitTests(unittest.TestCase):
    def test_window_and_actor_bounds(self):
        now=[0.]
        limiter=RateLimiter(window=60,max_actors=2,clock=lambda:now[0])
        self.assertTrue(limiter.allow('chat:one',1)[0])
        self.assertFalse(limiter.allow('chat:one',1)[0])
        for key in ['two','three']:limiter.allow(key,1)
        self.assertLessEqual(len(limiter.buckets),2)
        now[0]=61
        self.assertTrue(limiter.allow('chat:one',1)[0])

    def test_large_body_is_rejected_before_model(self):
        with patch('app.web.OpenRouter') as model,TestClient(app) as client:
            response=client.post('/api/chat',content=b'x'*17000,headers={'Content-Type':'application/json'})
        self.assertEqual(response.status_code,413)
        model.assert_not_called()

    def test_429_and_retry_after(self):
        provider=Mock();provider.generate.side_effect=RuntimeError('unavailable')
        with patch('app.web.rate_limiter',RateLimiter()),patch('app.web.CHAT_RATE',1),patch('app.web.OpenRouter',return_value=provider),TestClient(app) as client:
            client.post('/api/chat',json={'message':'Olá'})
            response=client.post('/api/chat',json={'message':'Olá'})
        self.assertEqual(response.status_code,429)
        self.assertIn('Retry-After',response.headers)

    def test_retry_is_bounded_and_quota_is_not_retried(self):
        request=httpx.Request('POST','https://openrouter.ai/api/v1/chat/completions')
        unavailable=httpx.Response(503,request=request)
        success=httpx.Response(200,json={'choices':[{'message':{'content':'Olá'}}]},request=request)
        with patch('app.openrouter.httpx.post',side_effect=[unavailable,success]) as post:
            self.assertEqual(OpenRouter(api_key='test').generate([],[])['parts'][0]['text'],'Olá')
            self.assertEqual(post.call_count,2)
        with patch('app.openrouter.httpx.post',return_value=httpx.Response(429,request=request)) as post:
            with self.assertRaises(RuntimeError):OpenRouter(api_key='test').generate([],[])
            self.assertEqual(post.call_count,1)

    def test_permanent_errors_log_status_without_provider_body_or_credentials(self):
        response=httpx.Response(401,json={'error':'secret-provider-details'},request=httpx.Request('POST','https://openrouter.ai'))
        with patch('app.openrouter.httpx.post',return_value=response),self.assertLogs('app.openrouter',level='WARNING') as logs:
            with self.assertRaises(RuntimeError):OpenRouter(api_key='private-test-key').generate([],[])
        self.assertIn('401',str(logs.output))
        self.assertNotIn('private-test-key',str(logs.output))
        self.assertNotIn('secret-provider-details',str(logs.output))

    def test_context_limit_prevents_another_provider_call(self):
        from app.chat import Chat
        from app.catalog import Catalog
        from pathlib import Path
        provider=Mock()
        history=[{'role':'user','parts':[{'text':'X'*50000}]}]
        with self.assertRaises(RuntimeError):Chat(provider,Catalog(Path('data'))).reply('Olá',history=history)
        provider.generate.assert_not_called()
