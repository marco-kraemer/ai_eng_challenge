# 06 — Encaminhar a conclusão da compra

**O que construir:**
Completar a jornada de venda: depois de entender preferências, comparar instrumentos e esclarecer condições, ajudar o cliente a decidir e encaminhá-lo ao canal oficial aplicável encontrado nas fontes.

Manter as ferramentas somente leitura. O agente não cria carrinho, pedido, reserva, cupom ou pagamento, e não afirma ter aberto chamado ou transferido atendimento. Quando não conseguir resolver, admite a limitação e orienta contato verificado.

**Bloqueado por:**
- 02 — Conduzir a escolha e comparar instrumentos
- 03 — Responder políticas com fontes do manual
- 04 — Apresentar promoções e condições de pagamento

**Status:** complete

**Referência:** `docs/decisoes-do-projeto-agente-artefact.md`

## Critérios de Aceitação
- [x] Um cenário de compra percorre descoberta, recomendação, comparação, condições verificadas e encaminhamento ao canal oficial.
- [x] O contato indicado existe na fonte e corresponde ao canal aplicável; ambiguidade material é explicada.
- [x] Pedidos para reservar estoque, criar carrinho, pagar ou conceder desconto recebem explicação cortês sobre capacidades e próximo passo disponível.
- [x] Testes automatizados verificam a jornada, a origem do contato e ausência de chamadas de mutação ou afirmações de ações não realizadas.
- [x] Uma solicitação fora de escopo não expulsa o cliente nem impede que a conversa continue dentro do escopo.

## Validação

Ferramenta store_contacts extrai canais do PDF com página, sem escolher um número universal. Testes verificam WhatsApp remoto, dados da empresa e preservação do conflito. Interface mostra canais consultados e fontes. Ferramentas de criar pedido/reserva são recusadas pelo registro; não há envio, carrinho, reserva, transferência ou pagamento. O fluxo de descoberta/comparação/condições/contato usa contexto e ferramentas verificadas nos tickets anteriores.
