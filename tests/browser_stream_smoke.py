"""Browser → real SSE route; only model inference is scripted and externally gated."""
import socket
import threading
import time
from unittest.mock import patch
import uvicorn
from playwright.sync_api import sync_playwright
from app.web import app
from app.telemetry import emit
from app.conversations import ConversationStore
from app.limits import RateLimiter


class Model:
    release = threading.Event()
    mode = 'good'
    def generate(self, contents, tools, **options):
        if options.get('response_format'):
            return {'parts': [{'text': 'store'}]}
        emit('delta', text='Olá, estou ')
        if self.mode == 'error':
            raise RuntimeError('private-internal-error')
        self.release.wait(10)
        emit('delta', text='aqui para ajudar.')
        return {'parts': [{'text': 'Olá, estou aqui para ajudar.'}]}


sock = socket.socket(); sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
server = uvicorn.Server(uvicorn.Config(app, log_level='error', proxy_headers=False))
worker = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
store = ConversationStore()
with patch('app.web.build_provider', Model), patch('app.telemetry.export_runs'), patch('app.web.conversations', store), patch('app.web.rate_limiter', RateLimiter()):
    worker.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if time.monotonic() > deadline: raise RuntimeError('Server startup failed')
            time.sleep(.02)
        with sync_playwright() as p:
            browser = p.chromium.launch(); page = browser.new_page(reduced_motion='reduce')
            errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{port}')
            page.get_by_label('Sua mensagem').fill('Olá'); page.locator('.send').click()
            page.get_by_text('Olá, estou ', exact=True).wait_for()
            assert page.locator('#message-form .send').is_disabled()
            assert page.get_by_text('Olá, estou aqui para ajudar.', exact=True).count() == 0
            Model.release.set()
            page.get_by_text('Olá, estou aqui para ajudar.', exact=True).wait_for()
            assert page.get_by_text('Olá, estou aqui para ajudar.', exact=True).count() == 1
            page.get_by_role('button', name='Nova conversa', exact=True).click()
            Model.release.clear()
            page.get_by_label('Sua mensagem').fill('Outra mensagem'); page.locator('.send').click()
            page.get_by_text('Olá, estou ', exact=True).wait_for()
            token = page.evaluate('conversationId')
            page.get_by_role('button', name='Nova conversa', exact=True).click()
            Model.release.set()
            page.get_by_role('heading', name='Como posso ajudar?').wait_for()
            assert page.locator('#messages .message').count() == 0
            Model.mode = 'error'
            page.get_by_label('Sua mensagem').fill('Teste de erro'); page.locator('.send').click()
            page.get_by_role('button', name='Tentar novamente', exact=True).wait_for()
            assert page.get_by_text('Olá, estou ', exact=True).count() == 0
            assert page.get_by_text('private-internal-error').count() == 0
            assert store.history(token) == []
            assert not errors, errors
            browser.close()
        print('Browser SSE OK: partial text before completion, single final answer, reset fencing and sanitized error recovery.')
    finally:
        Model.release.set(); server.should_exit = True; worker.join(timeout=10); sock.close()
