import unittest
from html.parser import HTMLParser
from fastapi.testclient import TestClient
from app.web import app

class Buttons(HTMLParser):
    def __init__(self):
        super().__init__(); self.intents=[]
    def handle_starttag(self,tag,attrs):
        data=dict(attrs)
        if tag=='button' and data.get('data-intent'):self.intents.append(data)

class EntryTests(unittest.TestCase):
    def test_customer_entry_has_no_staff_copy_or_arbitrary_query(self):
        with TestClient(app) as client:page=client.get('/')
        parser=Buttons();parser.feed(page.text)
        self.assertEqual({p['data-intent'] for p in parser.intents},{'products','purchase','order','store'})
        self.assertTrue(all('data-message' not in p for p in parser.intents))
        for forbidden in ['Um bom atendimento começa','Conhecimento que dá o tom','Orientar um atendimento','Um cliente recebeu','Preparar resposta ao cliente','Mensagem para o cliente']:
            self.assertNotIn(forbidden,page.text)
        self.assertIn('Como posso ajudar?',page.text)
