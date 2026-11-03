# 17 — Validar agente real, fontes, personalidade e contexto

**O que construir:**
Um conjunto de conversas reais verifica contexto, categorias, recusas, fontes e voz do Tom, registra falhas e conclui a validação remanescente do ticket 14.

**Bloqueado por:**
- 15
- 16

**Status:** ready-for-agent

## Critérios de Aceitação
- [ ] Casos novos de orçamento, troca de categoria, união/todas, confirmação/recusa e mudança de teto passam com modelo real.
- [ ] Conversa longa, isolamento e reset são verificados pela API.
- [ ] Tentativas de alterar identidade, revelar instruções e tarefas fora de escopo são recusadas sem acesso a pedidos.
- [ ] Revisão de respostas reais verifica persona, concisão e afirmações sustentadas pelos dados; falhas são corrigidas e reavaliadas.
- [ ] Avaliação live é opt-in, tem limite de chamadas/custo e salva relatório com modelo, revisão do código e limitações.
