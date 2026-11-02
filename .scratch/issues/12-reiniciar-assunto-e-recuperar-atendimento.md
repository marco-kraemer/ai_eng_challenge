# 12 — Iniciar outro assunto e recuperar atendimento sem perder clareza

**O que construir:**
Concluir a experiência de uso: distinguir continuação de outro assunto, cancelar respostas antigas após reinício, restabelecer os cards iniciais e tratar carregamento/erro sem quebrar a navegação. Refinar a composição e os estados interativos nos mesmos fluxos, com verificação visual em desktop e celular.

**Bloqueado por:**
- 10
- 11

**Status:** complete

## Critérios de Aceitação
- [x] Novo assunto descarta contexto, rascunhos e pendências e reabre as quatro intenções; recarregar também começa do zero.
- [x] Erro de rede/provedor oferece caminho de recuperação sem duplicar envios ou apresentar dados antigos como atuais.
- [x] Respostas atrasadas de assunto anterior não aparecem na conversa nova.
- [x] Foco, contraste, navegação por teclado, redução de movimento e ausência de rolagem horizontal são verificados nos fluxos principais.

## Validação

33 testes Python, mypy e teste Node passam. Testes de sessão verificam isolamento, TTL, limites de histórico e reinício; comparação consulta CSV atual e calcula diferença monetária em Python. Playwright em navegador real verificou entrada por teclado, ações contextuais, identificação de conversa, fontes expansíveis, rascunho/cópia, mobile sem overflow horizontal, reinício, repetição após erro e movimento reduzido. O teste Node cobre descarte de resposta atrasada após novo assunto. Backend simulado nas verificações visuais, sem consumo de cota. Respostas livres e decisões do modelo continuam sujeitas a erro e revisão.
