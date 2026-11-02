"""Weak prototype verification; credentials and customer records never reach the LLM."""
import csv
import hmac
import re
from datetime import date
from pathlib import Path

class Orders:
    def __init__(self,directory: Path):self.directory=directory

    def verify(self,order_id: int,email: str) -> dict:
        if type(order_id) is not int or order_id<=0 or not isinstance(email,str) or len(email)>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email.strip()):
            return {'status':'invalid'}
        try:
            with (self.directory/'orders.csv').open(newline='',encoding='utf-8-sig') as stream:
                order=next((row for row in csv.DictReader(stream) if int(row['order_id'])==order_id),None)
            if order is None:return {'status':'not_found'}
            with (self.directory/'customers.csv').open(newline='',encoding='utf-8-sig') as stream:
                customer=next((row for row in csv.DictReader(stream) if row['customer_id']==order['customer_id']),None)
            if customer is None:raise ValueError('Orphaned order')
            if not hmac.compare_digest(customer['email'].strip().casefold().encode(),email.strip().casefold().encode()):
                return {'status':'not_found'}
            status=order['status'].strip()
            if not status:raise ValueError('Missing status')
            estimated=order.get('estimated_delivery','').strip() or None
            if estimated:date.fromisoformat(estimated)
            return {'status':'found','order':{'status':status,'estimated_delivery':estimated,'tracking_code':order.get('tracking_code','').strip() or None}}
        except (OSError,ValueError,KeyError):
            return {'status':'error'}
