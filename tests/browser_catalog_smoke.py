"""Real browser/API/catalog checks; no model requests allowed."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1440,'height':1000}, reduced_motion='reduce')
    errors=[];model_requests=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.route('**/api/chat',lambda route:(model_requests.append(route.request.url),route.abort()))
    page.goto('http://127.0.0.1:8000')
    categories=page.request.get('http://127.0.0.1:8000/api/categories').json()['categories']
    assert {c['category_id'] for c in categories}=={1,2,3,4,5,9}
    page.locator('[data-intent=products]').click()
    page.locator('.instrument-option').nth(len(categories)-1).wait_for()
    assert page.locator('.instrument-option').count()==len(categories)
    page.wait_for_function("[...document.querySelectorAll('.instrument-image use')].every(node=>node.getBBox().width>0)")
    page.screenshot(path='/tmp/emporio-ink-picker-desktop.png')
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path='/tmp/emporio-ink-picker-mobile.png')
    category_button = page.get_by_role('button',name='Violões',exact=True)
    if category_button.get_attribute('aria-pressed') != 'true': category_button.click()
    page.get_by_role('button', name='Continuar', exact=True).click()
    page.get_by_label('Valor máximo (R$)').fill('10')
    with page.expect_response(lambda response:'/api/catalog/search' in response.url) as empty:
        page.get_by_role('button',name='Ver instrumentos',exact=True).click()
    data=empty.value.json()
    assert data['products']==[] and data['recovery']['reason']=='budget'
    minimum=data['recovery']['price_brl']
    assert data['search']['max_price']=='10.00'
    page.get_by_text('O menor preço disponível é',exact=False).wait_for()
    page.screenshot(path='/tmp/emporio-budget-recovery.png')
    with page.expect_response(lambda response:'/api/catalog/search' in response.url) as accepted:
        page.get_by_role('button',name='Ver opções até',exact=False).click()
    assert accepted.value.request.post_data_json['max_price']==minimum
    page.locator('.search-summary').last.get_by_role('button',name='Alterar orçamento').click()
    assert page.get_by_label('Valor máximo (R$)').input_value().replace('.','').replace(',','.')==minimum
    page.get_by_label('Valor máximo (R$)').fill('1000')
    page.get_by_role('button',name='Ver instrumentos',exact=True).click()
    choices=page.locator('.message').last.locator('.compare-choice input')
    choices.nth(1).wait_for()
    choices.nth(0).check();choices.nth(1).check()
    with page.expect_response(lambda response:'/api/catalog/compare' in response.url) as compared:
        page.get_by_role('button',name='Comparar selecionados (2)',exact=True).click()
    assert len(compared.value.json()['products'])==2
    page.locator('.comparison-table').wait_for()
    assert page.locator('.comparison-table caption').is_visible()
    assert page.get_by_text('Deslize para ver os outros instrumentos →',exact=True).is_visible()
    assert page.locator('.compare-choice input:enabled').count()==0, 'Old selection must be disabled after a new result'
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='/tmp/emporio-comparison-mobile.png')
    assert not model_requests and not errors, (model_requests,errors)
    page.get_by_role('button',name='Nova conversa',exact=True).click()
    assert page.locator('.comparison-table').count()==0
    assert page.locator('.compare-choice').count()==0
    browser.close()
print('Catalog browser OK: six available categories, ink studies, budget consent, preserved filters, selected comparison, mobile and zero model requests.')
