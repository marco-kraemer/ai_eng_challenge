# 07 — Manter o chat seguro e limitado sob falhas e abuso

**O que construir:**
Consolidar limites e proteção nos fluxos existentes: tamanho de entrada, histórico recente, estado mínimo, resultados de ferramentas, chamadas por turno, tokens e taxa de uso. Calibrar e documentar os valores conforme modelo e forma de execução escolhidos.

Garantir isolamento entre sessões e descarte de contexto ao iniciar nova conversa ou fechar e reabrir a página, sem histórico persistente em banco nem sumarização automática. Tratar falhas temporárias com tentativas limitadas; falhas permanentes devem ser diagnosticáveis. Esgotamento da cota gratuita informa indisponibilidade, sem custo automático.

Aplicar defesa em profundidade: validar argumentos e cálculos em Python, restringir capacidades e tratar texto de usuários, documentos e ferramentas como dados sem poder de conceder permissões.

**Bloqueado por:**
- 02 — Conduzir a escolha e comparar instrumentos
- 03 — Responder políticas com fontes do manual
- 04 — Apresentar promoções e condições de pagamento
- 05 — Consultar pedido com verificação e privacidade
- 06 — Encaminhar a conclusão da compra

**Status:** complete

**Referência:** `docs/decisoes-do-projeto-agente-artefact.md`

## Critérios de Aceitação
- [x] Testes automatizados verificam limites de mensagem, histórico, resultados, chamadas, tokens e taxa, incluindo resposta compreensível ao atingir cada limite.
- [x] Duas sessões simultâneas não compartilham preferências, pedidos ou resultados; nova conversa e reabertura da página descartam o contexto anterior.
- [x] Histórico e estado não crescem indefinidamente nem retêm dados antigos de verificação além do necessário.
- [x] Falhas temporárias têm número limitado de tentativas; erros permanentes não entram em loop e geram diagnóstico sem segredos ou dados pessoais.
- [x] Indisponibilidade e cota esgotada não viram afirmação de item inexistente, indisponível ou de resultado inventado, nem acionam serviço pago.
- [x] Testes adversariais cobrem instruções em mensagens, trechos do manual e resultados de ferramentas tentando revelar dados, alterar regras ou executar ações.
- [x] O agente continua cortês diante de solicitações suspeitas; limites de uso controlam repetição abusiva.
- [x] Prompt, validações e restrições têm suas limitações documentadas, sem promessa de ausência absoluta de alucinação.

## Validação

46 testes Python, Node e mypy passam. Limites: corpo HTTP de 16 KB; mensagem de 2.000 caracteres; até 100 conversas por processo, TTL 15 min; histórico de até 12 mensagens/8.000 caracteres; contexto dinâmico serializado UTF-8 de 24 KB; até quatro rodadas com três chamadas de ferramenta; saída de até 2.048 tokens por geração; quatro atendimentos simultâneos; 20 consultas de chat/min/IP e cinco verificações de pedido/min/IP. Payloads grandes recebem 413 e limites de taxa recebem 429/Retry-After. Há no máximo uma repetição em falha de rede ou HTTP 502/503/504, sem repetir 429 ou erro permanente. Logs incluem apenas tipo/status, não chave, corpo do provedor ou credenciais. O orçamento de entrada em bytes é conservador e não substitui contagem exata do tokenizer do modelo. Uso público distribuído exigirá armazenamento compartilhado e limites adicionais; não há garantia absoluta contra alucinação/injeção.
