# Empório da Música

Protótipo em desenvolvimento: chat FastAPI com catálogo CSV, busca híbrida no manual e OpenRouter. O fluxo real de consulta ao catálogo foi validado com duas chamadas de ferramentas; os demais critérios e tickets continuam em avaliação.

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
- O modelo solicita ferramentas; Python executa as ferramentas registradas de catálogo, categorias e políticas. CSV é relido a cada consulta; preços usam Decimal.
- Resultados têm no máximo dez produtos por chamada; o loop tem até quatro rodadas e três chamadas por rodada.
- Chave apenas no servidor; erros externos não são enviados ao cliente com detalhes sensíveis.
- O chat ainda não mantém contexto entre mensagens. A busca de políticas já está disponível. Pedidos, promoções estruturadas, limites públicos e hospedagem permanecem pendentes.
- O prompt orienta fundamentação, mas a resposta livre do modelo ainda não tem garantia determinística contra invenção.
- Sem histórico persistente e sem ferramentas de escrita, carrinho, reserva ou pagamento.

## Uso de assistentes

Codex foi usado para decompor decisões em tickets e implementar testes, catálogo, integração inicial e interface. O progresso e os bloqueios ficam em `.scratch/issues/`; decisões de produto estão em `docs/decisoes-do-projeto-agente-artefact.md`.

## Identidade visual e escopo do atendimento

A Empório da Música é fictícia no documento de produto. A identidade criada para o protótipo usa verde profundo, tons de papel, dourado e títulos serifados, sem alegar vínculo com uma empresa real. O chat tem sugestões iniciais, estados de carregamento e erro, layout responsivo e cards de produtos. Nome, descrição, preço e estoque dos cards vêm dos resultados estruturados do backend; o modelo não escreve HTML ou define esses dados. Conteúdo recebido é inserido com nós de texto, com suporte seguro a negrito simples.

Antes de responder, `StoreAssistant` faz uma chamada isolada ao modelo para classificar a mensagem: assunto da loja, identidade ou fora de escopo. A chamada não recebe ferramentas e tem instruções próprias. Somente a classificação exata `store` libera o atendente. Identidade e recusa são textos fixos da aplicação. Resposta inválida é recusada; falha de rede/cota gera indisponibilidade e não libera a geração. Mensagens mistas tentando disfarçar programação como assunto da loja também são classificadas como fora de escopo.

Isso adiciona uma requisição por mensagem, aumentando latência e consumo da cota gratuita. O classificador continua sendo um modelo e pode errar; não é uma garantia absoluta contra prompt injection. O prompt do atendente reforça a identidade, o escopo e a fundamentação, enquanto o registro de ferramentas limita operações possíveis. Validação determinística de todos os fatos da resposta livre, limites de taxa e contexto entre turnos continuam pendentes.

Validação real desta mudança: aula de `for` em Python recusada; pergunta sobre nome respondida como assistente da Empório; pedido misto de substituir identidade e ensinar Python com guitarra recusado; busca de violões até R$ 600 retornou os produtos do catálogo. Os testes automatizados verificam que classificações negadas/inválidas não chegam ao atendente, identidade não é gerada livremente e cards vêm do catálogo. Falhas do classificador não liberam o agente.

A camada visual foi implementada junto aos guardrails. O smoke test visual com Playwright não pôde iniciar Chromium neste ambiente por ausência da biblioteca de sistema `libnspr4.so`; desktop/mobile ainda precisam de conferência visual no navegador local. Playwright foi instalado apenas no ambiente de desenvolvimento, sem nova dependência da aplicação.


## Políticas e RAG

Perguntas como “que horas vocês abrem?” agora podem acionar `search_policies`. A busca combina BM25 e embeddings multilíngues locais e retorna trechos com página/seção. A interface mostra referências expansíveis. Não usa serviço vetorial pago nem envia o PDF completo ao modelo.

O primeiro uso baixa cerca de 130 MB de modelo para `.cache/`. O pico medido do processo de avaliação foi de aproximadamente 672 MB de RAM: hospedagem com 512 MB não está validada. O índice é reconstruído automaticamente quando o PDF muda e pode ser preparado antes de abrir o chat:

```bash
.venv/bin/python scripts/evaluate_policies.py --output docs/avaliacao-busca-politicas.json
```

O comando não chama OpenRouter. A bateria de desenvolvimento recuperou as evidências esperadas em 20/22 casos com busca híbrida; inclui falhas conhecidas e falsos positivos. Consulte [implementação, operação, conflitos e limitações](docs/busca-politicas.md) e [resultados completos](docs/avaliacao-busca-politicas.json). A recuperação não garante, sozinha, que toda afirmação da resposta livre esteja correta.
