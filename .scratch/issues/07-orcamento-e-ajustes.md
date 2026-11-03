# 07 — Encontrar alternativa de preço com consentimento

**O que construir:**
Quando o orçamento não alcança o catálogo, sugerir o menor preço real acima do teto, pedindo confirmação antes de ampliar. Manter categoria e orçamento ajustáveis.

**Bloqueado por:**
- 05

**Status:** done

## Critérios de Aceitação
- [x] Busca vazia diferencia preço insuficiente de ausência de estoque e erro.
- [x] Sugestão considera o menor preço elegível real e não altera o teto original.
- [x] Botão explícito confirma nova consulta revalidada sem LLM; ajustes preservam categoria e orçamento.
