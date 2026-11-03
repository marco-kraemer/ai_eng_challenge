# 15 — Rastrear atendimentos com privacidade no LangSmith

**O que construir:**
Uma conversa produz um trace correlacionado com etapas do grafo, chamadas ao modelo e ferramentas, sem credenciais, mensagens ou dados de pedidos. A falha de telemetria não interrompe o atendimento.

**Bloqueado por:**
- Nenhum — pode iniciar imediatamente

**Status:** done

## Critérios de Aceitação
- [x] Tracing opcional, desligado sem configuração; chave apenas no servidor.
- [x] Trace de uma conversa real aparece no projeto LangSmith e pode ser consultado por ID.
- [x] Etapas, ferramentas e erros são correlacionados por sessão pseudonimizada, sem conteúdo livre ou credenciais.
- [x] Teste prova isolamento concorrente, sanitização e tolerância a falha do exporter.

## Evidência — 2026-11-03
- Testes Python/Node e navegador verificam os contratos locais.
- Streaming OpenAI e trace remoto verificados: `docs/avaliacao-streaming.json`.
- Trace sem prompts ou respostas; métricas incluem usage real e custo estimado.
