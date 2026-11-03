"""Read-only structured catalog access; read fresh data on every request."""
import csv
import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path


def name_tokens(value: str) -> set[str]:
    """Compare words and model identifiers without accents/case or GD-20/GD 20 separators."""
    normalized = ''.join(char for char in unicodedata.normalize('NFKD', value.casefold())
                         if not unicodedata.combining(char))
    normalized = re.sub(r'(?<=[a-z])[\s-]+(?=\d)', '', normalized)
    return set(re.findall(r'[a-z0-9]+', normalized))


def data_warnings(item: dict) -> list[str]:
    """Flag an objective inconsistency in the supplied data, never infer user intent."""
    keys = str(item.get('specs', {}).get('keys', ''))
    described = re.search(r'\b(\d+)\s+teclas\b', item.get('description', ''), re.IGNORECASE)
    if keys.isdigit() and described and int(keys) != int(described[1]):
        return [f'A descrição informa {described[1]} teclas, mas as especificações indicam {keys}. Confirme a ficha e o modelo com a equipe antes de comprar.']
    return []


class Catalog:
    def __init__(self, directory: Path):
        self.directory = directory

    def search(self, *, category_id=None, category_ids=None, min_price='0', max_price=None,
               in_stock=True, status='active', limit=5, offset=0, query=None):
        try:
            if query is not None and (not isinstance(query, str) or not 1 <= len(query) <= 200 or not name_tokens(query)):
                raise ValueError('Invalid name query')
            terms = name_tokens(query) if query is not None else set()
            low = Decimal(str(min_price))
            high = Decimal(str(max_price)) if max_price is not None else None
            if (not low.is_finite() or low < 0 or
                high is not None and (not high.is_finite() or high < low) or
                type(limit) is not int or not 1 <= limit <= 10 or
                type(offset) is not int or offset < 0 or
                type(in_stock) is not bool or
                category_id is not None and (type(category_id) is not int or category_id <= 0) or
                category_ids is not None and (not isinstance(category_ids, list) or len(category_ids) > 9 or
                    any(type(i) is not int or i <= 0 for i in category_ids) or len(set(category_ids)) != len(category_ids)) or
                category_id is not None and category_ids is not None):
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
                    if (not terms.issubset(name_tokens(row['name'])) or price < low or high is not None and price > high or
                        category_id is not None and category != category_id or
                        category_ids and category not in category_ids or
                        in_stock and stock <= 0 or row['status'] != status):
                        continue
                    matches.append({
                        'product_id': int(row['product_id']), 'name': row['name'],
                        'price_brl': str(price.quantize(Decimal('0.01'))),
                        'category_id': category, 'stock_quantity': stock,
                        'status': row['status'], 'description': row['description'],
                        'specs': json.loads(row['specs']),
                    })
            for item in matches:
                item['warnings'] = data_warnings(item)
            # Broad searches show a representative mix; paginate only after filtering.
            if category_id is None and not terms:
                groups: dict[int, list] = {}
                for product in matches:
                    groups.setdefault(product['category_id'], []).append(product)
                matches = [group[position] for position in range(max((len(g) for g in groups.values()), default=0))
                           for group in groups.values() if position < len(group)]
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
                item['warnings'] = data_warnings(item)
                if ceiling is not None:
                    item['budget_difference_brl']=str(max(price-ceiling,Decimal(0)).quantize(Decimal('0.01')))
                items.append(item)
            return {'status':'found','items':items}
        except (OSError,ValueError,KeyError,InvalidOperation):
            return {'status':'error','items':[]}

    def categories(self) -> dict:
        try:
            with (self.directory/'categories.csv').open(newline='',encoding='utf-8-sig') as stream:
                items=[{'category_id':int(row['category_id']),'name':row['name'],'description':row['description']} for row in csv.DictReader(stream)]
            return {'status':'found','items':items}
        except (OSError,ValueError,KeyError):
            return {'status':'error','items':[]}

    def available_categories(self) -> dict:
        categories = self.categories()
        if categories['status'] == 'error':
            return categories
        try:
            with (self.directory / 'products.csv').open(newline='', encoding='utf-8-sig') as stream:
                available = {int(row['category_id']) for row in csv.DictReader(stream)
                             if row['status'] == 'active' and int(row['stock_quantity']) > 0}
            items = [item for item in categories['items'] if item['category_id'] in available]
            return {'status': 'found' if items else 'not_found', 'items': items}
        except (OSError, ValueError, KeyError):
            return {'status': 'error', 'items': []}

    def cheapest_available(self, category_id: int | None = None, *, category_ids: list[int] | None = None) -> dict:
        """Consider every matching row, including products beyond the first page."""
        offset = 0
        cheapest = None
        while True:
            page = self.search(category_id=category_id, category_ids=category_ids, limit=10, offset=offset)
            if page['status'] in ('error', 'invalid'):
                return page
            for product in page['items']:
                if cheapest is None or Decimal(product['price_brl']) < Decimal(cheapest['price_brl']):
                    cheapest = product
            if page.get('next_offset') is None:
                break
            offset = page['next_offset']
        return {'status': 'found' if cheapest else 'not_found', 'items': [cheapest] if cheapest else []}
