import tempfile
import unittest
from pathlib import Path
import numpy as np
from app.policies import PolicyIndex, extract_chunks

PDF = Path('data/políticas_da_loja.pdf')

class FakeEncoder:
    model_id = 'test-encoder-v1'
    def __init__(self):
        self.documents_encoded = 0
    def passages(self, texts):
        self.documents_encoded += 1
        return np.array([[float('Horário de Funcionamento' in t), float('Arrependimento' in t), 0.1] for t in texts])
    def query(self, text):
        if text == 'abrem quando?':
            return np.array([1., 0., 0.])
        if text == 'comprei pela internet e me arrependi':
            return np.array([0., 1., 0.])
        return np.array([0., 0., -1.])

class PolicyTests(unittest.TestCase):
    def test_extract_preserves_sections_tables_and_continuations(self):
        chunks = extract_chunks(PDF)
        hours = next(c for c in chunks if c.section == '2')
        self.assertEqual(hours.pages, (2,))
        for phrase in ['09:00', '18:00', 'Sábado', 'Domingo']:
            self.assertIn(phrase, hours.text)
        shipping = next(c for c in chunks if c.section == '5.2')
        self.assertEqual(shipping.pages, (4, 5))
        self.assertIn('SEDEX', shipping.text)
        self.assertTrue(all(len(c.text) <= 1800 for c in chunks))
        self.assertTrue(all(len(c.text.splitlines()) > 1 for c in chunks))
        self.assertFalse(any(c.title.startswith('Saudação:') for c in chunks))

    def test_semantic_and_lexical_retrieval_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            encoder = FakeEncoder()
            index = PolicyIndex(PDF, Path(directory), encoder)
            hours = index.search('abrem quando?')
            self.assertEqual(hours['status'], 'found')
            self.assertEqual(hours['items'][0]['section'], '2')
            self.assertEqual(hours['items'][0]['pages'], [2])
            self.assertEqual(index.search('comprei pela internet e me arrependi')['items'][0]['section'], '4.1')
            self.assertEqual(index.search('PIX', mode='lexical')['items'][0]['pages'], [3])
            PolicyIndex(PDF, Path(directory), encoder)
            self.assertEqual(encoder.documents_encoded, 1)

    def test_absence_limits_and_invalid_query(self):
        with tempfile.TemporaryDirectory() as directory:
            index = PolicyIndex(PDF, Path(directory), FakeEncoder())
            self.assertEqual(index.search('estacionamento subterrâneo gratuito')['status'], 'not_found')
            self.assertEqual(index.search('')['status'], 'invalid')
            self.assertEqual(index.search('horário', limit=100)['status'], 'invalid')
            self.assertLessEqual(len(index.search('PIX')['items']), 3)

    def test_conflicting_conditions_and_contacts_are_retrieved_together(self):
        with tempfile.TemporaryDirectory() as directory:
            index = PolicyIndex(PDF, Path(directory), FakeEncoder())
            payments = index.search('parcelamento', mode='lexical')
            self.assertTrue({'3', '3.1'}.issubset({c['section'] for c in payments['items']}))
            self.assertTrue(payments['warnings'])
            contacts = index.search('telefone WhatsApp', mode='lexical')
            text = ' '.join(c['text'] for c in contacts['items'])
            self.assertIn('3341-4444', text)
            self.assertIn('3321-4500', text)
            self.assertTrue(contacts['warnings'])


class LexicalPriorityTests(unittest.TestCase):
    def test_exact_accessory_evidence_survives_semantic_distraction(self):
        class DistractedEncoder(FakeEncoder):
            def passages(self, texts):
                return np.array([[0., 0., -1. if ('O que Não Cobre a Garantia' in text or 'Itens Não Elegíveis' in text) else 1.] for text in texts])
        with tempfile.TemporaryDirectory() as directory:
            index = PolicyIndex(PDF, Path(directory), DistractedEncoder())
            sections = {item['section'] for item in index.search('vendem cabos e palhetas?')['items']}
            self.assertTrue({'1', '7.1'}.issubset(sections))
