const assert = require('node:assert/strict');
const {readSSE} = require('../app/static/stream.js');

(async () => {
  const encode = new TextEncoder();
  const bytes = encode.encode('data: {"type":"progress","label":"Consultando…"}\r\n\r\ndata: {"type":"delta","text":"Olá"}\n\ndata: {"type":"done","result":{"message":"Olá"}}\n\n');
  const response = {body: new ReadableStream({start(controller) {
    for (let i = 0; i < bytes.length; i += 3) controller.enqueue(bytes.slice(i, i + 3));
    controller.close();
  }})};
  const events = [];
  const result = await readSSE(response, event => events.push(event));
  assert.equal(result.message, 'Olá');
  assert.equal(events[1].text, 'Olá');
  assert.equal(events[0].label, 'Consultando…');
  await assert.rejects(() => readSSE({body: new ReadableStream({start(c) {c.close();}})}, () => {}), /conclu/i);
  console.log('SSE parser OK: split UTF-8, CRLF, progress, delta and incomplete streams.');
})().catch(error => {console.error(error); process.exitCode = 1;});
