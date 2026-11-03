"""Customer flows in Chromium. Categories/catalog are real; LLM and order credentials are mocked."""
import json
from playwright.sync_api import sync_playwright

chat_requests=[]
chat_replies=[
    (200,{'message':'Posso comparar as características dessas opções.','products':[],'sources':[{'pages':[2],'title':'Horário de funcionamento','text':'Segunda a sexta, das 9h às 18h.'}],'actions':[]}),
    (503,{'detail':'Atendimento indisponível no momento. Tente mais tarde.'}),
    (200,{'message':'Vamos verificar como resolver o defeito do seu instrumento.','products':[],'sources':[],'actions':[]}),
]
with sync_playwright() as p:
    browser=p.chromium.launch()
    context=browser.new_context(viewport={'width':1440,'height':1000})
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    def route_chat(route):
        chat_requests.append(route.request.post_data_json)
        code,data=chat_replies.pop(0)
        if code==200:data['conversation_id']=route.request.post_data_json.get('conversation_id')
        route.fulfill(status=code,content_type='application/json',body=json.dumps(data))
    page.route('**/api/chat',route_chat)
    page.goto('http://127.0.0.1:8000')
    assert page.get_by_role('heading',name='Como posso ajudar?').is_visible()
    assert page.locator('[data-intent]').count()==4
    page.screenshot(path='/tmp/emporio-customer-home-desktop.png')
    page.locator('[data-intent=products]').focus()
    page.keyboard.press('Enter')
    page.get_by_role('heading',name='Qual instrumento você procura?').wait_for()
    page.locator('.instrument-option').nth(5).wait_for()
    page.wait_for_function("[...document.querySelectorAll('.instrument-image use')].every(node=>node.getBBox().width>0)")
    assert not chat_requests,'A picker must not ask about arbitrary guitars/budget or consume LLM quota'
    assert page.locator('#messages .message').count()==0
    page.screenshot(path='/tmp/emporio-customer-instruments-desktop.png')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='/tmp/emporio-customer-instruments-mobile.png')
    category_button = page.get_by_role('button',name='Violões',exact=True)
    if category_button.get_attribute('aria-pressed') != 'true': category_button.click()
    page.get_by_role('button', name='Continuar', exact=True).click()
    page.get_by_role('heading',name='Quanto você quer gastar?').wait_for()
    assert page.get_by_label('Valor máximo (R$)').input_value()==''
    page.get_by_role('button',name='← Voltar',exact=True).click()
    category_button = page.get_by_role('button',name='Violões',exact=True)
    if category_button.get_attribute('aria-pressed') != 'true': category_button.click()
    page.get_by_role('button', name='Continuar', exact=True).click()
    assert page.get_by_label('Valor máximo (R$)').input_value()==''
    page.get_by_role('button',name='Ver instrumentos',exact=True).click()
    assert page.get_by_text('Informe um valor válido',exact=False).is_visible()
    assert not chat_requests
    page.get_by_label('Valor máximo (R$)').fill('600,00')
    page.screenshot(path='/tmp/emporio-customer-budget-mobile.png')
    with page.expect_response(lambda response:'/api/catalog/search' in response.url) as selected:
        page.get_by_role('button',name='Ver instrumentos',exact=True).click()
    payload=selected.value.request.post_data_json
    assert payload['category_id']==5 and payload['max_price']=='600.00'
    data=selected.value.json()
    assert data['products'] and all(float(product['price_brl'])<=600 for product in data['products'])
    page.locator('.product').first.wait_for()
    assert not chat_requests,'Structured catalog search must work independently of model quota'
    page.screenshot(path='/tmp/emporio-customer-results-mobile.png')
    page.set_viewport_size({'width':1440,'height':1000})
    page.get_by_role('button',name='Comparar opções',exact=True).click()
    page.get_by_text('Posso comparar as características dessas opções.',exact=True).wait_for()
    assert chat_requests[0]['conversation_id']==data['conversation_id']
    assert chat_requests[0]['message']=='Qual é a diferença entre essas opções?'
    page.get_by_text('Consultar informações da loja',exact=True).click()
    assert page.get_by_text('Segunda a sexta, das 9h às 18h.',exact=True).is_visible()
    assert page.locator('.draft-box').count()==0
    page.get_by_role('button',name='Nova conversa',exact=True).click()
    page.locator('[data-intent=products]').click()
    category_button = page.get_by_role('button',name='Guitarras',exact=True)
    if category_button.get_attribute('aria-pressed') != 'true': category_button.click()
    page.get_by_role('button', name='Continuar', exact=True).click()
    with page.expect_response(lambda response:'/api/catalog/search' in response.url) as no_budget:
        page.get_by_role('button',name='Ainda não defini um valor',exact=True).click()
    assert 'max_price' not in no_budget.value.request.post_data_json
    assert all(product['category_id']==1 for product in no_budget.value.json()['products'])
    page.get_by_role('button',name='Nova conversa',exact=True).click()
    count=len(chat_requests)
    page.locator('[data-intent=purchase]').click()
    assert len(chat_requests)==count
    page.get_by_role('button',name='Produto com defeito',exact=False).click()
    page.get_by_role('button',name='Tentar novamente',exact=True).click()
    page.get_by_text('Vamos verificar como resolver o defeito do seu instrumento.',exact=True).wait_for()
    assert chat_requests[-1]['message']=='Meu instrumento apresentou um defeito. Como posso resolver?'
    order_requests=[]
    def order_lookup(route):
        order_requests.append(route.request.post_data_json)
        route.fulfill(content_type='application/json',body=json.dumps({'status':'found','order':{'status':'shipped','estimated_delivery':'2026-11-10','tracking_code':'BRTEST'}}))
    page.route('**/api/orders/verify',order_lookup)
    page.get_by_role('button',name='Nova conversa',exact=True).click()
    page.locator('[data-intent=order]').click()
    page.get_by_role('textbox',name='Número do pedido').fill('42')
    page.get_by_role('textbox',name='E-mail da compra').fill('cliente@example.test')
    page.get_by_role('button',name='Consultar pedido',exact=True).click()
    page.get_by_text('Status: Enviado',exact=False).wait_for()
    assert order_requests[0]['order_id']==42
    assert page.get_by_role('textbox',name='E-mail da compra').input_value()==''
    assert all('cliente@example.test' not in json.dumps(request) for request in chat_requests)
    page.emulate_media(reduced_motion='reduce')
    assert page.locator('.message').first.evaluate('(node)=>getComputedStyle(node).animationName')=='none'
    page.get_by_role('button',name='Nova conversa',exact=True).click()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='/tmp/emporio-customer-home-mobile.png')
    assert not errors,errors
    browser.close()
    print('Browser OK: customer copy, available-category illustrations, keyboard, explicit category/budget, optional price, real catalog without LLM, contextual comparison, sources, retry, order privacy, mobile and reset.')
