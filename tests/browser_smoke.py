"""Run against localhost:8000 with Playwright installed; chat API is mocked, not billed."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from app.catalog import Catalog

products=Catalog(Path('data')).search(category_id=5,max_price='600',limit=2)['items']
requests=[]
responses=[
    (200,{'message':'Separei duas opções reais para comparar.','products':products,'sources':[],
          'conversation_id':'browser-session','actions':[{'id':'compare','label':'Comparar opções','message':'Compare estas opções.'}]}),
    (200,{'message':'Veja as características consultadas.','products':products,'sources':[],
          'conversation_id':'browser-session','actions':[{'id':'draft','label':'Preparar resposta ao cliente','message':'Prepare uma resposta ao cliente.'}]}),
    (200,{'message':'Revise a sugestão antes de encaminhar.','products':[],
          'sources':[{'pages':[4],'title':'Devolução online','text':'Trecho de evidência para conferência.'}],
          'draft':'Olá! Confira estas opções com a loja.','conversation_id':'browser-session','actions':[]}),
    (503,{'detail':'Atendimento indisponível no momento. Tente mais tarde.'}),
    (200,{'message':'Consulta recuperada.','products':[],'sources':[],'conversation_id':'recovered','actions':[]}),
]
with sync_playwright() as p:
    browser=p.chromium.launch()
    context=browser.new_context(viewport={'width':1440,'height':1000},permissions=['clipboard-read','clipboard-write'])
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    def route_chat(route):
        requests.append(route.request.post_data_json)
        status,body=responses.pop(0)
        route.fulfill(status=status,content_type='application/json',body=json.dumps(body))
    page.route('**/api/chat',route_chat)
    page.route('**/api/conversation/reset',lambda route:route.fulfill(status=204))
    page.goto('http://127.0.0.1:8000')
    assert page.locator('[data-intent]').count()==4
    page.screenshot(path='/tmp/emporio-entry-desktop.png')
    page.locator('[data-intent=products]').focus()
    page.keyboard.press('Enter')
    page.get_by_role('button',name='Comparar opções').click()
    assert requests[1]['conversation_id']=='browser-session'
    assert requests[1]['action_id']=='compare'
    page.get_by_role('button',name='Preparar resposta ao cliente').click()
    page.locator('.draft-text').wait_for()
    page.get_by_role('button',name='Copiar mensagem').click()
    page.get_by_text('Mensagem copiada. Revise antes de encaminhar.').wait_for()
    assert page.evaluate('navigator.clipboard.readText()')=='Olá! Confira estas opções com a loja.'
    page.evaluate("navigator.clipboard.writeText=()=>Promise.reject(new Error('Denied'))")
    page.get_by_role('button',name='Copiar mensagem').click()
    page.get_by_text('Texto selecionado. Use a opção de copiar do seu dispositivo.').wait_for()
    assert page.locator('.draft-text').evaluate('(node)=>node.selectionEnd-node.selectionStart===node.value.length')
    page.locator('.source summary').click()
    assert page.get_by_text('Trecho de evidência para conferência.',exact=True).is_visible()
    page.screenshot(path='/tmp/emporio-support-desktop.png')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='/tmp/emporio-support-mobile.png')
    page.get_by_role('button',name='Outro assunto').click()
    assert page.locator('#welcome').is_visible()
    assert page.locator('.draft-text').count()==0
    page.screenshot(path='/tmp/emporio-entry-mobile.png')
    page.locator('[data-intent=store]').click()
    page.get_by_role('button',name='Tentar novamente').click()
    page.get_by_text('Consulta recuperada.',exact=True).wait_for()
    assert page.locator('[data-intent]').count()==4
    page.emulate_media(reduced_motion='reduce')
    assert page.locator('.message').first.evaluate('(node)=>getComputedStyle(node).animationName')=='none'
    order_requests=[]
    def verify(route):
        order_requests.append(route.request.post_data_json)
        route.fulfill(content_type='application/json',body=json.dumps({'status':'found','order':{'status':'shipped','estimated_delivery':'2026-11-10','tracking_code':'BRTEST'}}))
    page.route('**/api/orders/verify',verify)
    page.get_by_role('button',name='Consultar pedido',exact=True).click()
    page.get_by_role('textbox',name='Número do pedido').fill('42')
    page.get_by_role('textbox',name='E-mail da compra').fill('cliente@example.test')
    page.get_by_role('button',name='Verificar pedido').click()
    page.get_by_text('Status: Enviado',exact=False).wait_for()
    assert order_requests[0]['order_id']==42
    assert page.get_by_role('textbox',name='E-mail da compra').input_value()==''
    assert all('cliente@example.test' not in json.dumps(request) for request in requests)
    assert not errors,errors
    browser.close()
    print('Browser OK: entry, keyboard, context actions, copy, sources, mobile, reset, retry, reduced motion.')
