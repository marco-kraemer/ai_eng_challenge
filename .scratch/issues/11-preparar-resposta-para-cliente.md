# 11 — Preparar e copiar resposta para o cliente com evidências

**O que construir:**
A partir de uma orientação baseada em fontes, permitir preparar uma mensagem curta para encaminhar ao cliente. Separar visualmente orientação do atendimento, rascunho e evidências; copiar exige clique explícito, sem enviar mensagens para serviços externos.

**Bloqueado por:**
- 10
- 03

**Status:** complete

## Critérios de Aceitação
- [x] O rascunho usa somente fatos do atendimento atual e mantém limites e conflitos relevantes.
- [x] Copiar funciona com feedback acessível e apresenta alternativa selecionável se a área de transferência falhar.
- [x] Nenhuma mensagem é enviada automaticamente; testes verificam preservação das fontes e fluxo de cópia.

## Validação

33 testes Python, mypy e teste Node passam. Testes de sessão verificam isolamento, TTL, limites de histórico e reinício; comparação consulta CSV atual e calcula diferença monetária em Python. Playwright em navegador real verificou entrada por teclado, ações contextuais, identificação de conversa, fontes expansíveis, rascunho/cópia, mobile sem overflow horizontal, reinício, repetição após erro e movimento reduzido. O teste Node cobre descarte de resposta atrasada após novo assunto. Backend simulado nas verificações visuais, sem consumo de cota. Respostas livres e decisões do modelo continuam sujeitas a erro e revisão.
