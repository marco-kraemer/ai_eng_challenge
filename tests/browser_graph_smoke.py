"""Chromium → real HTTP API → LangGraph/tools/data. Only model inference is scripted.

Runs an isolated ephemeral local server; never reads or sends an OpenRouter key.
"""
import json
import socket
import threading
import time
from unittest.mock import patch

import uvicorn
from playwright.sync_api import sync_playwright
from app.web import app


class ScriptedModel:
    def generate(self, contents, tools, **options):
        if options.get('response_format'):
            question = json.loads(contents[-1]['parts'][0]['text'])['current_message'].lower()
            label = ('compare' if 'diferença' in question else 'policies' if 'horas' in question
                     else 'order' if 'pedido' in question else 'offtopic')
            return {'parts': [{'text': label}]}
        result = contents[-1]['parts'][0]['functionResponse']['response']
        assert result['status'] == 'found' and result['items']
        is_policy = contents[-1]['parts'][0]['functionResponse']['name'] == 'search_policies'
        text = 'Horários consultados no manual.' if is_policy else 'Compare as especificações das opções selecionadas.'
        return {'parts': [{'text': text}]}


def run():
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='error', proxy_headers=False))
    worker = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    with patch('app.web.build_provider', ScriptedModel):
        worker.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if time.monotonic() > deadline:
                    raise RuntimeError('Test server did not start')
                time.sleep(.02)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{port}')
                page.locator('[data-intent=products]').click()
                category_button = page.get_by_role('button', name='Violões', exact=True)
                if category_button.get_attribute('aria-pressed') != 'true': category_button.click()
                page.get_by_role('button', name='Continuar', exact=True).click()
                page.get_by_label('Valor máximo (R$)').fill('1000')
                page.get_by_role('button', name='Ver instrumentos', exact=True).click()
                page.locator('.product').first.wait_for()
                with page.expect_response(lambda response: '/api/chat' in response.url) as comparison:
                    page.get_by_role('button', name='Comparar opções', exact=True).click()
                page.get_by_text('Compare as especificações das opções selecionadas.', exact=True).wait_for()
                assert page.locator('.message').last.locator('.product').count() >= 2
                page.locator('#message-input').fill('Que horas vocês abrem em datas especiais?')
                with page.expect_response(lambda response: '/api/chat' in response.url, timeout=120000) as policies:
                    page.locator('#message-form .send').click()
                page.get_by_text('Horários consultados no manual.', exact=True).wait_for()
                page.locator('.sources').last.locator('summary').click()
                assert page.locator('.source-item').last.is_visible()
                page.locator('#message-input').fill('Me ensine Python')
                page.locator('#message-form .send').click()
                page.get_by_text('Esse assunto fica fora do meu atendimento.', exact=False).wait_for()
                page.locator('#message-input').fill('Quero acompanhar meu pedido')
                page.locator('#message-form .send').click()
                page.get_by_role('textbox', name='E-mail da compra').wait_for()
                assert not errors, errors
                browser.close()
        finally:
            server.should_exit = True
            worker.join(timeout=10)
            sock.close()
    print('Browser graph smoke passed: catalog → comparison → real policy retrieval → refusal → order form.')


if __name__ == '__main__':
    run()
