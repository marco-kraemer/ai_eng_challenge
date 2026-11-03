"""Delayed responses verify typing, duplicate prevention, retry, reset and motion."""
import json
from playwright.sync_api import sync_playwright, Error

with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':390,'height':844})
    routes=[];errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.route('**/api/chat*',lambda route:routes.append(route))
    page.goto('http://127.0.0.1:8000')
    def submit(text):
        page.locator('#message-input').fill(text)
        with page.expect_request('**/api/chat*'):
            page.locator('#message-form .send').click()
        page.locator('.typing-indicator').wait_for()
    def reply(route,message,status=200):
        payload={'message':message,'products':[],'sources':[],'actions':[],'conversation_id':'typing-test'} if status==200 else {'detail':message}
        route.fulfill(status=status,content_type='application/json',body=json.dumps(payload))
    submit('Quero encontrar um instrumento')
    assert page.locator('.typing-dot').count()==3
    assert page.locator('#message-form .send').is_disabled()
    assert 'Mensagem enviada' in page.locator('#status').inner_text()
    count=len(routes)
    page.locator('#message-input').fill('mensagem repetida')
    page.locator('#message-input').press('Enter')
    page.evaluate("document.querySelector('#message-form').dispatchEvent(new Event('submit',{cancelable:true}))")
    assert len(routes)==count
    assert page.locator('.typing-indicator').count()==1
    page.emulate_media(reduced_motion='reduce')
    assert page.locator('.typing-dot').first.evaluate('(node)=>getComputedStyle(node).animationName')=='none'
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='/tmp/emporio-typing-mobile.png')
    reply(routes[-1],'Aqui estão as opções.')
    page.get_by_text('Aqui estão as opções.',exact=True).wait_for()
    assert page.locator('.typing-indicator').count()==0
    assert page.locator('#message-form .send').is_enabled()
    submit('Outra busca')
    reply(routes[-1],'Tente novamente mais tarde.',503)
    page.get_by_role('button',name='Tentar novamente',exact=True).wait_for()
    assert page.locator('.typing-indicator').count()==0
    with page.expect_request('**/api/chat*'):
        page.get_by_role('button',name='Tentar novamente',exact=True).click()
    page.locator('.typing-indicator').wait_for()
    reply(routes[-1],'Consulta concluída.')
    page.get_by_text('Consulta concluída.',exact=True).wait_for()
    submit('Pergunta antiga')
    old=routes[-1]
    page.get_by_role('button',name='Nova conversa',exact=True).click()
    assert page.locator('.typing-indicator').count()==0
    submit('Pergunta nova')
    new=routes[-1]
    try:reply(old,'Resposta antiga descartada.')
    except Error:pass  # Reset aborts the previous fetch; it may already be cancelled.
    assert page.locator('.typing-indicator').count()==1
    assert page.locator('#message-form .send').is_disabled()
    reply(new,'Resposta nova.')
    page.get_by_text('Resposta nova.',exact=True).wait_for()
    assert page.get_by_text('Resposta antiga descartada.',exact=True).count()==0
    assert page.locator('.typing-indicator').count()==0
    submit('Falha de conexão')
    routes[-1].abort('failed')
    page.get_by_role('button',name='Tentar novamente',exact=True).last.wait_for()
    assert page.locator('.typing-indicator').count()==0
    assert page.locator('#message-form .send').is_enabled()
    assert not errors,errors
    browser.close()
print('Typing browser OK: visible pending bubble, no duplicate requests, success/error/retry/reset, stale response isolation, reduced motion and mobile.')
