import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from app.assistant import StoreAssistant
from app.catalog import Catalog
from app.chat import Chat

RESULT = {'status':'found','items':[{'id':'s2-0','section':'2','title':'Horário de Funcionamento','pages':[2],'text':'Segunda a Sexta-feira 09:00 às 18:00. Sábado 09:00 às 13:00. Domingo e Feriados Fechado.'}],'warnings':[]}

class PolicyChatTests(unittest.TestCase):
    def test_policy_tool_returns_sources_through_api_contract(self):
        provider=Mock()
        provider.generate.side_effect=[{'parts':[{'text':'store'}]},
            {'parts':[{'functionCall':{'name':'search_policies','args':{'query':'horário de funcionamento'}}}]},
            {'parts':[{'text':'Abrimos às 9h de segunda a sábado. Fonte: manual, p. 2.'}]}]
        with patch('app.chat.get_policy_index') as factory:
            factory.return_value.search.return_value=RESULT
            result=StoreAssistant(provider,Catalog(Path('data'))).reply('Que horas vocês abrem em datas especiais?')
        self.assertEqual(result['sources'][0]['pages'],[2])
        self.assertIn('9h', result['message'])
        self.assertEqual(result['products'],[])
        self.assertEqual(provider.generate.call_args.args[0][-1]['parts'][0]['functionResponse']['response'],RESULT)

    def test_failure_is_not_absence_and_invalid_args_do_not_load_index(self):
        chat=Chat(Mock(),Catalog(Path('data')))
        with patch('app.chat.get_policy_index') as factory:
            self.assertEqual(chat.dispatch('search_policies',{'query':'horários','extra':'bad'})['status'],'invalid')
            factory.assert_not_called()
            factory.side_effect=OSError('missing PDF')
            self.assertEqual(chat.dispatch('search_policies',{'query':'horários'})['status'],'error')
        self.assertEqual(chat.sources,{})

    def test_not_found_never_produces_a_source(self):
        chat=Chat(Mock(),Catalog(Path('data')))
        with patch('app.chat.get_policy_index') as factory:
            factory.return_value.search.return_value={'status':'not_found','items':[],'warnings':[]}
            self.assertEqual(chat.dispatch('search_policies',{'query':'estacionamento'})['status'],'not_found')
            self.assertEqual(chat.sources,{})

    def test_http_response_includes_verifiable_snippets(self):
        from fastapi.testclient import TestClient
        from app.web import app
        provider=Mock()
        provider.generate.side_effect=[{'parts':[{'text':'store'}]},
            {'parts':[{'functionCall':{'name':'search_policies','args':{'query':'horário de funcionamento'}}}]},
            {'parts':[{'text':'De segunda a sexta, das 9h às 18h. Manual, p. 2.'}]}]
        with patch('app.web.build_provider',return_value=provider), patch('app.chat.get_policy_index') as index, TestClient(app) as client:
            index.return_value.search.return_value=RESULT
            response=client.post('/api/chat',json={'message':'Que horas vocês abrem em datas especiais?'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['sources'][0]['id'],'s2-0')
        self.assertIn('18:00',response.json()['sources'][0]['text'])
