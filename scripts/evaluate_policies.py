"""Compare local retrieval on explicit Portuguese paraphrases. No LLM/API calls."""
import argparse
import json
import resource
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.policy_service import get_policy_index, ROOT

CASES = [
    ('que horas vocês abrem?', {'2'}),
    ('abrem quando?', {'2'}),
    ('sábado posso ir depois do almoço?', {'2'}),
    ('o WhatsApp atende domingo?', {'2'}),
    ('horário de funcionamento da loja', {'2'}),
    ('comprei pela internet e me arrependi', {'4.1'}),
    ('quero devolver minha compra online', {'4.1'}),
    ('o instrumento veio com defeito de fabricação', {'4.2'}),
    ('posso trocar por outra cor?', {'4.3'}),
    ('instrumentos personalizados podem ser trocados?', {'4.4'}),
    ('posso parcelar em três vezes?', {'3', '3.1'}),
    ('qual o desconto no PIX?', {'3'}),
    ('posso acumular PIX com preço promocional?', {'6.2'}),
    ('qual o telefone de contato WhatsApp?', {'1.2', '7'}),
    ('qual o endereço da loja?', {'1.2'}),
    ('qual o prazo do SEDEX para outras cidades?', {'5.2'}),
    ('meu instrumento tem garantia do fabricante?', {'8.2'}),
    ('vendem cabos e palhetas?', {'1', '7.1'}),
    ('desisti depois de receber a encomenda da internet', {'4.1'}),
    ('paguei e quero meu dinheiro de volta', {'4.1'}),
    ('meu teclado pifou logo que chegou', {'4.2'}),
    ('posso dividir a compra em prestações?', {'3', '3.1'}),
]
NEGATIVE = ['tem estacionamento subterrâneo gratuito?', 'aceitam bitcoin e ethereum?', 'qual a senha do wifi?', 'oferecem aulas de canto gratuitas?']


def evaluate():
    start = time.perf_counter()
    index = get_policy_index(ROOT / 'data')
    setup_seconds = time.perf_counter() - start
    rows = []
    stats = {}
    for mode in ('lexical', 'semantic', 'hybrid'):
        success = 0
        query_seconds = []
        for question, expected in CASES:
            start = time.perf_counter()
            result = index.search(question, mode=mode)
            query_seconds.append(time.perf_counter() - start)
            sections = {item['section'] for item in result['items']}
            hit = expected.issubset(sections)
            success += hit
            rows.append({'mode': mode, 'question': question, 'expected': sorted(expected), 'retrieved': [item['section'] for item in result['items']], 'all_expected_in_top3': hit})
        negatives = []
        for question in NEGATIVE:
            result = index.search(question, mode=mode)
            negatives.append({'question': question, 'status': result['status'], 'retrieved': [item['section'] for item in result['items']]})
        stats[mode] = {'all_expected_in_top3': f'{success}/{len(CASES)}', 'mean_query_ms': round(1000 * sum(query_seconds) / len(query_seconds), 2), 'negative_cases': negatives}
    return {'model': index.encoder.model_id, 'chunks': len(index.chunks), 'index_setup_seconds': round(setup_seconds, 2), 'peak_process_rss_mb': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), 'statistics': stats, 'cases': rows,
            'limitations': 'Small hand-authored development set; parameters were calibrated on these cases. Not a held-out benchmark or proof that retrieved text answers the question.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = evaluate()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, ensure_ascii=False, indent=2))
