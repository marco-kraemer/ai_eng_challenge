# 09 — Reproduzir avaliação das jornadas do cliente

**O que construir:**
Publicar conjunto reproduzível de cenários de disponibilidade, orçamento, contexto, políticas e recusa com relatório que distingue modelo simulado de recuperação real.

**Bloqueado por:**
- 05; 06; 07; 08

**Status:** done

## Critérios de Aceitação
- [x] Avaliação executável sem chave mede expectativas por cenário e sai com erro em regressão.
- [x] Documentação explica escopo, limitações e ausência de fotos reais.
- [x] Suíte Python, tipos, Node e navegador passam; todos os tickets ficam concluídos.

## Evidência
- 73 testes Python, mypy e Node passaram.
- Três smokes Chromium passaram, incluindo catálogo com APIs reais e zero chamadas ao chat.
- Avaliação de jornadas: 8/8, com inferência simulada e recuperação real explicitadas no relatório.
