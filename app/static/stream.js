/* Incremental SSE framing; never assumes HTTP chunks are JSON/event boundaries. */
async function readSSE(response, onEvent) {
  const reader = response.body.getReader(), decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const chunk = await reader.read();
      buffer += decoder.decode(chunk.value || new Uint8Array(), {stream: !chunk.done});
      if (buffer.length > 262144) throw new Error('Resposta maior que o esperado.');
      let boundary;
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        const frame = buffer.slice(0, boundary.index); buffer = buffer.slice(boundary.index + boundary[0].length);
        const data = frame.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).replace(/^ /, '')).join('\n');
        if (!data) continue;
        const event = JSON.parse(data);
        if (event.type === 'error') throw Object.assign(new Error(event.detail || 'Não foi possível concluir a consulta.'), {status: event.status});
        if (event.type === 'done') {
          if (!event.result || typeof event.result.message !== 'string') throw new Error('Resposta inválida.');
          return event.result;
        }
        onEvent(event);
      }
      if (chunk.done) throw new Error('A resposta não foi concluída. Tente novamente.');
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
globalThis.EmporioStream = {readSSE};
if (typeof module !== 'undefined') module.exports = {readSSE};
