import unittest
from pathlib import Path
from unittest.mock import Mock
from app.catalog import Catalog
from app.chat import Chat


class GroundingWarningTests(unittest.TestCase):
    def test_conflicting_policy_gets_explicit_instruction_without_reconciling_rules(self):
        model = Mock(); model.generate.return_value = {'parts': [{'text': 'Confirme a condição com a loja.'}]}
        evidence = {'status': 'found', 'items': [], 'warnings': ['Mínimos conflitantes.']}
        Chat(model, Catalog(Path('data'))).reply('Qual o mínimo?', policy_result=evidence)
        system = model.generate.call_args.kwargs['system']
        self.assertIn('Não transforme condições conflitantes em uma regra única', system)
        self.assertIn('Mínimos conflitantes.', str(model.generate.call_args.args))
