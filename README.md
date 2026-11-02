# Empório da Música

Assistente híbrido para apoiar atendimentos e a escolha de instrumentos. Consulta produtos, promoções, políticas e canais da loja; verifica pedidos em um fluxo separado do modelo; prepara rascunhos de resposta para o cliente.

A Empório da Música é fictícia. Esta entrega usa os arquivos fornecidos no desafio Artefact e mantém as divergências do manual explícitas.

[Repositório](https://github.com/marco-kraemer/ai_eng_challenge) · [Exemplos reais](docs/exemplos-de-interacao.md) · [Busca no manual](docs/busca-politicas.md) · [Entrega e hospedagem](docs/entrega.md)

## Executar

Python 3.12, acesso à internet para instalação e, no primeiro uso de políticas, download do modelo de embeddings. Na raiz:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp -n .env.example .env
```

Preencha `.env` localmente:

```dotenv
OPENROUTER_API_KEY=sua-chave
OPENROUTER_MODEL=openrouter/free
```

```bash
.venv/bin/uvicorn app.web:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers
```

Abra **http://localhost:8000**. A chave fica no servidor; `.env` é ignorado pelo Git e pelo Docker. Sem chave/cota, a página e a consulta protegida de pedidos continuam disponíveis, mas a geração de respostas informa indisponibilidade ou limite.

Para preparar o índice antes de abrir o chat e reproduzir a avaliação de recuperação, sem chamar OpenRouter:

```bash
.venv/bin/python scripts/evaluate_policies.py --output docs/avaliacao-busca-politicas.json
```

O modelo local usa aproximadamente 130 MB de disco e o processo de avaliação teve pico de cerca de 672 MB de RAM. Os vetores são reconstruídos quando o PDF muda. `POLICY_CACHE_DIR` permite escolher o diretório gravável do cache.

## Usar

- A tela inicial oferece instrumentos, políticas, situações de atendimento e informações da loja.
- Próximos passos mudam conforme a consulta: comparar opções, buscar mais baratos, esclarecer regras, ver contatos e preparar resposta ao cliente.
- Rascunhos têm bloco próprio, fontes e cópia explícita; a aplicação não envia mensagens ao cliente.
- “Consultar pedido” pede número e e-mail em formulário separado. Só retorna status, previsão e rastreio; credenciais não vão ao modelo por esse formulário. E-mail digitado no chat também é interceptado antes do provedor.
- “Outro assunto” apaga a conversa, rascunhos e pendências e cancela a apresentação de respostas antigas. Reabrir/recarregar a página começa outra sessão. Não usamos banco ou armazenamento persistente de conversas.

## Verificar

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/mypy app --check-untyped-defs
node tests/test_frontend.js
```

Os testes Python usam provedor simulado e dados sintéticos para pedidos, sem custo de modelo nem download dos embeddings. O teste Node requer Node 22 e usa um DOM mínimo para contexto de devolução, fontes e reinício com resposta atrasada.

A verificação adicional em Chromium usa API simulada e cobre teclado, ações, rascunho/cópia e fallback, fontes, mobile, reinício, recuperação de erro e formulário de pedido:

```bash
.venv/bin/pip install playwright
.venv/bin/python -m playwright install --with-deps chromium
# Com o servidor local rodando:
PYTHONPATH=. .venv/bin/python tests/browser_smoke.py
```

Playwright é opcional para desenvolvimento, fora das dependências da aplicação. Capturas dessa verificação ficam em `/tmp/emporio-*.png`. São verificações com dados simulados de API; os exemplos de chamadas reais estão documentados separadamente.

## Arquitetura e decisões

FastAPI serve HTML/CSS/JavaScript, sem frontend separado. `StoreAssistant` classifica escopo e identidade; `Chat` executa um registro de ferramentas somente leitura. Argumentos, filtros, cálculos e campos retornados são controlados no Python.

| Informação | Fonte e consulta |
|---|---|
| Produto, categoria, preço de tabela, estoque | CSV, filtros estruturados e comparação por ID |
| Promoção vigente e preço promocional | CSV de promoções ativas, Decimal, sem acumular PIX |
| Política, horário, endereço | PDF: BM25 + embeddings E5 multilíngues locais, RRF e páginas |
| Canal para concluir compra | Contatos extraídos literalmente do PDF, com divergências |
| Pedido individual | Cruzamento de pedido + e-mail no backend, sem enviar cadastro ao modelo |

A busca híbrida recuperou todas as seções esperadas em **20/22** casos de desenvolvimento, contra 18/22 na lexical e 16/22 na semântica isolada. [Resultados e falhas conhecidos](docs/avaliacao-busca-politicas.json). Essa métrica não comprova a correção de todas as respostas finais.

O OpenRouter usa apenas `openrouter/free` ou identificadores `:free`; não há fallback pago. O roteador pode escolher modelos diferentes, e a cota varia com a conta e os provedores. [Documentação](https://openrouter.ai/docs/guides/routing/routers/free-router). Fixar um modelo gratuito compatível com ferramentas torna avaliações mais reproduzíveis. O adaptador Gemini permanece como alternativa técnica, mas o endpoint usa OpenRouter.

## Limites e privacidade

- Até 100 conversas em memória por processo; expiram após 15 minutos de inatividade. Tokens de conversa ficam apenas na página, sem cookies/localStorage. Histórico: até 12 mensagens e 8.000 caracteres, com e-mails removidos; estado mínimo guarda filtros, IDs e opções disponíveis. Sem sumarização automática.
- Requisição: até 16 KB; mensagem: 2.000 caracteres. Contexto dinâmico serializado: até 24 KB UTF-8, um limite conservador em bytes, não a contagem exata do tokenizer do modelo. Saída configurada em até 2.048 tokens por geração.
- Até quatro rodadas e três ferramentas por rodada, quatro atendimentos simultâneos, 20 requisições de chat/min/IP e cinco verificações de pedido/min/IP. Limites são locais a um processo; usar um worker. Não confiar em cabeçalhos de proxy sem configurar um proxy confiável.
- No máximo uma repetição em timeout/conexão ou HTTP 502/503/504. HTTP 429 não é repetido automaticamente e recebe indicação de limite; não aciona serviço pago. A quota do modelo pode ficar indisponível mesmo com a aplicação saudável.
- Número + e-mail é **verificação fraca**, sem autenticação forte. Produção exige autenticação/OTP, proteção distribuída contra tentativas e revisão de privacidade. Status/previsão/rastreio são registros da base, sem rastreamento ao vivo.
- O manual diverge em contatos e mínimos de parcelamento; o agente deve expor a incerteza e pedir confirmação à equipe. Conteúdo recuperado permanece como dado de ferramenta, sem conceder permissões.
- Identidade e recusa são controladas pela aplicação, mas a classificação de escopo e a redação dependem do modelo e podem errar. Rascunhos exigem revisão humana. Não garantimos ausência absoluta de alucinação ou prompt injection.
- Não há carrinho, reserva, cupom, pedido novo, pagamento, transferência ou envio automático de mensagens. Logs não registram credenciais, cadastro ou corpo do provedor.

## Docker e publicação

Com Docker e Buildx:

```bash
docker buildx build --load -t emporio-demo:local .
docker run --rm --env-file .env -p 127.0.0.1:8000:8000 emporio-demo:local
```

A imagem foi construída e testada com limite de 1 GB, incluindo busca híbrida real e verificação de pedido; o pico do teste foi de aproximadamente 531 MB com cache montado. A imagem não inclui `.env`, `.git`, caches ou artefatos pessoais. A execução local é a alternativa de entrega; **não há link público da aplicação publicado**. O remoto GitHub está configurado; acesso público ainda precisa ser confirmado (a consulta anônima retornou 404). A memória medida elimina a suposição de que um serviço de 512 MB seja suficiente. A análise de opções, requisitos de conta e pendências está em [Entrega e hospedagem](docs/entrega.md).

## Uso de assistentes de código

Codex ajudou na decomposição em tickets, implementação em ciclos de teste que falha/implementação/refatoração, validações e documentação. Os testes e limitações estão registrados no repositório; o histórico de commits preserva as fatias entregues. Decisões de produto: [documento original](docs/decisoes-do-projeto-agente-artefact.md). Backlog: `.scratch/issues/`.
