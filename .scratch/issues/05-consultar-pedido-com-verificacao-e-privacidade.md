# 05 — Consultar pedido com verificação e privacidade

**O que construir:**
Entregar consulta de pedido no chat solicitando número do pedido e e-mail da compra. O backend cruza `data/orders.csv` com `data/customers.csv` e verifica os dois dados antes de retornar informações.

Projetar o resultado da ferramenta para conter somente status, previsão e código de rastreio quando disponíveis. Não enviar ao modelo cadastro completo, nome, e-mail armazenado, telefone, endereço, observações internas ou outros campos desnecessários. Documentar a limitação de número + e-mail como verificação fraca e a necessidade de autenticação adequada em produção.

**Bloqueado por:**
- 01 — Consultar produtos pelo chat

**Status:** ready-for-agent

**Referência:** `docs/decisoes-do-projeto-agente-artefact.md`

## Critérios de Aceitação
- [ ] O fluxo com número e e-mail correspondentes retorna somente status, previsão e rastreio disponíveis.
- [ ] Pedido inexistente e e-mail incorreto recebem a mesma resposta genérica, sem revelar qual dado estava correto.
- [ ] Informações do pedido não são retornadas antes da verificação dos dois dados.
- [ ] Testes automatizados inspecionam também o payload da ferramenta entregue ao modelo, garantindo ausência de cadastro e observações internas.
- [ ] Testes cobrem correspondência válida, incorreta, pedido inexistente, entrada inválida, campos opcionais ausentes e erro de consulta.
- [ ] O agente não afirma rastreamento ao vivo: explica que usa dados registrados e orienta consulta à transportadora ou contato com a loja.
- [ ] Dados pessoais e credenciais de verificação não são gravados em logs de aplicação ou histórico persistente; a limitação de segurança está documentada.
