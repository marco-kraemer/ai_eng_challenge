import unittest
from html.parser import HTMLParser
from fastapi.testclient import TestClient
from app.web import app

class Buttons(HTMLParser):
    def __init__(self):
        super().__init__(); self.prompts=[]
    def handle_starttag(self, tag, attrs):
        data=dict(attrs)
        if tag=='button' and data.get('data-intent'):
            self.prompts.append(data)

class EntryTests(unittest.TestCase):
    def test_four_real_entry_paths_and_neutral_mission(self):
        with TestClient(app) as client:
            page=client.get('/')
        parser=Buttons();parser.feed(page.text)
        self.assertEqual({p['data-intent'] for p in parser.prompts},{'products','policies','situation','store'})
        self.assertTrue(all(p['type']=='button' and len(p['data-message'])>20 for p in parser.prompts))
        self.assertIn('atendimento',page.text.lower())
        self.assertNotIn('carrinho', ' '.join(p['data-message'] for p in parser.prompts).lower())
