"""Read-only promotional quotes; all arithmetic uses Decimal with explicit rounding."""
import csv
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

CENT=Decimal('0.01')

def quote_price(base, discount, pix=False) -> dict:
    try:
        price,percent=Decimal(str(base)),Decimal(str(discount))
        if not price.is_finite() or price<0 or not percent.is_finite() or not 0<percent<=100:
            raise ValueError('Invalid quote')
        return {'original_price_brl':str(price.quantize(CENT,rounding=ROUND_HALF_UP)),
                'price_brl':str((price*(1-percent/100)).quantize(CENT,rounding=ROUND_HALF_UP)),
                'discount_percent':str(percent),'pix_applied':False,
                'payment_note':'Desconto PIX não acumulado com promoção.' if pix else 'Preço promocional; desconto PIX não cumulativo.'}
    except (InvalidOperation,TypeError,ValueError):
        raise ValueError('Preço ou desconto inválido.') from None

class Promotions:
    def __init__(self,directory: Path):
        self.directory=directory

    def search(self,product_id=None,category_id=None,max_price=None,limit=5,offset=0) -> dict:
        try:
            ceiling=Decimal(str(max_price)) if max_price is not None else None
            if (ceiling is not None and (not ceiling.is_finite() or ceiling<0) or
                    product_id is not None and type(product_id) is not int or
                    category_id is not None and type(category_id) is not int or
                    type(limit) is not int or not 1<=limit<=5 or type(offset) is not int or offset<0):
                raise ValueError('Invalid query')
        except (InvalidOperation,ValueError,TypeError):
            return {'status':'invalid','items':[]}
        try:
            with (self.directory/'products.csv').open(newline='',encoding='utf-8-sig') as stream:
                products={int(row['product_id']):row for row in csv.DictReader(stream)}
            with (self.directory/'promotions.csv').open(newline='',encoding='utf-8-sig') as stream:
                offers=list(csv.DictReader(stream))
            best: dict[int,dict]={}
            for offer in offers:
                if offer['is_active'] not in ('0','1'):
                    raise ValueError('Invalid active flag')
                if offer['is_active']=='0':continue
                identifier=int(offer['product_id'])
                row=products[identifier]
                category=int(row['category_id'])
                if row['status']!='active' or product_id is not None and identifier!=product_id or category_id is not None and category!=category_id:
                    continue
                quote=quote_price(row['price_brl'],offer['discount_percent'])
                if ceiling is not None and Decimal(quote['price_brl'])>ceiling:continue
                item={'product_id':identifier,'name':row['name'],'category_id':category,'stock_quantity':int(row['stock_quantity']),
                      'status':row['status'],'description':row['description'],'specs':json.loads(row['specs']),
                      'promotion_id':int(offer['promotion_id']),'promotion_description':offer['description'],**quote}
                if identifier not in best or Decimal(item['price_brl'])<Decimal(best[identifier]['price_brl']):best[identifier]=item
            found=sorted(best.values(),key=lambda item:(Decimal(item['price_brl']),item['product_id']))
            items=found[offset:offset+limit]
            return {'status':'found' if items else 'not_found','items':items,
                    'next_offset':offset+limit if offset+limit<len(found) else None}
        except (OSError,KeyError,ValueError,InvalidOperation):
            return {'status':'error','items':[]}
