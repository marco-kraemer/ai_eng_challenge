# 14 — Validar e corrigir interpretação de continuações com o modelo real

**O que construir:**
Concluir a correção de interpretação contextual de orçamento e propostas. A LLM deve compreender respostas livres com o histórico e escolher ferramentas e filtros; não adicionar listas de frases ou mapeamento de sinônimos em Python para decidir intenções.

**Status:** pending

**Dependência atual:**
Cota disponível no OpenRouter. O provedor retornou HTTP 429 na revalidação. Não considerar esse erro uma falha semântica nem marcar o ticket concluído apenas porque os testes com inferência simulada passam.

## Evidência e estado atual
- Atalhos por frases para orçamento e confirmação foram removidos.
- `pending_budget` e preferências são enviados ao classificador e ao agente.
- Antes do último ajuste do classificador, “tanto faz” acionou ferramentas reais e retornou violões. Outras três continuações terminaram em recusa; é necessário registrar a saída do classificador para distinguir erro de interpretação de formato inválido ou resposta vazia.
- O critério de escopo foi ajustado para considerar continuações, mas a avaliação subsequente recebeu HTTP 429 em todos os casos. Essa alteração ainda não foi revalidada ao vivo.
- `scripts/evaluate_budget_language.py --live` executa os casos com o provedor configurado. Os testes unitários não comprovam a qualidade da interpretação.

## Critérios de aceitação
- [ ] Com modelo real, responder livremente à pergunta de orçamento resulta em produtos do instrumento já informado, sem orçamento obrigatório.
- [ ] Confirmar, recusar e substituir uma proposta atualiza os filtros e o estado corretamente, sem listas de expressões na aplicação.
- [ ] Incluir formulações novas que não foram copiadas para as instruções do modelo.
- [ ] Se houver falha, registrar classificação, ferramentas e filtros, corrigir a causa e repetir os casos afetados.
- [ ] Manter recusa de assuntos alheios, isolamento de sessão e reinício da conversa.
- [ ] Avaliar ao vivo também a voz de Tom: naturalidade, transparência sobre IA, concisão e ausência de afirmações pessoais ou de produto sem fonte.
- [ ] Registrar resultados e limitações antes de encerrar o ticket; não trocar modelo, rotacionar chaves ou publicar resultados não observados.

## Validação parcial com OpenAI direta — 2026-11-03
- Provedor padrão migrado para GPT-4.1 mini, com chave e créditos autorizados pelo usuário.
- Primeira rodada real: 2/4. Classificação correta nos quatro; duas buscas sem preço usaram tipo de instrumento em `query`, que pesquisa nome de produto.
- Orientação das ferramentas corrigida: descobrir IDs com `list_categories` e filtrar tipo de instrumento por `category_id`, sem dicionários de frases em Python.
- Revalidação real: 4/4, entre 3,07 e 4,95 segundos. Relatório: `docs/avaliacao-openai-orcamento.json`.
- Validação parcial, com histórico pré-carregado: não encerra critérios de novas formulações, isolamento/reset, voz e grounding de todas as afirmações.
