import unittest
from app.actions import next_actions, resolve_action

class ActionTests(unittest.TestCase):
    def test_only_relevant_supported_next_steps(self):
        products=[{'product_id':81},{'product_id':82}]
        actions=next_actions({'products':products,'sources':[]})
        self.assertIn('compare',[a['id'] for a in actions])
        self.assertIn('cheaper',[a['id'] for a in actions])
        self.assertNotIn('reserve',[a['id'] for a in actions])
        self.assertEqual([a['id'] for a in next_actions({'needs_return_channel':True})],['online','physical'])
        self.assertIn('policy_details',[a['id'] for a in next_actions({'sources':[{'id':'s2-0'}]})])

    def test_action_cannot_be_forged_or_reuse_other_conversation(self):
        with self.assertRaises(ValueError):resolve_action('compare',{})
        with self.assertRaises(ValueError):resolve_action('run_code',{'allowed_actions':['run_code']})
        self.assertIn('diferença',resolve_action('compare',{'allowed_actions':['compare']}))
