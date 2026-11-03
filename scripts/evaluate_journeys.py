"""Reproducible customer-flow checks; scripted inference, real graph/tools/data."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.web import app
from app.limits import RateLimiter
from app.conversations import ConversationStore


class ScenarioModel:
    def generate(self, contents, tools, **options):
        if options.get('system'):
            question=json.loads(contents[-1]['parts'][0]['text'])['current_message'].lower()
            label=('offtopic' if 'python' in question else 'policies' if 'horas' in question
                   else 'identity' if 'nome' in question else 'order' if 'pedido' in question
                   else 'compare' if 'diferença' in question else 'store')
            return {'parts':[{'text':label}]}
        return {'parts':[{'text':'Confira as informações consultadas no catálogo e nas fontes da loja.'}]}


def evaluate(scenarios):
    cases=[]
    with patch('app.web.build_provider',ScenarioModel), patch('app.web.rate_limiter',RateLimiter()), patch('app.web.conversations',ConversationStore()), TestClient(app) as client:
        for scenario in scenarios:
            errors=[]
            token=None
            for index,step in enumerate(scenario['steps'],1):
                body=dict(step['body'])
                if token:body['conversation_id']=token
                response=client.post(step['path'],json=body)
                data=response.json()
                token=data.get('conversation_id',token)
                for key,value in step['expect'].items():
                    actual=(response.status_code if key=='status' else data.get('recovery',{}).get('reason') if key=='reason'
                            else bool(data.get(key)) if key in ('products','sources') else value in data.get('message','') if key=='contains'
                            else data.get(key))
                    expected=True if key=='contains' else value
                    if actual!=expected:errors.append(f'step {index}: {key}: expected {expected!r}, received {actual!r}')
            cases.append({'id':scenario['id'],'passed':not errors,'errors':errors})
    return {'model_mode':'scripted; not a live model quality evaluation', 'data_mode':'real CSVs and local hybrid PDF retrieval',
            'total':len(cases),'passed':sum(case['passed'] for case in cases),'cases':cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios',type=Path,default=Path('tests/fixtures/customer_journeys.json'))
    parser.add_argument('--output',type=Path,default=Path('docs/avaliacao-jornadas.json'))
    args=parser.parse_args()
    report=evaluate(json.loads(args.scenarios.read_text()))
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f"Jornadas: {report['passed']}/{report['total']} passaram (inferência simulada).")
    return 0 if report['passed']==report['total'] else 1


if __name__=='__main__':
    raise SystemExit(main())
