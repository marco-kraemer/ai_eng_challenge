"""Real browser, API and catalog; category selection must never call the LLM."""
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[1]
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
base = f'http://127.0.0.1:{port}'
server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.web:app', '--host', '127.0.0.1', '--port', str(port)],
    cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for attempt in range(100):
        try:
            if httpx.get(base + '/api/health', timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(.1)
    else:
        raise RuntimeError('Test server did not start')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
        errors = []; model_requests = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('**/api/chat*', lambda route: (model_requests.append(route.request.url), route.abort()))
        page.goto(base)
        page.locator('[data-intent=products]').click()
        page.get_by_role('button', name='Violões', exact=True).click()
        page.get_by_role('button', name='Ukuleles', exact=True).click()
        assert page.locator('.instrument-option[aria-pressed=true]').count() == 2
        page.screenshot(path='/tmp/emporio-category-picker-mobile.png')
        page.get_by_role('button', name='Continuar', exact=True).click()
        page.get_by_label('Valor máximo (R$)').fill('1000')
        with page.expect_response(lambda r: '/api/catalog/search' in r.url) as response:
            page.get_by_role('button', name='Ver instrumentos', exact=True).click()
        data = response.value.json()
        assert data['search']['category_ids'] == [5, 9]
        assert {p['category_id'] for p in data['products']} == {5, 9}
        page.locator('.search-summary').last.get_by_role('button', name='Alterar orçamento').click()
        page.get_by_label('Valor máximo (R$)').fill('10')
        page.get_by_role('button', name='Ver instrumentos', exact=True).click()
        page.get_by_role('button', name='Ver opções até', exact=False).last.wait_for()
        with page.expect_response(lambda r: '/api/catalog/search' in r.url) as accepted:
            page.get_by_role('button', name='Ver opções até', exact=False).last.click()
        assert accepted.value.request.post_data_json['category_ids'] == [5, 9]
        page.locator('.message').last.get_by_role('button', name='Alterar busca', exact=True).click()
        page.get_by_role('button', name='Todos os instrumentos', exact=True).click()
        assert page.locator('.instrument-option[aria-pressed=true]').count() == 0
        page.get_by_role('button', name='Continuar', exact=True).click()
        page.get_by_label('Valor máximo (R$)').fill('1000')
        with page.expect_response(lambda r: '/api/catalog/search' in r.url) as response:
            page.get_by_role('button', name='Ver instrumentos', exact=True).click()
        data = response.value.json()
        assert data['search']['category_ids'] == []
        assert {p['category_id'] for p in data['products']} == {5, 9}
        assert page.locator('.search-summary').last.inner_text().startswith('Todos os instrumentos')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path='/tmp/emporio-multiple-categories-mobile.png')
        assert not errors and not model_requests, (errors, model_requests)
        page.get_by_role('button', name='Nova conversa', exact=True).click()
        page.locator('[data-intent=products]').click()
        page.get_by_role('button', name='Continuar', exact=True).wait_for()
        assert page.get_by_role('button', name='Continuar', exact=True).is_disabled()
        page.get_by_role('button', name='Teclados e Pianos', exact=True).click()
        page.get_by_role('button', name='Continuar', exact=True).click()
        page.get_by_label('Valor máximo (R$)').fill('1200')
        page.get_by_role('button', name='Ver instrumentos', exact=True).click()
        page.get_by_text('A descrição informa 88 teclas', exact=False).wait_for(timeout=3000)
        browser.close()
    print('Browser OK: multiple categories, recovery, budget editing, all categories, reset and mobile; no LLM calls.')
finally:
    server.terminate()
    server.wait(timeout=10)
