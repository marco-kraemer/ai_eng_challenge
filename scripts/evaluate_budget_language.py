"""Opt-in live evaluation of contextual budget language, using the configured provider.

Run with --live. Sends synthetic conversations to the configured provider; uses real catalog tools.
Contract unit tests do not replace this model-quality check.
"""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from app.assistant import StoreAssistant
from app.catalog import Catalog
from app.catalog_flow import catalog_reply
from app.llm import build_provider


class ObservedProvider:
    def __init__(self):
        self.provider = build_provider()
        self.tool_calls = []
        self.classifications = []

    def generate(self, contents, tools, **options):
        response = self.provider.generate(contents, tools, **options)
        if options.get('system'):
            self.classifications.append([part['text'] for part in response.get('parts', []) if 'text' in part])
        self.tool_calls.extend(part['functionCall'] for part in response.get('parts', []) if 'functionCall' in part)
        return response


def evaluate():
    catalog = Catalog(Path('data'))
    offer, _, pending = catalog_reply(catalog, 2, '500')
    guitar_history = [
        {'role': 'user', 'parts': [{'text': 'Sou estudante e iniciante e quero comprar um violão. Me ajuda.'}]},
        {'role': 'model', 'parts': [{'text': 'Qual orçamento você tem em mente?'}]},
    ]
    offer_history = [
        {'role': 'user', 'parts': [{'text': 'Quero ver baixos até R$ 500.'}]},
        {'role': 'model', 'parts': [{'text': offer['message']}]},
    ]
    cases = [
        ('tanto-faz', 'tanto faz', guitar_history, {'topic': 'products'}, 5, None),
        ('free-wording', 'Prefiro olhar umas opções primeiro, o dinheiro eu vejo depois.', guitar_history, {'topic': 'products'}, 5, None),
        ('accept-offer', 'Fechou, me mostra essas opções então.', offer_history, pending, 2, offer['recovery']['price_brl']),
        ('reject-offer', 'Esse aumento não cabe no meu bolso, deixa pra lá.', offer_history, pending, None, '500.00'),
    ]
    results = []
    for name, message, history, state, category, budget in cases:
        provider = ObservedProvider()
        assistant = StoreAssistant(provider, catalog, state=state)
        start = time.monotonic()
        try:
            response = assistant.reply(message, history=history)
            context = assistant.context()
            products = response['products']
            passed = (context['preferences'].get('max_price') == budget and not context['pending_budget']
                      and (bool(products) and all(p['category_id'] == category for p in products)
                           if category is not None else not products))
            row = {'case': name, 'passed': passed, 'seconds': round(time.monotonic()-start, 2),
                   'classification': provider.classifications, 'tools': provider.tool_calls, 'message': response['message'],
                   'product_count': len(products), 'preferences': context['preferences']}
        except (RuntimeError, ValueError) as error:
            row = {'case': name, 'passed': False, 'error': str(error), 'tools': provider.tool_calls}
        results.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Explicitly enable real provider requests.')
    args = parser.parse_args()
    if not args.live:
        parser.error('Use --live to enable real provider requests.')
    load_dotenv()
    results = evaluate()
    passed = sum(row['passed'] for row in results)
    print(f'Live budget language: {passed}/{len(results)} passed.')
    return 0 if passed == len(results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
