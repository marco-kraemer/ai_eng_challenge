# 16 — Medir custo, tokens e latência por atendimento

**O que construir:**
Cada atendimento tem métricas reais de chamadas, tokens, cache, etapas e tempo; uma avaliação reproduzível gera relatório agregado sem inventar valores ausentes.

**Bloqueado por:**
- 15

**Status:** done

## Critérios de Aceitação
- [x] Usage real do provedor diferencia entrada, saída e tokens em cache; preço versionado e estimativa identificada.
- [x] Relatório inclui sucesso, erros de infraestrutura separados de falha semântica, mediana/p95 e custo por atendimento.
- [x] Perguntas institucionais e consultas guiadas contabilizam zero chamadas à LLM.
- [x] Falha ou ausência de usage não é registrada como consumo zero; testes verificam agregação e custos.

## Evidência — 2026-11-03
- Testes Python/Node e navegador verificam os contratos locais.
- Streaming OpenAI e trace remoto verificados: `docs/avaliacao-streaming.json`.
- Trace sem prompts ou respostas; métricas incluem usage real e custo estimado.
