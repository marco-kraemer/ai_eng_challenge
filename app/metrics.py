"""Provider-reported token accounting; prices are estimates, never billing totals."""
from math import ceil
from statistics import median

PRICING_DATE = '2026-11-03'
PRICING_SOURCE = 'https://developers.openai.com/api/docs/models/gpt-4.1-mini'


def usage_metrics(usage, model):
    result: dict = {'cost_usd': None, 'usage_missing': 1}
    if not isinstance(usage, dict):
        return result
    prompt = usage.get('prompt_tokens'); output = usage.get('completion_tokens')
    details = usage.get('prompt_tokens_details') or {}
    cached = details.get('cached_tokens', 0) if isinstance(details, dict) else 0
    if type(prompt) is not int or type(output) is not int or type(cached) is not int:
        return result
    if min(prompt, output, cached) < 0 or cached > prompt:
        return result
    result = {'input_tokens': prompt, 'output_tokens': output, 'cached_tokens': cached,
              'total_tokens': prompt + output, 'usage_missing': 0, 'cost_usd': None}
    if model in ('gpt-4.1-mini', 'gpt-4.1-mini-2025-04-14'):
        result['cost_usd'] = round(((prompt-cached)*.40 + cached*.10 + output*1.60)/1_000_000, 10)
    return result


def record_usage(usage, model, record=None):
    from app.telemetry import current_turn, safe_metadata
    values = usage_metrics(usage, model)
    trace = current_turn()
    if record is not None:
        record['extra']['metadata'].update(safe_metadata({**values, 'model': model, 'ls_model_name': model, 'ls_provider': 'openai' if str(model).startswith('gpt-4.1-mini') else 'unknown'}))
        if not values['usage_missing']:
            record['usage_metadata'] = {'input_tokens': values['input_tokens'], 'output_tokens': values['output_tokens'],
                'total_tokens': values['total_tokens'], 'input_token_details': {'cache_read': values['cached_tokens']}}
    if trace is not None:
        m = trace.metrics
        m['llm_calls'] += 1
        for key in ('input_tokens', 'output_tokens', 'cached_tokens', 'total_tokens', 'usage_missing'):
            m[key] = m.get(key, 0) + values.get(key, 0)
        cost = values['cost_usd']
        if cost is None or m.get('cost_usd') is None:
            m['cost_usd'] = None
        else:
            m['cost_usd'] = round(m['cost_usd'] + cost, 10)
        m['known_cost_usd'] = round(m.get('known_cost_usd', 0) + (cost or 0), 10)
    return values


def aggregate(rows):
    times = sorted(row['seconds'] for row in rows)
    costs = [r.get('metrics', {}).get('cost_usd') for r in rows]
    known = [c for c in costs if c is not None]
    return {'turns': len(rows), 'passed': sum(bool(r['passed']) for r in rows),
            'infrastructure_errors': sum(r['status'] >= 400 for r in rows),
            'semantic_failures': sum(not r['passed'] and r['status'] < 400 for r in rows),
            'latency_median_seconds': median(times) if times else None,
            'latency_p95_seconds': times[ceil(.95*len(times))-1] if times else None,
            'latency_quantile_method': 'nearest rank; measured HTTP wall time',
            'unknown_cost_turns': sum(c is None for c in costs),
            'known_cost_usd': round(sum(known), 8),
            'average_known_turn_cost_usd': round(sum(known)/len(known), 8) if known else None,
            'llm_calls': sum(r.get('metrics', {}).get('llm_calls', 0) for r in rows)}
