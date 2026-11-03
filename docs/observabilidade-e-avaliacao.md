# Observabilidade e avaliação

Verificação de desenvolvimento em 3 de novembro de 2026, com GPT-4.1 mini direto na OpenAI. [Relatório reproduzível](avaliacao-agente.json). Não é um benchmark independente.

## Trace sem conteúdo de cliente

Configure `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT=emporio-musica` e opcionalmente `LANGSMITH_WORKSPACE_ID`/`LANGSMITH_ENDPOINT` (US ou EU). Sem chave ou com `EMPORIO_TRACING=false`, não há exportação. Não é necessário habilitar tracing automático do LangChain.

`app/telemetry.py` mantém contexto isolado por requisição e exporta explicitamente apenas registros sanitizados. A raiz `customer_turn` contém nós do grafo; spans `llm`, `tool` e `retriever` registram as etapas reais. `trace_id` retorna na resposta HTTP; `thread_id` é um hash do token da sessão, sem o token original. Conversas guiadas e pedidos também têm trace, sem seus argumentos privados.

Não exportamos prompts, texto de cliente, respostas geradas, argumentos livres, credenciais, cadastros, histórico ou e-mail. Inputs/outputs são vazios; metadados usam allowlist. Erros incluem só o tipo da exceção. Isso reduz exposição e limita o diagnóstico remoto: para reproduzir erro de linguagem, use casos sintéticos locais com consentimento, não logs indiscriminados. Exportação é limitada por timeout e não determina o sucesso da compra/consulta.

Trace real verificado no projeto `emporio-musica`: `9491c4c5-716b-43d7-aecf-40d4b534c4fc`, oito spans, três chamadas ao modelo; inputs/outputs remotos vazios e usage presente. A consulta pode levar alguns segundos para refletir a ingestão. [Evidência sanitizada](avaliacao-streaming.json). Não é um painel público; requer permissão na conta LangSmith.

## Tokens, cache, custo e tempo

`app/metrics.py` usa `prompt_tokens`, `completion_tokens` e `prompt_tokens_details.cached_tokens`. Entrada inclui cache; para estimar custo, subtraímos os tokens em cache da tarifa normal e aplicamos a tarifa de cache uma única vez.

Preços em 2026-11-03 por milhão de tokens GPT-4.1 mini: US$ 0,40 entrada, US$ 0,10 entrada em cache e US$ 1,60 saída. [Fonte oficial](https://developers.openai.com/api/docs/models/gpt-4.1-mini). É uma estimativa de usage, sem impostos, ajustes ou garantia sobre cobrança final. Modelos não reconhecidos ou usage ausente têm custo desconhecido; consumo observado parcial fica separado. Falha não vira custo zero.

O agregado publica mediana/p95 por nearest rank, sucesso de contratos, falha semântica e erro HTTP de infraestrutura separadamente. Zero chamadas em FAQ/guiado/pedido é contado explicitamente. A latência HTTP local inclui inicialização/exportação da rodada; o span mede sua etapa. O tempo até o primeiro token é registrado apenas quando há delta real do provedor. Não se confunde com a confirmação imediata de recebimento.

Na última rodada: 26 operações, 40 chamadas, US$ 0,0237872 estimados; mediana 1,4975 s, p95 5,59 s; zero erros de infraestrutura e 26 contratos aprovados. A amostra mistura operações com/sem LLM, portanto não estima a latência de uma pergunta arbitrária. Streaming separado: primeiro delta em 2,401 s e fim em 3,677 s; a leitura posterior do LangSmith está fora desse tempo. O ensaio de streaming antecede os últimos ajustes de redação.

## Método e revisão qualitativa

O script `scripts/evaluate_agent.py` usa API HTTP local, CSV/PDF reais, sessões isoladas em memória e OpenAI real. Guarda revisão/fingerprint do código, decisões estruturadas, respostas, IDs, páginas, usage e tempo. O relatório registra a revisão `185dfcc` e o fingerprint dos arquivos Python da aplicação testada. Relatórios não identificam por si só alterações locais fora desses arquivos. No harness isolado, o limite local é elevado para 100 requisições/min para não misturar uma avaliação em lote com o teste de limite; produção mantém 20/min, com contratos separados.

Cada execução precisa de `--live`. Teto padrão US$ 0,50 e 60 chamadas; reserva conservadora por bytes de entrada, saída máxima e retry limitado antes de chamar o provedor. Uso desconhecido consome a reserva. Isso não controla outras execuções ou cobranças da conta. Nunca há fallback de modelo ou rotação de chaves.

Revisão dos casos observados:

| Aspecto | Evidência e limite |
|---|---|
| Contexto/categorias | Seis turnos sucessivos: troca de bateria para violão, catálogo geral, união, teclado, aceite e remoção de filtros. Categorias e tetos conferidos com dados reais |
| Orçamento livre | Formulação nova sem cifra obrigatória retornou violões; recusa encerrou proposta; novo teto substituiu o anterior |
| Grounding comercial | IDs/preços comparados ao CSV. Foi detectado conflito 88/61 teclas; agora há aviso no card e a resposta menciona a divergência. Isso não verifica automaticamente todas as afirmações textuais |
| Políticas | Modalidade preservada na devolução online; fontes na página 4. Parcelamento explicita dois trechos conflitantes após correção; a redação ainda pode oferecer “confirmar” de modo ambíguo, sem executar contato |
| Persona | Identidade declara Tom e IA; respostas curtas, sem experiência pessoal ou slogans nos casos revisados. Há repetição de preços e perguntas; estilo ainda pode melhorar |
| Segurança | Programação e pedido de segredo recusados; política inexistente sem fonte; sessão independente sem recuperar seleção alheia; reset gera outra sessão. Não é prova exaustiva contra ataques |
| Pedido | Formulário consulta registro de demonstração sem LLM. Credenciais não aparecem nos traces; essa verificação não equivale a autenticação |

Falhas corrigidas durante a rodada: aceite que reutilizava o teto antigo passou a usar uma operação semântica explícita; resposta de parcelamento deixou de fundir condições conflitantes; recuperação sem estoque evita reescrita de preço pela LLM; divergência de teclas ganhou aviso verificável. As revisões foram reexecutadas. O relatório mantém respostas literais, incluindo imperfeições, para permitir revisão independente.

Os testes não são um catálogo de frases aceitas. A aplicação não mapeia essas expressões em Python; elas são entradas de avaliação de um plano interpretado pela LLM. Antes de uso comercial: ampliar casos inéditos, revisão humana cega de grounding/persona, autenticação e limpeza das fontes inconsistentes.

## Streaming

`POST /api/chat/stream` compartilha sessão, execução, limite e lease com `POST /api/chat`. Eventos: `accepted`, `progress`, `delta`, `answer_reset`, `done` ou `error`. Progresso corresponde a nós/ferramentas reais, sem chain of thought. As duas etapas de JSON estruturado não transmitem tokens ao cliente; argumentos de ferramentas são acumulados no servidor.

A interface trata fragmentação UTF-8/CRLF, controla requisição em andamento e descarta respostas antigas após reset. Texto parcial é provisório; cards/fontes/contexto só chegam em `done`. Erro remove o parcial e não persiste resposta incompleta. Cancelamento interrompe a leitura nos próximos eventos; uma chamada já em andamento pode gerar custo antes de ser interrompida. FAQ pode ir diretamente ao resultado, sem deltas artificiais.
