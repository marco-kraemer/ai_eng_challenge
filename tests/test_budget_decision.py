import json
import unittest
from app.query_plan import resolve_budget


class BudgetDecisionTests(unittest.TestCase):
    def test_semantic_acceptance_uses_offer_after_scope_resolution(self):
        previous = {'category_id': 4, 'max_price': '600.00'}
        offer = {'category_id': 4, 'max_price': '1127.00'}
        plan = {'category_id': 4, 'max_price': '600.00'}
        self.assertEqual(resolve_budget('accept_offer', plan, previous, offer)['max_price'], '1127.00')
        with self.assertRaises(ValueError):
            resolve_budget('accept_offer', {'category_id': 5}, previous, offer)

    def test_open_price_and_new_limit_do_not_reuse_old_offer(self):
        old = {'category_ids': [5, 9], 'max_price': '600.00'}
        offer = {'category_ids': [5, 9], 'max_price': '1000.00'}
        self.assertNotIn('max_price', resolve_budget('clear', old, old, offer))
        self.assertEqual(resolve_budget('set', {**old, 'max_price': '800.00'}, old, offer)['max_price'], '800.00')
        self.assertEqual(resolve_budget('keep', {**old, 'max_price': '1000.00'}, old, offer)['max_price'], '600.00')
