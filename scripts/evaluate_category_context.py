"""Opt-in live HTTP conversation: switch, combine and clear instrument categories."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def evaluate(variant='reported'):
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    from fastapi.testclient import TestClient
    from app.conversations import ConversationStore
    from app.limits import RateLimiter
    from app.web import app
    from scripts.evaluate_budget_language import ObservedProvider

    provider = ObservedProvider()
    store = ConversationStore()
    cases = [
        ('switch-from-drums', 'quero violão, não tenho muito dinheiro', [5], '1000.00', True),
        ('broaden-to-all', 'Me dê instrumentos até R$ 1.000.', [], '1000.00', True),
        ('multiple-categories', 'Quero ver violões e ukuleles até seiscentos reais.', [5, 9], '600.00', True),
        ('switch-with-pending-offer', 'Agora só teclados com esse mesmo limite.', [4], '600.00', False),
        ('confirm-new-offer', 'Pode mostrar por esse valor sugerido.', [4], '1127.00', True),
        ('clear-all-filters', 'Agora me mostra todos os tipos de instrumento, sem limite de preço.', [], None, True),
    ]
    if variant == 'paraphrases':
        questions = [
            'Troca isso por um violão, preciso de algo em conta.',
            'Quero opções do catálogo até mil reais, de qualquer tipo.',
            'Pode restringir a ukulele ou violão? Meu teto agora é seiscentos.',
            'E se eu escolher um teclado? O orçamento continua igual.',
            'Tá bom, pode abrir as opções que cabem no valor que você acabou de sugerir.',
            'Não quero ficar preso a nenhum instrumento nem preço; mostre possibilidades variadas.',
        ]
        cases = [(name, question, ids, budget, found) for (name, _, ids, budget, found), question in zip(cases, questions)]
    rows = []
    with patch('app.web.conversations', store), patch('app.web.rate_limiter', RateLimiter()), patch('app.web.build_provider', return_value=provider), TestClient(app) as client:
        initial = client.post('/api/catalog/search', json={'category_id': 3, 'max_price': '1000'})
        initial.raise_for_status()
        token = initial.json()['conversation_id']
        for name, question, expected_ids, expected_budget, has_products in cases:
            provider.tool_calls.clear(); provider.classifications.clear()
            start = time.monotonic()
            response = client.post('/api/chat', json={'conversation_id': token, 'message': question})
            data = response.json(); search = data.get('search', {})
            state = store.state(token); products = data.get('products', [])
            ids = search.get('category_ids')
            # No new numeric ceiling was stated in the first turn: keeping the
            # prior ceiling or showing affordable options without a cap is valid.
            budget_matches = (search.get('max_price') in (None, '1000.00') if name == 'switch-from-drums'
                              else search.get('max_price') == expected_budget)
            passed = (response.status_code == 200 and ids is not None and sorted(ids) == expected_ids
                      and budget_matches and bool(products) == has_products
                      and (all(p['category_id'] in expected_ids for p in products) if expected_ids else True)
                      and (not expected_ids or has_products or state.get('pending_budget', {}).get('category_id') == expected_ids[0]))
            if name == 'broaden-to-all':
                passed = passed and len({p['category_id'] for p in products}) > 1 and 'category_id' not in state['preferences']
            if name == 'switch-from-drums':
                passed = passed and all(Decimal(p['price_brl']) <= 1000 for p in products)
            row = {'case': name, 'question': question, 'passed': passed, 'status': response.status_code,
                   'seconds': round(time.monotonic() - start, 2), 'search': search,
                   'product_categories': [p['category_id'] for p in products],
                   'preferences': state.get('preferences'), 'pending_budget': state.get('pending_budget'),
                   'classification': list(provider.classifications), 'tools': list(provider.tool_calls),
                   'message': data.get('message', data.get('detail'))}
            rows.append(row); print(json.dumps(row, ensure_ascii=False), flush=True)
        client.post('/api/conversation/reset', json={'conversation_id': token})
    return {'provider': 'configured live provider', 'model': provider.provider.last_model, 'variant': variant,
            'mode': 'real multi-turn HTTP, CSV catalog and in-memory isolated session; not a statistical quality benchmark',
            'total': len(rows), 'passed': sum(row['passed'] for row in rows), 'cases': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--variant', choices=('reported', 'paraphrases'), default='reported')
    args = parser.parse_args()
    if not args.live:
        parser.error('Use --live to enable real provider requests and token consumption.')
    result = evaluate(args.variant)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f"Category conversation: {result['passed']}/{result['total']} passed.")
    raise SystemExit(0 if result['passed'] == result['total'] else 1)
