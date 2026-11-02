# 06 — Encaminhar a conclusão da compra

**O que construir:**
Completar a jornada de venda: depois de entender preferências, comparar instrumentos e esclarecer condições, ajudar o cliente a decidir e encaminhá-lo ao canal oficial aplicável encontrado nas fontes.

Manter as ferramentas somente leitura. O agente não cria carrinho, pedido, reserva, cupom ou pagamento, e não afirma ter aberto chamado ou transferido atendimento. Quando não conseguir resolver, admite a limitação e orienta contato verificado.

**Bloqueado por:**
- 02 — Conduzir a escolha e comparar instrumentos
- 03 — Responder políticas com fontes do manual
- 04 — Apresentar promoções e condições de pagamento

**Status:** ready-for-agent

**Referência:** `docs/decisoes-do-projeto-agente-artefact.md`

## Critérios de Aceitação
- [ ] Um cenário de compra percorre descoberta, recomendação, comparação, condições verificadas e encaminhamento ao canal oficial.
- [ ] O contato indicado existe na fonte e corresponde ao canal aplicável; ambiguidade material é explicada.
- [ ] Pedidos para reservar estoque, criar carrinho, pagar ou conceder desconto recebem explicação cortês sobre capacidades e próximo passo disponível.
- [ ] Testes automatizados verificam a jornada, a origem do contato e ausência de chamadas de mutação ou afirmações de ações não realizadas.
- [ ] Uma solicitação fora de escopo não expulsa o cliente nem impede que a conversa continue dentro do escopo.
