# 02 — Conduzir a escolha e comparar instrumentos

**O que construir:**
Ampliar o chat para acolher a intenção de compra, descobrir preferências e comparar instrumentos com base nas ferramentas existentes. Manter contexto recente e estado estruturado mínimo em sessão temporária, começando sem sumarização automática.

Experiência, orçamento, estilo e uso orientam perguntas, uma por vez, sem roteiro obrigatório de cinco perguntas. Conhecimento musical geral pode orientar a conversa, mas especificações devem existir em `description` e `specs` de `data/products.csv`.

**Bloqueado por:**
- 01 — Consultar produtos pelo chat

**Status:** complete

**Referência:** `docs/decisoes-do-projeto-agente-artefact.md`

## Critérios de Aceitação
- [x] Um fluxo de várias mensagens preserva orçamento e preferências e usa essas informações na busca seguinte.
- [x] O agente faz uma pergunta por vez e recomenda com o que já sabe quando o cliente pede opções sem continuar a entrevista.
- [x] Comparações usam somente características presentes no catálogo e deixam clara a ausência de informação.
- [x] Uma alternativa acima do orçamento informa preço e diferença calculada em Python, preservando opções dentro do limite quando existirem.
- [x] Testes automatizados verificam estado da conversa, interrupção das perguntas, respeito ao orçamento e correspondência das características citadas com os dados.
- [x] Fatos atuais de preço e estoque continuam dependendo de nova consulta à ferramenta.

## Validação

33 testes Python, mypy e teste Node passam. Testes de sessão verificam isolamento, TTL, limites de histórico e reinício; comparação consulta CSV atual e calcula diferença monetária em Python. Playwright em navegador real verificou entrada por teclado, ações contextuais, identificação de conversa, fontes expansíveis, rascunho/cópia, mobile sem overflow horizontal, reinício, repetição após erro e movimento reduzido. O teste Node cobre descarte de resposta atrasada após novo assunto. Backend simulado nas verificações visuais, sem consumo de cota. Respostas livres e decisões do modelo continuam sujeitas a erro e revisão.
