import csv,tempfile,unittest
from pathlib import Path
from app.commerce import Promotions, quote_price

class PromotionTests(unittest.TestCase):
    def test_rounding_validation_and_no_pix_stacking(self):
        quote=quote_price('199.99','15',pix=True)
        self.assertEqual(quote['price_brl'],'169.99')
        self.assertFalse(quote['pix_applied'])
        for discount in ['-1','101','NaN']:
            with self.assertRaises(ValueError):quote_price('100',discount)

    def test_only_confirmed_active_promotions_and_error_distinction(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            (path/'products.csv').write_text('product_id,name,price_brl,category_id,stock_quantity,status,description,specs\n1,Violão,100,5,2,active,Teste,{}\n2,Outro,200,5,0,active,Teste,{}\n')
            (path/'promotions.csv').write_text('promotion_id,product_id,discount_percent,description,is_active\n1,1,10,Oferta,1\n2,2,30,Expirada,0\n')
            result=Promotions(path).search()
            self.assertEqual(result['status'],'found')
            self.assertEqual(len(result['items']),1)
            self.assertEqual(result['items'][0]['price_brl'],'90.00')
            self.assertEqual(Promotions(path).search(product_id=2)['status'],'not_found')
            self.assertEqual(Promotions(path).search(max_price='NaN')['status'],'invalid')
            (path/'promotions.csv').write_text('bad,data\n1,2\n')
            self.assertEqual(Promotions(path).search()['status'],'error')
