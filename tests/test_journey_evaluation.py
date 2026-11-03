import unittest

class JourneyEvaluationTests(unittest.TestCase):
    def test_evaluation_detects_wrong_expectations(self):
        from scripts.evaluate_journeys import evaluate
        good={'id':'valid','steps':[{'path':'/api/catalog/search','body':{'category_id':5,'max_price':'10'},'expect':{'status':200,'reason':'budget'}}]}
        bad={'id':'regression','steps':[{'path':'/api/catalog/search','body':{'category_id':5,'max_price':'10'},'expect':{'status':200,'products':True}}]}
        result=evaluate([good,bad])
        self.assertEqual(result['passed'],1)
        self.assertEqual(result['total'],2)
        self.assertFalse(result['cases'][1]['passed'])
