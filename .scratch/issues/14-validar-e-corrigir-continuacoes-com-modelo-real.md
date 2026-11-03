# 14 — Validar e corrigir interpretação de continuações com o modelo real

**O que construir:**
Concluir a correção de interpretação contextual de orçamento e propostas. A LLM deve compreender respostas livres com o histórico e escolher ferramentas e filtros; não adicionar listas de frases ou mapeamento de sinônimos em Python para decidir intenções.

**Status:** done

**Bloqueado por:**
- 17 — Validação ampla do agente, reaproveitando as evidências de contexto já obtidas.

## Evidência e estado atual
- Atalhos por frases para orçamento e confirmação foram removidos.
- `pending_budget` e preferências são enviados ao classificador e ao agente.
- Antes do último ajuste do classificador, “tanto faz” acionou ferramentas reais e retornou violões. Outras três continuações terminaram em recusa; é necessário registrar a saída do classificador para distinguir erro de interpretação de formato inválido ou resposta vazia.
- O critério de escopo foi ajustado para considerar continuações, mas a avaliação subsequente recebeu HTTP 429 em todos os casos. Essa alteração ainda não foi revalidada ao vivo.
- `scripts/evaluate_budget_language.py --live` executa os casos com o provedor configurado. Os testes unitários não comprovam a qualidade da interpretação.

## Critérios de aceitação
- [x] Com modelo real, responder livremente à pergunta de orçamento resulta em produtos do instrumento já informado, sem orçamento obrigatório.
- [x] Confirmar, recusar e substituir uma proposta atualiza os filtros e o estado corretamente, sem listas de expressões na aplicação.
- [x] Incluir formulações novas que não foram copiadas para as instruções do modelo.
- [x] Se houver falha, registrar classificação, ferramentas e filtros, corrigir a causa e repetir os casos afetados.
- [x] Manter recusa de assuntos alheios, isolamento de sessão e reinício da conversa.
- [x] Avaliar ao vivo também a voz de Tom: naturalidade, transparência sobre IA, concisão e ausência de afirmações pessoais ou de produto sem fonte.
- [x] Registrar resultados e limitações antes de encerrar o ticket; não trocar modelo, rotacionar chaves ou publicar resultados não observados.

## Validação parcial com OpenAI direta — 2026-11-03
- Provedor padrão migrado para GPT-4.1 mini, com chave e créditos autorizados pelo usuário.
- Primeira rodada real: 2/4. Classificação correta nos quatro; duas buscas sem preço usaram tipo de instrumento em `query`, que pesquisa nome de produto.
- Orientação das ferramentas corrigida: descobrir IDs com `list_categories` e filtrar tipo de instrumento por `category_id`, sem dicionários de frases em Python.
- Revalidação real: 4/4, entre 3,07 e 4,95 segundos. Relatório: `docs/avaliacao-openai-orcamento.json`.
- Validação parcial, com histórico pré-carregado: não encerra critérios de novas formulações, isolamento/reset, voz e grounding de todas as afirmações.

## Escopo de categorias — 2026-11-03
- Catálogo e UI agora aceitam uma categoria, união de categorias ou todas.
- Classificação com plano JSON estruturado da consulta, taxonomia atual e separação entre mensagem atual e histórico. Backend executa um plano por turno antes da redação e preserva o escopo nos cards/resumo/proposta.
- Duas conversas reais de seis turnos passaram (relato original e paráfrases), mais quatro continuações de orçamento: 16/16 nos critérios registrados em `docs/avaliacao-categorias-contexto.json`.
- Essa validação não encerra os critérios amplos de persona, grounding e adversariais do ticket.

- Uma checagem em produção reproduziu herança indevida de categoria mesmo após a rodada local. A resolução foi separada em leitura contextual de filtros e extração do escopo da mensagem atual, com citação literal para ampliar ao catálogo geral. A taxonomia é referência do sistema, não menção do cliente. Após o ajuste final, foram repetidas as duas conversas e as quatro continuações de orçamento: 16/16 nos critérios registrados. Temperatura zero reduz variação; as limitações de LLM continuam explícitas.

## Encerramento — 2026-11-03
- Avaliação live ampliada: 26/26 contratos, 40 chamadas, US$ 0,0237872 estimados; `docs/avaliacao-agente.json`.
- Revisão qualitativa e imperfeições: `docs/observabilidade-e-avaliacao.md`. Não é garantia de ausência de alucinação.
- CI remoto aprovado em `185dfcc`, incluindo a regressão adicional de streaming com Redis real.
