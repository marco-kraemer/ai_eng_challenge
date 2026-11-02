import unittest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.web import app

class SessionAPITests(unittest.TestCase):
    def test_context_is_private_to_page_and_reset_discards_it(self):
        calls=[]
        provider=Mock()
        def generate(contents,tools,**kwargs):
            if kwargs.get('system'):
                return {'parts':[{'text':'store'}]}
            calls.append(contents)
            return {'parts':[{'text':'Posso ajudar com as opções.'}]}
        provider.generate.side_effect=generate
        with patch('app.web.OpenRouter',return_value=provider),TestClient(app) as client:
            first=client.post('/api/chat',json={'message':'Quero violões até 600'}).json()
            token=first['conversation_id']
            client.post('/api/chat',json={'message':'Mostre os mais baratos','conversation_id':token})
            self.assertIn('600',str(calls[-1]))
            client.post('/api/chat',json={'message':'Olá'})
            self.assertNotIn('600',str(calls[-1]))
            self.assertEqual(client.post('/api/conversation/reset',json={'conversation_id':token}).status_code,204)
            client.post('/api/chat',json={'message':'Oi','conversation_id':token})
            self.assertNotIn('600',str(calls[-1]))
