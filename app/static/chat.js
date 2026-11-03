const form = document.querySelector('#message-form');
const input = document.querySelector('#message-input');
const send = document.querySelector('#message-form .send');
const messages = document.querySelector('#messages');
const status = document.querySelector('#status');
const conversation = document.querySelector('#conversation');
const welcome = document.querySelector('#welcome');
const picker = document.querySelector('#picker');
const reset = document.querySelector('#new');
const orderShortcut = document.querySelector('#order-shortcut');
const money = new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'});
let conversationId = null;
let activeRequest = null;
let generation = 0;
let pickerLoad = 0;
let categories = [];
let selectedCategory = null;
let selectedBudget = null;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function scroll() { conversation.scrollTop = conversation.scrollHeight; }
function bodyText(text) {
  const node = element('div', 'body');
  text.split(/(\*\*[^*]+\*\*)/g).forEach(piece => {
    node.append(piece.startsWith('**') && piece.endsWith('**')
      ? element('strong', '', piece.slice(2, -2)) : document.createTextNode(piece));
  });
  return node;
}
function instrumentImage(reference) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'instrument-image');
  svg.setAttribute('viewBox', '0 0 180 150');
  svg.setAttribute('aria-hidden', 'true');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', reference.startsWith('/assets/instruments.svg#') ? reference : '/assets/instruments.svg#generico');
  svg.append(use);
  return svg;
}
function showMessages() {
  pickerLoad++;
  picker.hidden = true;
  welcome.hidden = true;
  messages.hidden = false;
}
function goBack() {
  pickerLoad++;
  picker.hidden = true;
  messages.hidden = false;
  welcome.hidden = messages.children.length > 0;
  conversation.scrollTop = 0;
}
function pickerHeading(title, description, step, back = goBack) {
  picker.replaceChildren();
  const top = element('div', 'picker-top');
  const button = element('button', 'quiet', '← Voltar');
  button.type = 'button';
  button.addEventListener('click', back);
  top.append(button, element('span', 'steps', step));
  const heading = element('h2', '', title);
  heading.tabIndex = -1;
  picker.append(top, heading, element('p', '', description));
  heading.focus({preventScroll: true});
  conversation.scrollTop = 0;
}
async function openFinder() {
  if (send.disabled) return;
  const load = ++pickerLoad, currentGeneration = generation;
  welcome.hidden = true; messages.hidden = true; picker.hidden = false;
  pickerHeading('Qual instrumento você procura?', 'Escolha uma categoria para ver as opções.', '1. Instrumento · 2. Orçamento');
  const loading = element('p', '', 'Carregando instrumentos…');
  loading.setAttribute('role', 'status'); picker.append(loading);
  try {
    const response = await fetch('/api/categories');
    if (!response.ok) throw new Error('categories');
    const data = await response.json();
    if (load !== pickerLoad || currentGeneration !== generation) return;
    categories = data.categories;
    renderCategories();
  } catch {
    if (load !== pickerLoad || currentGeneration !== generation) return;
    loading.textContent = 'Não foi possível carregar os instrumentos.';
    const retry = element('button', 'quiet', 'Tentar novamente');
    retry.type = 'button'; retry.addEventListener('click', openFinder); picker.append(retry);
  }
}
function renderCategories() {
  pickerHeading('Qual instrumento você procura?', 'Escolha uma categoria para ver as opções.', '1. Instrumento · 2. Orçamento');
  const grid = element('div', 'instrument-grid');
  for (const category of categories) {
    const button = element('button', 'instrument-option');
    button.type = 'button'; button.setAttribute('data-category-id', category.category_id);
    button.append(instrumentImage(category.illustration), element('strong', '', category.label));
    button.addEventListener('click', () => {if (selectedCategory?.category_id !== category.category_id) selectedBudget = null; selectedCategory = category; renderBudget();});
    grid.append(button);
  }
  if (!categories.length) picker.append(element('p', 'empty-catalog', 'Não há instrumentos em estoque no momento. Você pode consultar as informações da loja ou voltar mais tarde.'));
  picker.append(grid);
}
function parseBudget(raw) {
  let value = raw.trim().replace(/^R\$\s*/, '').replace(/\s/g, '');
  if (value.includes(',')) {
    if (!/^(\d{1,3}(\.\d{3})*|\d+),\d{1,2}$/.test(value)) return null;
    value = value.replace(/\./g, '').replace(',', '.');
  } else if (/^\d{1,3}(\.\d{3})+$/.test(value)) value = value.replace(/\./g, '');
  else if (!/^\d+(\.\d{1,2})?$/.test(value)) return null;
  const amount = Number(value);
  return Number.isFinite(amount) && amount > 0 && amount <= 10000000 ? amount.toFixed(2) : null;
}
function renderBudget() {
  pickerHeading('Quanto você quer gastar?', 'Escolha um valor máximo ou continue sem definir um preço.', '1. Instrumento · 2. Orçamento', renderCategories);
  const selection = element('div', 'selected-instrument');
  const change = element('button', 'quiet', 'Trocar instrumento');
  change.type = 'button'; change.addEventListener('click', renderCategories);
  selection.append(instrumentImage(selectedCategory.illustration), element('strong', '', selectedCategory.label), change);
  const options = element('div', 'budget-options');
  const budgetForm = element('form', 'budget-form');
  const label = element('label', '', 'Valor máximo (R$)'); label.htmlFor = 'budget-input';
  const field = element('input'); field.id = 'budget-input'; field.type = 'text'; field.inputMode = 'decimal'; field.placeholder = 'Ex.: 1.500,00'; field.autocomplete = 'off';
  if (selectedBudget !== null) field.value = Number(selectedBudget).toLocaleString('pt-BR', {minimumFractionDigits: 2});
  const error = element('div', 'budget-error'); error.setAttribute('role', 'alert');
  const confirm = element('button', 'send', 'Ver instrumentos'); confirm.type = 'submit';
  for (const amount of [500, 1000, 2000, 5000]) {
    const button = element('button', 'budget-option', 'Até ' + money.format(amount));
    button.type = 'button'; button.setAttribute('aria-pressed', 'false');
    button.addEventListener('click', () => {
      field.value = amount.toLocaleString('pt-BR', {minimumFractionDigits: 2}); error.textContent = '';
      options.querySelectorAll('button').forEach(other => other.setAttribute('aria-pressed', other === button ? 'true' : 'false'));
    });
    options.append(button);
  }
  field.addEventListener('input', () => {error.textContent = ''; options.querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', 'false'));});
  const skip = element('button', 'skip-budget', 'Ainda não defini um valor'); skip.type = 'button';
  skip.addEventListener('click', () => searchSelectedCatalog(null));
  budgetForm.addEventListener('submit', event => {
    event.preventDefault(); const budget = parseBudget(field.value);
    if (budget === null) {error.textContent = 'Informe um valor válido ou escolha “Ainda não defini um valor”.'; field.focus(); return;}
    searchSelectedCatalog(budget);
  });
  budgetForm.append(label, field, error, confirm, skip);
  picker.append(selection, options, budgetForm);
}
function searchSelectedCatalog(budget) {
  const category = selectedCategory;
  selectedBudget = budget;
  const message = 'Quero ver ' + category.name.toLocaleLowerCase('pt-BR') + (budget === null ? '. Ainda não defini um orçamento.' : ' até ' + money.format(Number(budget)) + '.');
  const payload = {category_id: category.category_id};
  if (budget !== null) payload.max_price = budget;
  return requestReply(message, '/api/catalog/search', payload);
}
const HELP = {
  purchase: {
    title: 'Qual é a sua dúvida?', description: 'Escolha um assunto sobre sua compra.',
    topics: [
      ['Trocar ou devolver', 'Quero trocar ou devolver uma compra.'],
      ['Produto com defeito', 'Meu instrumento apresentou um defeito. Como posso resolver?'],
      ['Entrega e frete', 'Como funciona a entrega? Quero saber o prazo e o frete.'],
      ['Formas de pagamento', 'Quais formas de pagamento vocês aceitam?'],
      ['Garantia', 'Como funciona a garantia dos instrumentos?']
    ]
  },
  store: {
    title: 'O que você quer saber?', description: 'Escolha uma informação sobre a loja.',
    topics: [
      ['Horários de atendimento', 'Quais são os horários de atendimento da loja?'],
      ['Endereço da loja', 'Qual é o endereço da loja?'],
      ['Falar com a loja', 'Como posso falar com a loja?']
    ]
  }
};
function openHelp(kind) {
  if (send.disabled) return;
  pickerLoad++; welcome.hidden = true; messages.hidden = true; picker.hidden = false;
  const menu = HELP[kind];
  pickerHeading(menu.title, menu.description, '');
  const grid = element('div', 'help-grid');
  for (const [label, question] of menu.topics) {
    const button = element('button', 'help-option'); button.type = 'button';
    button.append(element('span', '', label), element('span', 'arrow', '→'));
    button.addEventListener('click', () => submit(question)); grid.append(button);
  }
  picker.append(grid);
}
function openOrder() {
  if (send.disabled) return;
  showMessages(); add('Consulte seu pedido com os dados da compra.', false, [], [], [], true);
}
const SPEC_LABELS = {strings: 'Cordas', electronics: 'Captação', scale: 'Escala', keys: 'Teclas', frets: 'Trastes', body: 'Corpo', type: 'Tipo', size: 'Tamanho', top: 'Tampo'};
function productFacts(product) {
  const facts = [];
  for (const [key, label] of Object.entries(SPEC_LABELS)) {
    const value = product.specs?.[key];
    if (value === undefined || value === null || value === '') continue;
    const readable = key === 'electronics' ? ({yes: 'Com captação', no: 'Sem captação'}[value] || String(value)) : String(value);
    facts.push([label, readable]);
    if (facts.length === 3) break;
  }
  return facts;
}
function comparisonTable(products) {
  const wrapper = element('div', 'comparison-scroll'); wrapper.tabIndex = 0;
  wrapper.setAttribute('role', 'region'); wrapper.setAttribute('aria-label', 'Comparação de instrumentos');
  const table = element('table', 'comparison-table');
  table.append(element('caption', '', 'Características informadas no catálogo'));
  const head = element('tr'); head.append(element('th', '', 'Característica'));
  for (const product of products) {const cell = element('th', '', product.name); cell.setAttribute('scope', 'col'); head.append(cell);}
  table.append(head);
  const rows = [['Preço de tabela', p => money.format(Number(p.price_brl))], ['Disponibilidade', p => p.stock_quantity > 0 ? 'Em estoque' : 'Sem estoque']];
  for (const [key, label] of Object.entries(SPEC_LABELS)) {
    if (products.some(p => p.specs?.[key] !== undefined)) rows.push([label, p => p.specs?.[key] === undefined ? 'Não informado' : key === 'electronics' ? ({yes: 'Com captação', no: 'Sem captação'}[p.specs[key]] || String(p.specs[key])) : String(p.specs[key])]);
  }
  if (products.some(p => p.budget_difference_brl !== undefined)) rows.push(['Acima do orçamento', p => money.format(Number(p.budget_difference_brl))]);
  for (const [label, value] of rows) {
    const row = element('tr'), heading = element('th', '', label); heading.setAttribute('scope', 'row'); row.append(heading);
    for (const product of products) row.append(element('td', '', value(product)));
    table.append(row);
  }
  wrapper.append(element('p', 'comparison-hint', 'Deslize para ver os outros instrumentos →'), table); return wrapper;
}
function add(text, user = false, products = [], sources = [], actions = [], orderVerification = false, contacts = [], search = null, comparison = false) {
  const item = element('article', 'message' + (user ? ' user' : ''));
  const label = element('div', 'label');
  if (!user) label.append(element('span', 'mini', '♪'));
  label.append(document.createTextNode(user ? 'Você' : 'Tom · Empório da Música'));
  item.append(label, bodyText(text));
  if (orderVerification) item.append(orderWidget());
  if (search) {
    const summary = element('div', 'search-summary');
    summary.append(element('span', '', search.label + ' · ' + (search.max_price === null ? 'Sem limite de preço' : 'Até ' + money.format(Number(search.max_price))) + ' · Em estoque'));
    const edit = element('button', 'quiet', 'Alterar orçamento'); edit.type = 'button';
    edit.addEventListener('click', () => {if (send.disabled) return; selectedCategory = search; selectedBudget = search.max_price; welcome.hidden = true; messages.hidden = true; picker.hidden = false; renderBudget();});
    summary.append(edit); item.append(summary);
  }
  if (products.length || search) document.querySelectorAll('.compare-choice input, .compare-selected').forEach(node => {node.disabled = true; if (node.type === 'checkbox') node.checked = false;});
  if (comparison) item.append(comparisonTable(products));
  if (products.length && !comparison) {
    const chosen = new Set();
    const checks = [];
    const compare = element('button', 'quiet compare-selected', 'Comparar selecionados'); compare.type = 'button'; compare.disabled = true;
    compare.addEventListener('click', () => {
      if (send.disabled || chosen.size < 2) return;
      const payload = {product_ids: [...chosen]};
      const budget = search ? search.max_price : selectedBudget;
      if (budget !== null) payload.max_price = budget;
      return requestReply('Quero comparar os instrumentos selecionados.', '/api/catalog/compare', payload);
    });
    const grid = element('div', 'products');
    for (const product of products) {
      const card = element('article', 'product');
      card.append(element('div', 'product-top', product.stock_quantity > 0 ? 'Em estoque' : 'Sem estoque'), element('h3', '', product.name), element('p', 'description', product.description));
      if (product.original_price_brl) {
        const original = element('div', 'original-price');
        original.append(element('del', '', money.format(Number(product.original_price_brl))), document.createTextNode(product.discount_percent + '% de desconto'));
        card.append(original);
      }
      const facts = element('dl', 'product-facts');
      for (const [label, value] of productFacts(product)) facts.append(element('dt', '', label), element('dd', '', value));
      card.append(facts);
      if (products.length >= 2) {
        const choice = element('label', 'compare-choice');
        const checkbox = element('input'); checkbox.type = 'checkbox'; checkbox.setAttribute('aria-label', 'Comparar ' + product.name); checks.push(checkbox);
        checkbox.addEventListener('change', () => {
          checkbox.checked ? chosen.add(product.product_id) : chosen.delete(product.product_id);
          compare.disabled = chosen.size < 2;
          compare.textContent = chosen.size ? 'Comparar selecionados (' + chosen.size + ')' : 'Comparar selecionados';
          checks.forEach(node => node.disabled = !node.checked && chosen.size >= 4);
        });
        choice.append(checkbox, document.createTextNode('Comparar')); card.append(choice);
      }
      const bottom = element('div', 'product-bottom'); bottom.append(element('div', 'price', money.format(Number(product.price_brl)))); card.append(bottom); grid.append(card);
    }
    item.append(grid);
    if (products.length >= 2) item.append(compare);
  }
  for (const contact of contacts) {
    const channel = element('div', 'contact-channel');
    channel.append(element('span', '', contact.kind === 'remote' ? 'WhatsApp da loja' : 'Telefone da loja'), element('strong', '', contact.phone), element('small', '', 'Informação da loja · p. ' + contact.pages.join(', '))); item.append(channel);
  }
  if (sources.length) {
    const refs = element('details', 'sources'); refs.append(element('summary', '', 'Consultar informações da loja'));
    for (const source of sources) {
      const detail = element('div', 'source-item');
      detail.append(element('strong', '', source.title + ' · p. ' + source.pages.join(', ')), element('pre', '', source.text)); refs.append(detail);
    }
    item.append(refs);
  }
  if (actions.length) {
    const choices = element('div', 'next-actions');
    for (const action of actions) {
      if (action.id === 'draft') continue;
      const choice = element('button', 'next-action', action.label); choice.type = 'button';
      choice.addEventListener('click', () => {
        if (action.kind === 'catalog_search') {
          selectedCategory = search; selectedBudget = action.selection.max_price;
          return requestReply('Quero ver opções até ' + money.format(Number(selectedBudget)) + '.', '/api/catalog/search', action.selection);
        }
        return action.kind === 'instrument_picker' || action.id === 'categories' ? openFinder() : submit(action.message, action.id);
      }); choices.append(choice);
    }
    item.append(choices);
  }
  messages.append(item); scroll(); return item;
}
function orderWidget() {
  const box = element('section', 'order-box'), title = element('h3', '', 'Meu pedido');
  const hint = element('p', '', 'Informe o número do pedido e o e-mail usado na compra.');
  const orderForm = element('form', 'order-form'), number = element('input'), email = element('input');
  const verify = element('button', 'send', 'Consultar pedido'), feedback = element('div', 'order-feedback');
  number.type = 'text'; number.inputMode = 'numeric'; number.pattern = '[0-9]+'; number.maxLength = 12; number.required = true; number.autocomplete = 'off'; number.placeholder = 'Número do pedido'; number.setAttribute('aria-label', 'Número do pedido');
  email.type = 'email'; email.required = true; email.maxLength = 254; email.autocomplete = 'off'; email.placeholder = 'E-mail da compra'; email.setAttribute('aria-label', 'E-mail da compra'); verify.type = 'submit'; feedback.setAttribute('role', 'status');
  orderForm.append(number, email, verify); box.append(title, hint, orderForm, feedback);
  orderForm.addEventListener('submit', async event => {
    event.preventDefault(); const currentGeneration = generation; verify.disabled = true; feedback.textContent = 'Consultando seu pedido…';
    try {
      const response = await fetch('/api/orders/verify', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({order_id: Number(number.value), email: email.value})});
      const data = await response.json(); if (currentGeneration !== generation) return;
      if (!response.ok) feedback.textContent = typeof data.detail === 'string' ? data.detail : 'Confira os dados e tente novamente.';
      else if (data.status !== 'found') feedback.textContent = 'Não foi possível verificar o pedido com os dados informados. Confira o número e o e-mail da compra.';
      else {
        const names = {pending:'Pendente',processing:'Em processamento',shipped:'Enviado',in_transit:'Em transporte',delivered:'Entregue',cancelled:'Cancelado',canceled:'Cancelado'};
        feedback.textContent = 'Status: ' + (names[data.order.status] || data.order.status) + '\nPrevisão registrada: ' + (data.order.estimated_delivery || 'Não informada') + '\nCódigo de rastreio: ' + (data.order.tracking_code || 'Não informado') + '\n\nEssas informações são do registro do pedido, não um rastreamento ao vivo.';
      }
    } catch { if (currentGeneration === generation) feedback.textContent = 'Não foi possível consultar agora. Tente novamente em instantes.'; }
    finally { number.value = ''; email.value = ''; verify.disabled = false; }
  });
  return box;
}
function showFailure(text, retryAction) {
  const item = add(text), retry = element('button', 'next-action retry', 'Tentar novamente'); retry.type = 'button';
  retry.addEventListener('click', retryAction); item.append(retry); scroll();
}
function showTyping() {
  const item = element('article', 'message typing-indicator');
  // #status announces the wait; keep the decorative bubble out of live announcements.
  item.setAttribute('aria-hidden', 'true');
  const label = element('div', 'label');
  label.append(element('span', 'mini', '♪'), document.createTextNode('Tom · Empório da Música'));
  const bubble = element('div', 'typing-bubble');
  bubble.append(element('span', 'typing-text', 'Digitando'));
  const dots = element('span', 'typing-dots');
  for (let i = 0; i < 3; i++) dots.append(element('span', 'typing-dot'));
  bubble.append(dots); item.append(label, bubble); messages.append(item); scroll();
  return item;
}
function setBusy(busy) {
  send.disabled = busy; orderShortcut.disabled = busy;
  document.querySelectorAll('.intent, .instrument-option, .budget-option').forEach(button => button.disabled = busy);
  if (busy) document.querySelectorAll('.next-action').forEach(button => button.disabled = true);
}
async function submit(message, actionId = null) {
  if (send.disabled || !message.trim()) return;
  if (message.length > 2000) {showMessages(); add('Escreva sua dúvida em até 2.000 caracteres.'); return;}
  return requestReply(message, '/api/chat', {message, action_id: actionId});
}
async function requestReply(displayMessage, url, payload) {
  if (send.disabled) return;
  const currentGeneration = generation, controller = new AbortController(); activeRequest = controller;
  const timeout = setTimeout(() => controller.abort(), 120000);
  showMessages(); add(displayMessage, true); input.value = ''; setBusy(true);
  const pending = showTyping();
  status.textContent = 'Mensagem enviada. O assistente está preparando a resposta…'; form.setAttribute('aria-busy', 'true');
  try {
    const response = await fetch(url, {method: 'POST', signal: controller.signal, headers: {'Content-Type': 'application/json'}, body: JSON.stringify({...payload, conversation_id: conversationId})});
    const data = await response.json(); if (currentGeneration !== generation) return;
    pending.remove();
    if (response.ok) {
      conversationId = data.conversation_id || conversationId;
      add(data.message, false, data.products || [], data.sources || [], data.actions || [], Boolean(data.order_verification_required), data.contacts || [], data.search || null, Boolean(data.comparison));
    } else {
      const explanation = typeof data.detail === 'string' ? data.detail : 'Não foi possível concluir a consulta. Confira sua mensagem e tente novamente.';
      if (response.status === 422) add(explanation);
      else showFailure(explanation, () => requestReply(displayMessage, url, payload));
    }
  } catch (error) {
    if (currentGeneration !== generation) return;
    pending.remove();
    showFailure(error.name === 'AbortError' ? 'A consulta demorou mais que o esperado. Tente novamente ou inicie outra conversa.' : 'Não conseguimos conectar. Confira sua conexão e tente novamente.', () => requestReply(displayMessage, url, payload));
  } finally {
    clearTimeout(timeout); pending.remove();
    if (currentGeneration === generation) {activeRequest = null; setBusy(false); status.textContent = ''; form.removeAttribute('aria-busy'); input.focus();}
  }
}
function resetConversation() {
  generation++; pickerLoad++;
  if (activeRequest) activeRequest.abort(); activeRequest = null;
  if (conversationId) fetch('/api/conversation/reset', {method: 'POST', keepalive: true, headers: {'Content-Type':'application/json'}, body: JSON.stringify({conversation_id: conversationId})}).catch(() => {});
  conversationId = null; selectedCategory = null; selectedBudget = null; messages.replaceChildren(); messages.hidden = false; welcome.hidden = false; picker.hidden = true;
  input.value = ''; setBusy(false); status.textContent = ''; form.removeAttribute('aria-busy'); conversation.scrollTop = 0; input.focus();
}
form.addEventListener('submit', event => {event.preventDefault(); submit(input.value.trim());});
document.querySelectorAll('[data-intent]').forEach(button => button.addEventListener('click', () => {
  if (button.dataset.intent === 'products') openFinder();
  else if (button.dataset.intent === 'order') openOrder();
  else openHelp(button.dataset.intent);
}));
reset.addEventListener('click', resetConversation);
orderShortcut.addEventListener('click', openOrder);
