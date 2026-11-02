import unittest
from pathlib import Path
from unittest.mock import Mock
from app.conversations import ConversationStore
from app.catalog import Catalog
from app.assistant import StoreAssistant

class ConversationTests(unittest.TestCase):
    def test_isolated_bounded_expiring_context(self):
        clock=[0.]
        store=ConversationStore(max_sessions=2,ttl=10,clock=lambda:clock[0])
        first=store.open(None); second=store.open(None)
        store.append(first,'Violão até 600','Qual tipo?')
        self.assertEqual(store.history(second),[])
        for n in range(20):store.append(first,'X'*2000,'Y'*2000)
        self.assertLessEqual(sum(len(m['parts'][0]['text']) for m in store.history(first)),8000)
        store.reset(first)
        self.assertEqual(store.history(first),[])
        clock[0]=11
        self.assertNotEqual(store.open(second),second)
        self.assertLessEqual(len(store.sessions),2)

    def test_followup_context_reaches_classifier_and_agent(self):
        provider=Mock()
        provider.generate.side_effect=[{'parts':[{'text':'store'}]},{'parts':[{'text':'Vou consultar as opções mais baratas.'}]}]
        history=[{'role':'user','parts':[{'text':'Quero violões até 600'}]}, {'role':'model','parts':[{'text':'Prefere nylon?'}]}]
        StoreAssistant(provider,Catalog(Path('data'))).reply('Mostre opções',history=history)
        for call in provider.generate.call_args_list:
            self.assertIn('600',str(call.args[0]))

    def test_comparison_uses_fresh_catalog_and_deterministic_budget_difference(self):
        result=Catalog(Path('data')).compare([81,82],budget='600')
        self.assertEqual(result['status'],'found')
        self.assertEqual(result['items'][0]['budget_difference_brl'],'0.00')
        self.assertEqual(result['items'][1]['budget_difference_brl'],'249.00')
        self.assertIn('specs',result['items'][0])
        self.assertEqual(Catalog(Path('data')).compare([81],budget='NaN')['status'],'invalid')
