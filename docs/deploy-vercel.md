# Publicar a Empório da Música na Vercel

A aplicação está preparada para o runtime Python/FastAPI da Vercel. A interface e as APIs continuam na mesma origem. Esta preparação não cria um projeto na plataforma nem publica uma URL.

## Configuração incluída

- `app/index.py` exporta a aplicação FastAPI; o uso local continua sendo `app.web:app`.
- `.python-version` fixa Python 3.12.
- `vercel.json` seleciona FastAPI, executa a preparação do RAG e define até 300 segundos por requisição. Dados, assets e modelo local entram no pacote; arquivos de desenvolvimento e `.env` ficam de fora.
- `.vercelignore` evita enviar segredos e caches locais. `.rag-bundle` é gerado novamente no build.
- `requirements.txt` contém dependências de execução; `requirements-dev.txt` acrescenta as de testes e tipagem.

## 1. Criar os serviços e configurar variáveis

Importe o repositório no painel da Vercel, com a raiz do projeto como Root Directory. Selecione o preset **FastAPI** e mantenha o Build Command de `vercel.json`. Com Fluid Compute, configure **2 GB de memória no painel**, sem definir `memory` em `vercel.json`.

Crie ou conecte um banco **Upstash Redis**, pelo Marketplace da Vercel ou pelo painel da Upstash. Configure no projeto, em Production e no ambiente Preview que for usar:

| Variável | Valor |
|---|---|
| `LLM_PROVIDER` | `openai` |
| `OPEN_AI_KEY` | Chave da API OpenAI, como segredo no painel (`OPENAI_API_KEY` também é aceita) |
| `OPENAI_MODEL` | `gpt-4.1-mini` |
| `UPSTASH_REDIS_REST_URL` | Endpoint HTTPS REST da Upstash |
| `UPSTASH_REDIS_REST_TOKEN` | Token REST com leitura e escrita; não usar o token somente de leitura |
| `VERCEL_SUPPORT_LARGE_FUNCTIONS` | `1`; habilitar no ambiente do build (Production e Preview). Necessário para este backend com ONNX/NumPy, em projetos elegíveis |

`VERCEL`, `VERCEL_ENV` e as variáveis Git são fornecidas pela plataforma. Não copie o arquivo `.env` para o deploy. `POLICY_CACHE_DIR` não precisa ser configurado: na Vercel, o padrão é `/tmp/emporio-policy-cache`.

O estado usa um namespace separado para produção e para cada branch de preview. `STATE_NAMESPACE` é uma substituição opcional, com até 80 letras, números, hífens ou sublinhados. Não use o mesmo namespace para ambientes que precisam ficar isolados. Escolha regiões próximas para a função e o Redis.

Credenciais Redis são obrigatórias na Vercel. A aplicação recusa configuração incompleta; não volta silenciosamente para conversas locais, o que perderia contexto entre instâncias. Sem Redis configurado, a execução local continua usando memória como antes.

## 2. O que acontece no build e na execução

O build baixa somente os arquivos necessários do modelo ONNX quantizado, com revisão fixada, gera embeddings dos trechos do PDF e grava `.rag-bundle`. O cache de download fica em um diretório temporário fora do projeto e é removido antes do empacotamento; somente a cópia final do modelo entra na função. Não chama a LLM nem acessa o Redis. O download público do modelo precisa estar disponível durante o build.

Na primeira consulta RAG de uma instância, o pacote é copiado para `/tmp`, que é gravável. O modelo é carregado com arquivos locais, sem download em execução. O índice e o encoder são reutilizados enquanto aquela instância estiver ativa. Instâncias novas repetem a inicialização; o cache em memória não é global. Alterações no PDF invalidam os vetores por hash.

As conversas, propostas de orçamento e filtros ficam no Redis, com TTL de 15 minutos e histórico limitado a 12 mensagens/8.000 caracteres. E-mails continuam removidos do histórico. Reiniciar elimina a conversa; bloqueios com proprietário e prazo impedem uma resposta atrasada de restaurá-la. Há até 100 sessões ativas por namespace; quando esse limite é atingido, novas sessões recebem indisponibilidade até liberar espaço.

Limites de consultas e as quatro vagas simultâneas de geração também são compartilhados. Bloqueios expiram em 330 segundos, acima dos 300 segundos máximos da função; se alterar essa duração, ajuste o prazo dos bloqueios. Falha do Redis retorna 503 antes de continuar sem proteção. As rotas não devem ser usadas como acesso direto a dados do Redis.

O endereço do visitante é obtido dos headers sobrescritos pela Vercel apenas quando `VERCEL=1`. Fora desse ambiente, headers enviados pelo cliente não substituem o endereço da conexão. A chave do limitador é armazenada como hash.

## 3. Verificações antes de enviar o link

1. Conferir o build: assets do RAG presentes e tamanho final da função aceito pela plataforma. O tamanho exato depende das dependências empacotadas; a preparação local não substitui o build da Vercel.
2. Abrir `/api/health`: deve retornar `{"status":"ok"}`. Essa rota verifica o processo, não a disponibilidade do Redis ou da LLM.
3. Abrir a página, buscar um instrumento sem orçamento e consultar endereço/horários. Esses fluxos não precisam da LLM, mas as operações de sessão usam Redis.
4. Continuar uma conversa, reiniciar e confirmar que o contexto anterior não reaparece. Confirmar a operação em produção após novos processos/inicializações.
5. Consultar pedido de demonstração, comparar produtos e abrir uma pergunta que exija o manual.
6. Com cota disponível, executar os testes de linguagem e personalidade do ticket 14. Hospedagem não resolve limites ou saldo da API de inferência.
7. Configurar o acesso da URL de produção para que o avaliador não precise entrar na sua conta Vercel; testar em janela anônima. Pré-visualizações podem ter proteção de acesso.

Ainda não há build remoto, Redis de produção configurado ou URL pública validados. Nenhum serviço pago foi contratado. Confirme os planos e os limites das contas antes de publicar.

## Validação local

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/mypy app --check-untyped-defs
node tests/test_frontend.js
.venv/bin/python scripts/prepare_vercel.py
```

Se já houver o cache do modelo local, use `scripts/prepare_vercel.py --from-cache .cache` para testar o build sem baixar novamente. O cache gerado não deve ser commitado.

Os testes de scripts Lua podem ser executados contra Redis real, com Docker:

```bash
docker run --detach --rm --name emporio-vercel-redis-test redis:7-alpine
REDIS_TEST_CONTAINER=emporio-vercel-redis-test .venv/bin/python -m unittest discover -s tests -p test_redis_state.py -v
docker stop emporio-vercel-redis-test
```

Esses testes usam o transporte REST simulado para encaminhar os comandos a Redis real. Validam os scripts, bloqueios e armazenamento entre instâncias; não comprovam conectividade ou credenciais da Upstash de produção. O teste opcional é ignorado sem `REDIS_TEST_CONTAINER`.

Na preparação, passaram 112 testes Python, incluindo os seis testes com Redis real, além de mypy e testes Node. O RAG foi carregado com rede bloqueada a partir do pacote de 129,2 MiB: inicialização + consulta em 4,7 s e pico de RSS de 513,6 MiB. São medições locais desta verificação, não previsões de latência na Vercel. A geração pela LLM permanece com a pendência já registrada no ticket 14.

Referências: [FastAPI na Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [runtime Python](https://vercel.com/docs/functions/runtimes/python), [limites das funções](https://vercel.com/docs/functions/limitations), [headers da plataforma](https://vercel.com/docs/headers/request-headers), [Upstash REST](https://upstash.com/docs/redis/features/restapi).

## Correção de tamanho do pacote

O primeiro build remoto falhou com `LAMBDA_SIZE_EXCEEDED` (735,31 MiB). A preparação criava `.cache-build` dentro do projeto: `.vercelignore` só impedia seu envio inicial, mas não excluía o diretório recriado pelo build. O empacotador podia incluir blobs/snapshots auxiliares além do modelo final.

O download agora ocorre em um diretório temporário fora do projeto, com limpeza em sucesso e falha. `.cache-build/**` também está excluído da função como proteção contra artefatos antigos. Repetir o build substitui arquivos antigos do modelo, inclusive arquivos somente de leitura.

Mantenha `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` em **Production e Preview** e confirme **Fluid Compute** habilitado. A variável é lida pelo empacotador durante o build; alterar só o ambiente de execução ou repetir um deployment antigo não aplica a correção. O empacotador Python 29.0.0, usado pelo CLI 65.4.0 do log, tenta instalar parte das dependências em execução quando essa opção está desabilitada; o conjunto ONNX/NumPy/modelo não cabe no limite interno dessa otimização. A correção reduz o pacote, mas não substitui essa configuração da plataforma.

Reprodução local com o empacotador oficial `@vercel/python@29.0.0` e a variável habilitada: build concluído, função de 347,9 MiB (364.850.303 bytes), com aproximadamente 218,3 MiB de dependências e 129,2 MiB de assets do RAG. A inspeção dos arquivos da função não encontrou `.cache-build`, `.cache` ou `.env`. A confirmação do próximo build remoto permanece dependente da configuração e execução na conta Vercel. Os quatro testes de regressão do build passaram; a suíte totalizou 116 testes (seis testes opcionais de Redis real ignorados nesta execução).
