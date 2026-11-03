# 18 — Mostrar progresso real da consulta no chat

**O que construir:**
Ao enviar uma mensagem, o cliente vê confirmação imediata e etapas reais como consulta ao catálogo/manual, com tratamento de falha, reinício e concorrência.

**Bloqueado por:**
- Nenhum — pode iniciar imediatamente

**Status:** done

## Critérios de Aceitação
- [x] Endpoint SSE usa o mesmo controle de sessão, limites e execução da rota JSON.
- [x] Eventos de progresso representam etapas executadas e não expõem prompts, argumentos ou raciocínio.
- [x] Interface lê eventos fragmentados, evita envios duplicados e descarta respostas antigas após reset.
- [x] Testes verificam término, erro, liberação de leases e UI acessível.

## Evidência — 2026-11-03
- Testes Python/Node e navegador verificam os contratos locais.
- Streaming OpenAI e trace remoto verificados: `docs/avaliacao-streaming.json`.
- Trace sem prompts ou respostas; métricas incluem usage real e custo estimado.
