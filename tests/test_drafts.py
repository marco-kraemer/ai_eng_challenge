import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from fastapi.testclient import TestClient
from app.web import app,conversations
from test_policy_chat import RESULT

class DraftTests(unittest.TestCase):
    def test_draft_is_separate_and_requires_fresh_evidence(self):
        token=conversations.open(None)
        conversations.append(token,'Devolução online','Consulte o manual.',{'allowed_actions':['draft']})
        provider=Mock(); provider.generate.side_effect=[{'parts':[{'text':'store'}]},
            {'parts':[{'functionCall':{'name':'search_policies','args':{'query':'horário'}}}]},
            {'parts':[{'text':'Nosso atendimento começa às 9h.'}]}]
        with patch('app.web.OpenRouter',return_value=provider),patch('app.chat.get_policy_index') as index,TestClient(app) as client:
            index.return_value.search.return_value=RESULT
            response=client.post('/api/chat',json={'action_id':'draft','conversation_id':token})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['draft'],'Nosso atendimento começa às 9h.')
        self.assertNotEqual(response.json()['message'],response.json()['draft'])
        self.assertEqual(response.json()['sources'][0]['pages'],[2])

    def test_unverified_free_text_is_not_presented_as_client_draft(self):
        token=conversations.open(None)
        conversations.append(token,'Horários','Consulta anterior',{'allowed_actions':['draft']})
        provider=Mock();provider.generate.side_effect=[{'parts':[{'text':'store'}]},{'parts':[{'text':'Uma condição inventada sem ferramenta.'}]}]
        with patch('app.web.OpenRouter',return_value=provider),TestClient(app) as client:
            result=client.post('/api/chat',json={'action_id':'draft','conversation_id':token}).json()
        self.assertNotIn('draft',result)
        self.assertNotIn('inventada',result['message'])
