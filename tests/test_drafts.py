"""Regression: internal staff drafting is not part of the customer chatbot."""
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.web import app,conversations

class CustomerActionTests(unittest.TestCase):
    def test_legacy_staff_action_is_rejected_before_model(self):
        token=conversations.open(None)
        conversations.append(token,'Horários','Consulta anterior',{'allowed_actions':['draft']})
        with patch('app.web.OpenRouter') as provider,TestClient(app) as client:
            response=client.post('/api/chat',json={'action_id':'draft','conversation_id':token})
        self.assertEqual(response.status_code,422)
        provider.assert_not_called()
