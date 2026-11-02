"""Read-only structured catalog access; read fresh data on every request."""
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


class Catalog:
    def __init__(self, directory: Path):
        self.directory = directory

    def search(self, *, category_id=None, min_price='0', max_price=None,
               in_stock=True, status='active', limit=5, offset=0):
        try:
            low = Decimal(str(min_price))
            high = Decimal(str(max_price)) if max_price is not None else None
            if (not low.is_finite() or low < 0 or
                high is not None and (not high.is_finite() or high < low) or
                type(limit) is not int or not 1 <= limit <= 10 or
                type(offset) is not int or offset < 0 or
                type(in_stock) is not bool or
                category_id is not None and type(category_id) is not int):
                raise ValueError('Invalid filters')
        except (InvalidOperation, ValueError, TypeError):
            return {'status': 'invalid', 'items': []}
        try:
            with (self.directory / 'products.csv').open(newline='', encoding='utf-8-sig') as stream:
                matches = []
                for row in csv.DictReader(stream):
                    price = Decimal(row['price_brl'])
                    stock = int(row['stock_quantity'])
                    category = int(row['category_id'])
                    if (price < low or high is not None and price > high or
                        category_id is not None and category != category_id or
                        in_stock and stock <= 0 or row['status'] != status):
                        continue
                    matches.append({
                        'product_id': int(row['product_id']), 'name': row['name'],
                        'price_brl': str(price.quantize(Decimal('0.01'))),
                        'category_id': category, 'stock_quantity': stock,
                        'status': row['status'], 'description': row['description'],
                        'specs': json.loads(row['specs']),
                    })
            items = matches[offset:offset + limit]
            return {'status': 'found' if items else 'not_found', 'items': items,
                    'next_offset': offset + limit if offset + limit < len(matches) else None}
        except (OSError, ValueError, KeyError, InvalidOperation):
            return {'status': 'error', 'items': []}

    def compare(self, product_ids: list[int], budget=None):
        try:
            if not isinstance(product_ids,list) or not 2 <= len(product_ids) <= 4 or any(type(i) is not int for i in product_ids):
                raise ValueError('Invalid IDs')
            ceiling=Decimal(str(budget)) if budget is not None else None
            if ceiling is not None and (not ceiling.is_finite() or ceiling<0):
                raise ValueError('Invalid budget')
        except (ValueError,InvalidOperation,TypeError):
            return {'status':'invalid','items':[]}
        try:
            with (self.directory/'products.csv').open(newline='',encoding='utf-8-sig') as stream:
                rows={int(row['product_id']):row for row in csv.DictReader(stream)}
            items=[]
            for identifier in dict.fromkeys(product_ids):
                if identifier not in rows:
                    return {'status':'not_found','items':[]}
                row=rows[identifier]
                price=Decimal(row['price_brl'])
                item={'product_id':identifier,'name':row['name'],'price_brl':str(price.quantize(Decimal('0.01'))),
                      'category_id':int(row['category_id']),'status':row['status'],'stock_quantity':int(row['stock_quantity']),
                      'description':row['description'],'specs':json.loads(row['specs'])}
                if ceiling is not None:
                    item['budget_difference_brl']=str(max(price-ceiling,Decimal(0)).quantize(Decimal('0.01')))
                items.append(item)
            return {'status':'found','items':items}
        except (OSError,ValueError,KeyError,InvalidOperation):
            return {'status':'error','items':[]}
