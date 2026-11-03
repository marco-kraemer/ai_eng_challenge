"""Real UI/API/PDF FAQ journey with all inference disabled."""
import socket
import threading
import time
from unittest.mock import patch
import uvicorn
from playwright.sync_api import sync_playwright
from app.web import app

class NoInference:
    calls=0
    def generate(self,*args,**kwargs):
        NoInference.calls+=1
        raise RuntimeError('Model deliberately unavailable during FAQ verification')


def run():
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error',proxy_headers=False))
    worker=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True)
    with patch('app.web.OpenRouter',NoInference):
        worker.start()
        try:
            deadline=time.monotonic()+10
            while not server.started:
                if time.monotonic()>deadline:raise RuntimeError('Test server did not start')
                time.sleep(.02)
            with sync_playwright() as p:
                browser=p.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{port}')
                for question,expected in [('Onde vocês ficam?','Rua 14 de Maio, 3200'),('Que horas vocês abrem?','09:00 às 18:00'),('Qual o WhatsApp da loja?','(67) 3321-4500'),('Qual o e-mail da loja?','grafias diferentes')]:
                    page.locator('#message-input').fill(question)
                    with page.expect_response(lambda response:'/api/chat' in response.url) as answer:
                        page.locator('#message-form .send').click()
                    assert answer.value.status==200
                    assert expected in answer.value.json()['message']
                    assert answer.value.json()['sources']
                    page.locator('.message').last.locator('.sources summary').click()
                    assert page.locator('.message').last.locator('.source-item').first.is_visible()
                assert NoInference.calls==0
                assert not errors and page.evaluate('document.documentElement.scrollWidth<=innerWidth'),errors
                page.get_by_role('button',name='Nova conversa',exact=True).click()
                assert page.locator('.message').count()==0
                browser.close()
        finally:
            server.should_exit=True;worker.join(timeout=10);sock.close()
    print('FAQ browser OK: address, hours, WhatsApp, email conflicts, sources, reset; zero model calls.')

if __name__=='__main__':run()
