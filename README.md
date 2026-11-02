# Empório da Música

Protótipo em desenvolvimento: chat FastAPI com catálogo CSV e OpenRouter. O fluxo real de consulta ao catálogo foi validado com duas chamadas de ferramentas; os demais critérios e tickets continuam em avaliação.

## Executar localmente

Requer Python 3.12 ou superior. Na raiz do repositório:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# Crie .env na raiz com:
# OPENROUTER_API_KEY=sua-chave
# OPENROUTER_MODEL=openrouter/free
.venv/bin/uvicorn app.web:app --host 127.0.0.1 --port 8000
```

Abra http://127.0.0.1:8000. Sem configuração, a página funciona e o endpoint responde indisponibilidade. Não há resposta simulada apresentada como resposta de modelo real.

## Modelo e custo

O backend carrega `.env` automaticamente e usa OpenRouter. Aceita somente `openrouter/free` ou identificadores terminados em `:free`, sem fallback pago. A chave fica exclusivamente no servidor e `.env` é ignorado pelo Git.

O [roteador gratuito](https://openrouter.ai/docs/guides/routing/routers/free-router) seleciona modelos compatíveis com ferramentas; o modelo pode variar a cada chamada. Cotas e disponibilidade dependem da conta e do provedor. Para avaliação reproduzível, fixe um modelo gratuito que suporte ferramentas.

Validação real: a pergunta sobre violões ativos em estoque até R$ 600 executou duas chamadas de ferramentas e retornou Yamaha C40 (R$ 599,90), Tagima Memphis AC-39 (R$ 429,90) e Rozini RC-104 (R$ 459,90), presentes no CSV. Modelo reportado na resposta final: `nvidia/nemotron-3.5-super-vl:free`. Isso valida esse cenário, sem garantir todos os casos ou disponibilidade futura.

O adaptador preserva identificadores das chamadas e devolve resultados pela [API de ferramentas](https://openrouter.ai/docs/guides/features/tool-calling). Erros e cotas esgotadas recebem resposta de indisponibilidade. O adaptador Gemini permanece no código como alternativa, mas o endpoint usa OpenRouter.

## Verificação

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/mypy app --check-untyped-defs
```

Testes usam provedor roteirizado e TestClient, sem chamadas externas nem custos. Cobrem filtros de orçamento/estoque, entradas inválidas, consulta vazia/erro, ciclo de ferramenta e indisponibilidade sem credencial. Não comprovam qualidade geral do modelo nem toda a experiência no navegador; a validação real descrita acima foi executada separadamente.

## Decisões e limites atuais

- FastAPI serve HTML/CSS/JavaScript sem frontend separado. Conteúdo de mensagens é inserido com `textContent`.
- O modelo solicita ferramentas; Python executa somente catálogo e listagem de categorias registrados. CSV é relido a cada consulta; preços usam Decimal.
- Resultados têm no máximo dez produtos por chamada; o loop tem até quatro rodadas e três chamadas por rodada.
- Chave apenas no servidor; erros externos não são enviados ao cliente com detalhes sensíveis.
- O chat ainda não mantém contexto entre mensagens. Políticas, pedidos, promoções, limites públicos e hospedagem serão implementados nos tickets seguintes.
- O prompt orienta fundamentação, mas a resposta livre do modelo ainda não tem garantia determinística contra invenção.
- Sem histórico persistente e sem ferramentas de escrita, carrinho, reserva ou pagamento.

## Uso de assistentes

Codex foi usado para decompor decisões em tickets e implementar testes, catálogo, integração inicial e interface. O progresso e os bloqueios ficam em `.scratch/issues/`; decisões de produto estão em `docs/decisoes-do-projeto-agente-artefact.md`.
