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
