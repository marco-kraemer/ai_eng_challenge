import unittest
from unittest.mock import Mock
from scripts.evaluate_agent import BudgetedProvider


class EvaluationBudgetTests(unittest.TestCase):
    def test_budget_and_call_caps_stop_before_provider(self):
        model = Mock()
        bounded = BudgetedProvider(model, budget_usd=.001, max_calls=10)
        with self.assertRaisesRegex(RuntimeError, 'avaliação'):
            bounded.generate([], [])
        model.generate.assert_not_called()
        model.generate.return_value = {'parts': [{'text': 'ok'}], '_model': 'gpt-4.1-mini',
            '_usage': {'prompt_tokens': 10, 'completion_tokens': 2}}
        bounded = BudgetedProvider(model, budget_usd=.05, max_calls=1)
        bounded.generate([], [])
        self.assertGreater(bounded.spent, 0)
        with self.assertRaisesRegex(RuntimeError, 'avaliação'):
            bounded.generate([], [])
        self.assertEqual(model.generate.call_count, 1)
