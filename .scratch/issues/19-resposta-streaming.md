# 19 — Transmitir a resposta final progressivamente

**O que construir:**
A resposta final aparece conforme é gerada pelo provedor; cards, fontes e contexto são publicados atomicamente ao final.

**Bloqueado por:**
- 18

**Status:** done

## Critérios de Aceitação
- [x] Streaming real do provedor, sem simular tokens de um texto já pronto.
- [x] Tokens de classificadores, planejadores e argumentos de ferramentas nunca chegam ao cliente.
- [x] Falha/interrupção não persiste resposta parcial nem permite resposta antiga após reset.
- [x] Usage final é registrado, e rotas FAQ/JSON continuam compatíveis.
- [x] Teste de navegador demonstra texto parcial antes da resposta final, sem duplicação, incluindo recuperação de erro.

## Evidência — 2026-11-03
- Testes Python/Node e navegador verificam os contratos locais.
- Streaming OpenAI e trace remoto verificados: `docs/avaliacao-streaming.json`.
- Trace sem prompts ou respostas; métricas incluem usage real e custo estimado.
