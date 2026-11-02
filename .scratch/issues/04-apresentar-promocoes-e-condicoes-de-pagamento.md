# 04 — Apresentar promoções e condições de pagamento

**O que construir:**
Responder no chat sobre ofertas e pagamento combinando consultas exatas a `data/promotions.csv` e `data/products.csv` com trechos de política. Validar descontos e calcular valores com precisão monetária no Python.

Apresentar somente promoções ativas confirmadas na base. Não acumular desconto PIX com preço promocional. Parcelas, juros e valores mínimos só podem ser informados com respaldo no manual; divergências geram resposta de incerteza e encaminhamento aplicável.

**Bloqueado por:**
- 01 — Consultar produtos pelo chat
- 03 — Responder políticas com fontes do manual

**Status:** complete

**Referência:** `docs/decisoes-do-projeto-agente-artefact.md`

## Critérios de Aceitação
- [x] O chat apresenta produto, promoção ativa e preço calculado, todos compatíveis com os dados consultados naquele turno.
- [x] Testes automatizados cobrem promoção ativa/inativa, ausência de promoção, percentual inválido, precisão/arredondamento e não acumulação com PIX.
- [x] Condições de parcelamento são acompanhadas de evidência do manual, sem inventar quantidade de parcelas, juros ou mínimos.
- [x] Conflitos de condições de pagamento recebem resposta explícita sobre a incerteza, sem promessa comercial não sustentada.
- [x] Pedidos de criação de cupom, alteração de preço ou desconto sem autorização não provocam mutações nem promessas.
- [x] Erro na consulta é informado como erro, sem ser interpretado como ausência de promoção.

## Validação

Testes de arredondamento, percentuais inválidos, campanhas ativas/inativas, limite monetário, ausência e erro passam. Ferramenta integrada ao loop e cards mostram preço original e desconto confirmado. Parcelamento continua fundamentado no manual e conflitos já foram verificados com o modelo real. Não há ferramenta de cupom ou alteração de preço.
