"""Reproduce the customer bass conversation with real catalog and HTTP requests."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page()
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:8000')
    page.locator('[data-intent=products]').click()
    page.get_by_role('button',name='Baixos',exact=True).click()
    page.get_by_label('Valor máximo (R$)').fill('500')
    with page.expect_response(lambda response:'/api/catalog/search' in response.url) as offered:
        page.get_by_role('button',name='Ver instrumentos',exact=True).click()
    offer=offered.value.json()
    assert offer['products']==[] and offer['recovery']['reason']=='budget'
    page.locator('#message-input').fill('quero ver, me dá o que você tem')
    with page.expect_response(lambda response:'/api/chat' in response.url) as accepted:
        page.locator('#message-form .send').click()
    result=accepted.value.json()
    assert accepted.value.status==200 and result['products']
    assert result['search']['max_price']==offer['recovery']['price_brl']
    assert all(product['category_id']==2 for product in result['products'])
    page.locator('.product').first.wait_for()
    assert 'ID 2' not in result['message']
    assert page.locator('.typing-indicator').count()==0
    assert not errors,errors
    browser.close()
print('Budget context browser OK: basses up to 500 → offer → typed confirmation → current bass cards at offered budget.')
