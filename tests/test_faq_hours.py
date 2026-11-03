import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from fastapi.testclient import TestClient
from app.web import app
from app.limits import RateLimiter
from app.assistant import StoreAssistant, REFUSAL
from app.catalog import Catalog

class HoursFAQTests(unittest.TestCase):
    def setUp(self):
        p=patch('app.web.rate_limiter',RateLimiter());p.start();self.addCleanup(p.stop)

    def test_general_weekday_and_weekend_hours_do_not_call_model(self):
        provider=Mock();provider.generate.side_effect=RuntimeError('No inference')
        questions=[('Que horas vocês abrem?','09:00 às 18:00'),('Quais são os horários da loja?','Sábado'),
                   ('Qual o horário de funcionamento?','09:00 às 13:00'),('Vocês abrem no sábado?','09:00 às 13:00'),
                   ('A loja abre na segunda-feira?','09:00 às 18:00'),('Abrem aos domingos?','Fechado'),
                   ('Qual o horário nos feriados?','Fechado')]
        with patch('app.web.OpenRouter',return_value=provider),TestClient(app) as client:
            for question,expected in questions:
                response=client.post('/api/chat',json={'message':question})
                self.assertEqual(response.status_code,200,question)
                self.assertIn(expected,response.json()['message'])
                self.assertEqual(response.json()['sources'][0]['pages'],[2])
            provider.generate.assert_not_called()

    def test_relative_dates_exceptions_and_mixed_requests_fall_through(self):
        for question in ('Vocês abrem hoje?','Que horas abre amanhã?','Abrem no Natal?',
                         'Vocês abrem no sábado dia 25?','Abrem domingo e me ensine Python?',
                         'Qual o prazo para abrir uma devolução?','E no sábado?'):
            provider=Mock();provider.generate.return_value={'parts':[{'text':'offtopic'}]}
            result=StoreAssistant(provider,Catalog(Path('data'))).reply(question)
            self.assertEqual(result['message'],REFUSAL)
            self.assertEqual(provider.generate.call_count,1)

    def test_hour_shortcut_keeps_session_and_does_not_cache_user_context(self):
        from app.web import conversations
        provider=Mock();provider.generate.side_effect=RuntimeError('No inference')
        with patch('app.web.OpenRouter',return_value=provider),TestClient(app) as client:
            address=client.post('/api/chat',json={'message':'Onde vocês ficam?'}).json()
            hours=client.post('/api/chat',json={'message':'Que horas vocês abrem?','conversation_id':address['conversation_id']}).json()
        self.assertEqual(hours['conversation_id'],address['conversation_id'])
        self.assertEqual(conversations.state(hours['conversation_id'])['topic'],'policies')
        self.assertTrue(hours['actions'])
        provider.generate.assert_not_called()
