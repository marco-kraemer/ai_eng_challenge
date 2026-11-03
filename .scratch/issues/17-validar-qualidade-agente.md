# 17 — Validar agente real, fontes, personalidade e contexto

**O que construir:**
Um conjunto de conversas reais verifica contexto, categorias, recusas, fontes e voz do Tom, registra falhas e conclui a validação remanescente do ticket 14.

**Bloqueado por:**
- 15
- 16

**Status:** done

## Critérios de Aceitação
- [x] Casos novos de orçamento, troca de categoria, união/todas, confirmação/recusa e mudança de teto passam com modelo real.
- [x] Conversa longa, isolamento e reset são verificados pela API.
- [x] Tentativas de alterar identidade, revelar instruções e tarefas fora de escopo são recusadas sem acesso a pedidos.
- [x] Revisão de respostas reais verifica persona, concisão e afirmações sustentadas pelos dados; falhas são corrigidas e reavaliadas.
- [x] Avaliação live é opt-in, tem limite de chamadas/custo e salva relatório com modelo, revisão do código e limitações.

## Encerramento — 2026-11-03
- Avaliação live ampliada: 26/26 contratos, 40 chamadas, US$ 0,0237872 estimados; `docs/avaliacao-agente.json`.
- Revisão qualitativa e imperfeições: `docs/observabilidade-e-avaliacao.md`. Não é garantia de ausência de alucinação.
- CI remoto aprovado em `185dfcc`, incluindo a regressão adicional de streaming com Redis real.
