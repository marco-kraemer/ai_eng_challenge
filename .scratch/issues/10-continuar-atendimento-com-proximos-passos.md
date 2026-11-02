# 10 — Continuar atendimento com próximos passos contextuais

**O que construir:**
Retornar ações estruturadas e limitadas junto das respostas e mostrar chips de continuação pertinentes aos dados consultados. Clique preserva contexto temporário e usa ferramentas reais novamente. Ações vêm de um registro permitido no backend e não concedem capacidades novas.

**Bloqueado por:**
- 09
- 02

**Status:** complete

## Critérios de Aceitação
- [x] Catálogo oferece comparação e recorte; políticas oferecem esclarecimento e evidência; situações oferecem próximos passos pertinentes.
- [x] Sugestões de troca/devolução e seguimentos como online ou mais barato mantêm contexto recente com isolamento entre sessões.
- [x] Não há sugestões de carrinho, reserva ou consulta de pedido sem a funcionalidade correspondente disponível; texto livre continua acessível.
- [x] Testes cobrem clique, contexto, lista permitida de ações e ausência de dados inventados.

## Validação

33 testes Python, mypy e teste Node passam. Testes de sessão verificam isolamento, TTL, limites de histórico e reinício; comparação consulta CSV atual e calcula diferença monetária em Python. Playwright em navegador real verificou entrada por teclado, ações contextuais, identificação de conversa, fontes expansíveis, rascunho/cópia, mobile sem overflow horizontal, reinício, repetição após erro e movimento reduzido. O teste Node cobre descarte de resposta atrasada após novo assunto. Backend simulado nas verificações visuais, sem consumo de cota. Respostas livres e decisões do modelo continuam sujeitas a erro e revisão.
