# Empório da Música

Chatbot para clientes da Empório da Música. Ajuda a escolher instrumentos, tirar dúvidas sobre a compra, acompanhar pedidos e encontrar informações da loja.

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

Abra **http://localhost:8000**. A chave fica no servidor; `.env` é ignorado pelo Git e pelo Docker. Sem chave/cota, a seleção de instrumento e orçamento, a busca estruturada no catálogo e a consulta protegida de pedidos continuam disponíveis. Somente a conversa gerada pelo modelo informa indisponibilidade ou limite.

Para preparar o índice antes de abrir o chat e reproduzir a avaliação de recuperação, sem chamar OpenRouter:

```bash
.venv/bin/python scripts/evaluate_policies.py --output docs/avaliacao-busca-politicas.json
```

O modelo local usa aproximadamente 130 MB de disco e o processo de avaliação teve pico de cerca de 672 MB de RAM. Os vetores são reconstruídos quando o PDF muda. `POLICY_CACHE_DIR` permite escolher o diretório gravável do cache.

## Usar

- **Encontrar um instrumento:** abre nove categorias com ilustrações. Escolha o instrumento e depois um orçamento, com valores sugeridos, campo livre ou “Ainda não defini um valor”. A busca consulta diretamente o catálogo, sem chamada ao modelo e sem instrumento/preço predefinidos.
- **Acompanhar meu pedido:** abre a verificação de número e e-mail da compra. Retorna apenas status, previsão e rastreio; as credenciais do formulário não vão ao modelo.
- **Dúvidas sobre minha compra:** oferece assuntos como troca/devolução, defeito, entrega, pagamento e garantia. A pergunta é enviada somente depois de escolher o assunto.
- **Informações da loja:** oferece horários, endereço e contato, sem mandar uma pergunta arbitrária ao abrir o menu.
- **Nova conversa:** limpa mensagens e pendências, cancela a apresentação de respostas antigas e retorna às opções iniciais. Reabrir a página também inicia outra sessão.

A interface é exclusivamente para o cliente final. Não oferece preparação de mensagens para outro cliente nem orientações de trabalho para atendentes. Ilustrações representam categorias, não fotos de produtos específicos. Detalhes e valores dos cards vêm dos CSVs.

## Verificar

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/mypy app --check-untyped-defs
node tests/test_frontend.js
```

Os testes Python usam provedor simulado e dados sintéticos para pedidos, sem custo de modelo nem download dos embeddings. O teste Node requer Node 22 e usa um DOM mínimo para o seletor, valores em reais, orçamento opcional, IDs de conversa, fontes e reinício com resposta atrasada.

A verificação adicional em Chromium usa API simulada e cobre navegação por teclado, nove ilustrações carregadas, seleção de instrumento e valor, voltar etapas, orçamento opcional, catálogo real sem modelo, fontes, mobile, reinício, recuperação de erro e formulário de pedido:

```bash
.venv/bin/pip install playwright
.venv/bin/python -m playwright install --with-deps chromium
# Com o servidor local rodando:
PYTHONPATH=. .venv/bin/python tests/browser_smoke.py
```

Playwright é opcional para desenvolvimento, fora das dependências da aplicação. Capturas dessa verificação ficam em `/tmp/emporio-customer-*.png`. São verificações com dados simulados de API; os exemplos de chamadas reais estão documentados separadamente.

## Arquitetura e decisões

FastAPI serve HTML e arquivos CSS/JavaScript/SVG locais. Não há frontend separado ou dependência de imagens externas. `StoreAssistant` classifica escopo e identidade; `Chat` executa um registro de ferramentas somente leitura. Argumentos, filtros, cálculos e campos retornados são controlados no Python.

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
- Identidade e recusa são controladas pela aplicação, mas a classificação de escopo e a redação dependem do modelo e podem errar. Não garantimos ausência absoluta de alucinação ou prompt injection.
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
