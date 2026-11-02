// Minimal DOM harness for the short return-channel continuation; no browser dependency.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor() { this.children = []; this.events = new Map(); this.value = ''; this.disabled = false; }
  append(...items) { this.children.push(...items); }
  addEventListener(name, fn) { this.events.set(name, fn); }
  replaceChildren() { this.children = []; }
  setAttribute() {}
  removeAttribute() {}
  focus() {}
}
(async () => {
  const nodes = new Map();
  const requests = [];
  const replies = [
    {message: 'Online ou loja física?', products: [], sources: [], needs_return_channel: true},
    {message: 'Consulte a regra de arrependimento.', products: [], sources: [{pages: [4], title: 'Devolução online', text: 'Evidência extraída.'}]},
    {message: 'Online ou loja física?', products: [], sources: [], needs_return_channel: true},
    {message: 'Olá!', products: [], sources: []},
  ];
  const context = vm.createContext({Intl, AbortController, setTimeout, clearTimeout, document: {
    querySelector: selector => {if (!nodes.has(selector)) nodes.set(selector, new Element()); return nodes.get(selector);},
    querySelectorAll: () => [], createElement: () => new Element(), createTextNode: text => ({textContent: text}),
  }, fetch: async (url, options) => {requests.push(JSON.parse(options.body)); return {ok: true, json: async () => await replies.shift()};}});
  const script = fs.readFileSync('app/static/index.html', 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
  vm.runInContext(script, context);
  await vm.runInContext('submit("Posso devolver um instrumento?")', context);
  await vm.runInContext('submit("Comprei online")', context);
  assert.match(requests[1].message, /Posso devolver um instrumento/);
  assert.match(requests[1].message, /Comprei online/);
  assert.equal(vm.runInContext('pendingReturnQuestion', context), '');
  function descendants(node) { return [node, ...(node.children || []).flatMap(descendants)]; }
  assert.equal(descendants(nodes.get('#messages')).filter(n => n.className === 'source').length, 1);
  await vm.runInContext('submit("Quero devolver")', context);
  nodes.get('#new').events.get('click')();
  await vm.runInContext('submit("Oi")', context);
  assert.equal(requests[3].message, 'Oi');
  let resolveOld;
  replies.push(new Promise(resolve => {resolveOld=resolve;}));
  const running=vm.runInContext('submit("pergunta antiga")',context);
  await Promise.resolve();
  nodes.get('#new').events.get('click')();
  resolveOld({message:'Resposta antiga que não pode aparecer.',products:[],sources:[]});
  await running;
  assert.equal(nodes.get('#messages').children.length,0,'Late response must not repopulate a new conversation');
  assert.equal(nodes.get('.send').disabled,false);
  console.log('OK: return-channel continuation, source rendering and reset (minimal DOM harness).');
})().catch(error => { console.error(error); process.exitCode = 1; });
