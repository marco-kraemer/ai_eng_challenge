// Minimal DOM harness. Real rendering and keyboard interaction use browser_smoke.py.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag = 'div') { this.tagName = tag; this.children = []; this.events = new Map(); this.attributes = new Map(); this.value = ''; this.disabled = false; }
  append(...items) { for (const item of items) {item.parentNode = this; this.children.push(item);} }
  remove() {if (this.parentNode) this.parentNode.children = this.parentNode.children.filter(child => child !== this);}
  addEventListener(name, fn) { this.events.set(name, fn); }
  replaceChildren() { this.children = []; }
  setAttribute(name, value) { this.attributes.set(name, String(value)); if (name === 'class') this.className = value; }
  removeAttribute(name) { this.attributes.delete(name); }
  querySelectorAll(tag) { return descendants(this).filter(n => n !== this && n.tagName === tag); }
  focus() {}
}
function descendants(node) { return [node, ...(node.children || []).flatMap(descendants)]; }
(async () => {
  const nodes = new Map(), requests = [], resets = [], replies = [];
  const context = vm.createContext({Intl, AbortController, setTimeout, clearTimeout, document: {
    querySelector: selector => { if (!nodes.has(selector)) nodes.set(selector, new Element()); return nodes.get(selector); },
    querySelectorAll: () => [], createElement: tag => new Element(tag), createElementNS: (ns, tag) => new Element(tag), createTextNode: text => ({textContent: text}),
  }, fetch: async (url, options = {}) => {
    if (url === '/api/categories') return {ok: true, json: async () => ({categories: [{category_id: 1, name: 'Guitarras', label: 'Guitarras', illustration: '/assets/instruments.svg#guitarra'}, {category_id: 5, name: 'Violões', label: 'Violões', illustration: '/assets/instruments.svg#violao'}]})};
    if (url === '/api/conversation/reset') {resets.push(JSON.parse(options.body)); return {ok: true};}
    requests.push({url, ...JSON.parse(options.body)});
    return {ok: true, json: async () => await replies.shift()};
  }});
  vm.runInContext(fs.readFileSync('app/static/chat.js', 'utf8'), context);
  const facts = JSON.parse(vm.runInContext('JSON.stringify(productFacts({specs:{strings:"nylon",electronics:"no",scale:"650mm",top:"Spruce",unknown:"Ignore"}}))', context));
  assert.deepEqual(facts, [['Cordas','nylon'],['Captação','Sem captação'],['Escala','650mm']]);
  assert.equal(vm.runInContext('productFacts({}).length', context), 0);
  for (const [raw, expected] of [['1.000,50', '1000.50'], ['1000.50', '1000.50'], ['1.000', '1000.00'], ['500', '500.00'], ['R$ 2.000,00', '2000.00'], ['', null], ['-1', null], ['NaN', null], ['1,234', null], ['1.23.4', null]]) {
    assert.equal(vm.runInContext(`parseBudget(${JSON.stringify(raw)})`, context), expected);
  }
  replies.push({message: 'Online ou loja física?', products: [], sources: [], conversation_id: 'session-a', needs_return_channel: true});
  await vm.runInContext('submit("Posso devolver um instrumento?")', context);
  replies.push({message: 'Consulte a regra de arrependimento.', products: [], sources: [{pages: [4], title: 'Devolução online', text: 'Evidência.'}], conversation_id: 'session-a'});
  await vm.runInContext('submit("Comprei online")', context);
  assert.equal(requests[1].conversation_id, 'session-a');
  assert.equal(requests[1].message, 'Comprei online');
  assert.equal(descendants(nodes.get('#messages')).filter(n => n.className === 'source-item').length, 1);
  nodes.get('#new').events.get('click')();
  assert.equal(resets[0].conversation_id, 'session-a');
  let resolveOld;
  replies.push(new Promise(resolve => {resolveOld = resolve;}));
  const running = vm.runInContext('submit("pergunta antiga")', context);
  await Promise.resolve();
  assert.equal(descendants(nodes.get('#messages')).filter(n => n.className === 'message typing-indicator').length, 1, 'Typing indicator must appear before the response');
  assert.equal(nodes.get('#message-form .send').disabled, true);
  const pendingCount = requests.length;
  await vm.runInContext('submit("mensagem repetida")', context);
  assert.equal(requests.length, pendingCount, 'Repeated submissions must not send requests');
  nodes.get('#new').events.get('click')();
  resolveOld({message: 'Resposta que não pode aparecer.', products: [], sources: []}); await running;
  assert.equal(nodes.get('#messages').children.length, 0);
  assert.equal(nodes.get('#message-form .send').disabled, false);
  const before = requests.length;
  await vm.runInContext('openFinder()', context);
  assert.equal(requests.length, before, 'Opening a category picker must not send a model request');
  const option = descendants(nodes.get('#picker')).find(n => n.attributes?.get('data-category-id') === '1');
  option.events.get('click')();
  replies.push({message: 'Opções de guitarras.', products: [], sources: [], conversation_id: 'session-b'});
  await vm.runInContext('searchSelectedCatalog("1500.50")', context);
  assert.equal(requests.at(-1).url, '/api/catalog/search');
  assert.equal(requests.at(-1).category_id, 1);
  assert.equal(requests.at(-1).max_price, '1500.50');
  replies.push({message: 'Opções sem limite definido.', products: [], sources: []});
  await vm.runInContext('searchSelectedCatalog(null)', context);
  assert.equal(Object.hasOwn(requests.at(-1), 'max_price'), false);
  await vm.runInContext('openFinder()', context);
  let buttons = descendants(nodes.get('#picker'));
  let first = buttons.find(n => n.attributes?.get('data-category-id') === '1');
  const second = buttons.find(n => n.attributes?.get('data-category-id') === '5');
  assert.equal(first.attributes.get('aria-pressed'), 'true');
  const requestCount = requests.length;
  second.events.get('click')();
  assert.equal(requests.length, requestCount, 'Toggling categories must not query or navigate away');
  replies.push({message: 'Duas categorias.', products: [], sources: []});
  await vm.runInContext('searchSelectedCatalog("1000.00")', context);
  assert.deepEqual(requests.at(-1).category_ids, [1, 5]);
  assert.equal(Object.hasOwn(requests.at(-1), 'category_id'), false);
  await vm.runInContext('openFinder()', context);
  buttons = descendants(nodes.get('#picker'));
  buttons.find(n => n.className === 'all-instruments').events.get('click')();
  replies.push({message: 'Todos os instrumentos.', products: [], sources: []});
  await vm.runInContext('searchSelectedCatalog("1000.00")', context);
  assert.deepEqual(requests.at(-1).category_ids, []);
  assert.equal(Object.hasOwn(requests.at(-1), 'category_id'), false);
  console.log('OK: customer picker, BRL values, explicit category/budget, no default budget, conversation IDs, sources and late-response reset.');
})().catch(error => {console.error(error); process.exitCode = 1;});
