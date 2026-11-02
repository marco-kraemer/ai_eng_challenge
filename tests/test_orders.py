import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from fastapi.testclient import TestClient
from app.orders import Orders
from app.assistant import StoreAssistant
from app.catalog import Catalog
from app.web import app

class OrderTests(unittest.TestCase):
    def test_verification_minimizes_fields_and_mismatch_is_generic(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            (path/'customers.csv').write_text('customer_id,name,email,phone\n7,Segredo,cliente@example.test,999\n')
            (path/'orders.csv').write_text('order_id,customer_id,status,estimated_delivery,tracking_code,notes,total_brl\n42,7,shipped,2026-11-10,BR123,Nota interna,100\n')
            orders=Orders(path)
            good=orders.verify(42,' CLIENTE@example.test ')
            self.assertEqual(set(good['order']),{'status','estimated_delivery','tracking_code'})
            self.assertNotIn('Segredo',str(good));self.assertNotIn('Nota interna',str(good))
            self.assertEqual(orders.verify(42,'errado@example.test'),orders.verify(99,'cliente@example.test'))
            self.assertEqual(orders.verify(0,'bad')['status'],'invalid')
            self.assertEqual(Orders(Path('/nonexistent')).verify(42,'cliente@example.test')['status'],'error')

    def test_email_in_chat_never_reaches_model(self):
        provider=Mock()
        result=StoreAssistant(provider,Catalog(Path('data'))).reply('Pedido 42 cliente@example.test')
        self.assertTrue(result['order_verification_required'])
        provider.generate.assert_not_called()

    def test_order_endpoint_does_not_call_model(self):
        with patch('app.web.Orders') as orders,patch('app.web.OpenRouter') as model,TestClient(app) as client:
            orders.return_value.verify.return_value={'status':'found','order':{'status':'shipped','estimated_delivery':None,'tracking_code':None}}
            response=client.post('/api/orders/verify',json={'order_id':42,'email':'cliente@example.test'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['order']['status'],'shipped')
        model.assert_not_called()
