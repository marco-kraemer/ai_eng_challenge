# Deploy na Vercel

**Demo:** https://emporiomusica.vercel.app · **Repositório:** https://github.com/marco-kraemer/ai_eng_challenge

GitHub `main` está conectado ao projeto existente `emporio_musica`. Um push cria deployment de produção automaticamente. A interface e as APIs FastAPI usam a mesma origem. O deploy de código `185dfcc` ficou Ready em 2026-11-03, com função de 145,89 MB. [Verificação HTTPS de produção](verificacao-producao.json).

## Configuração

Importar o repositório com Root Directory na raiz, preset **FastAPI**, Python 3.12 e Build Command definido em `vercel.json`: `python scripts/prepare_vercel.py`. O entrypoint é `app/index.py`. Fluid Compute e 2 GB de memória são a configuração usada; duração máxima de função de 300 segundos.

Em **Settings → Environment Variables**, configurar para Production e Preview:

| Variável | Conteúdo |
|---|---|
| `LLM_PROVIDER` | `openai` |
| `OPEN_AI_KEY` | Chave secreta OpenAI; `OPENAI_API_KEY` também aceita |
| `OPENAI_MODEL` | `gpt-4.1-mini` |
| `UPSTASH_REDIS_REST_URL` | Endpoint REST HTTPS do banco Upstash |
| `UPSTASH_REDIS_REST_TOKEN` | Token REST com leitura **e escrita**, como segredo |
| `VERCEL_SUPPORT_LARGE_FUNCTIONS` | `1`, para o empacotamento usado por este backend ONNX/NumPy |
| `LANGSMITH_API_KEY` | Opcional; chave secreta de observabilidade |
| `LANGSMITH_PROJECT` | `emporio-musica` |
| `EMPORIO_TRACING` | `true` para exportar traces sanitizados; `false` para desabilitar |
| `LANGSMITH_WORKSPACE_ID` | Opcional, quando exigido pela chave |

`VERCEL`, `VERCEL_ENV` e metadados Git são fornecidos pela plataforma. Não enviar `.env`, copiar segredos para o frontend ou usar `NEXT_PUBLIC_*` para essas chaves. Mudança de variável exige **novo deployment** para afetar os processos. Produção e Preview devem usar namespaces separados de estado; `STATE_NAMESPACE` só é necessário para substituir o padrão.

Para obter as duas variáveis Upstash: abra o banco no painel, localize **REST API**, copie a URL e o token REST padrão de leitura/escrita. Não use host/porta do protocolo Redis nem o token somente leitura. Salve no painel da Vercel e faça redeploy. O backend falha com 503 se Redis estiver indisponível; não muda silenciosamente para estado local.

A URL de produção precisa estar acessível sem login Vercel. Preview pode continuar protegido. CI verde é uma verificação separada do deploy: a integração Git dispara o build, não espera automaticamente o workflow `Checks`.

## Build e cache

O build baixa o encoder E5 ONNX quantizado com revisão fixada, gera embeddings dos 26 chunks do PDF e grava `.rag-bundle`. Não chama LLM nem Redis. O download temporário fica fora do projeto e é removido antes do empacotamento. `.vercelignore` e `excludeFiles` excluem segredos, testes, documentação e caches intermediários.

Na primeira consulta RAG de uma instância, o pacote é copiado para `/tmp/emporio-policy-cache`. Não há download do modelo em execução. Índice/encoder são reutilizados nessa instância; não são um cache global entre funções. O hash do PDF invalida vetores antigos. FAQ institucional reconhecida não carrega o encoder.

O erro histórico `LAMBDA_SIZE_EXCEEDED` vinha da inclusão de caches auxiliares gerados dentro do projeto. A preparação foi corrigida; o último build observado tem 145,89 MB. O tamanho depende das dependências e deve ser conferido a cada alteração relevante. `VERCEL_SUPPORT_LARGE_FUNCTIONS` é uma opção do empacotador usada por esta configuração; não é requisito universal de projetos Vercel.

## Estado compartilhado e streaming

Upstash guarda até 100 sessões por namespace, TTL de 15 minutos e histórico de até 12 mensagens/8.000 caracteres. Preferências, IDs e proposta pendente são estruturados; e-mails são removidos do histórico. Reset exclui a sessão, e escrita com lease/proprietário impede ressuscitar estado antigo.

Limites de IP e quatro vagas simultâneas são compartilhados. Leases de 330 segundos excedem a função de 300 segundos. Se alterar a duração da função, revisar essa relação. A aplicação confia nos headers substituídos pela Vercel somente quando `VERCEL=1`; localmente, usar `--no-proxy-headers`.

O frontend usa `POST /api/chat/stream` e SSE; `/api/chat` continua JSON para integração/teste. HTTP 200 inicia o stream, mas falhas posteriores vêm em evento `error`: consumidores precisam ler até `done` ou `error`. Eventos de progresso não contêm raciocínio, prompts ou argumentos. Interrupção remove texto parcial; uma chamada já iniciada pode continuar consumindo tokens até o cancelamento ser observado.

## Conferir uma atualização

1. Fazer commit e push no `main`.
2. Conferir [Checks](https://github.com/marco-kraemer/ai_eng_challenge/actions/workflows/checks.yml) e **Vercel → Deployments → Ready**. Conferir o commit do deployment.
3. Abrir `/api/health`: verifica o processo, não a cota OpenAI nem credenciais Redis.
4. Em janela anônima, buscar categorias, consultar catálogo e endereço. Esses fluxos verificam assets, estado compartilhado e FAQ sem inferência.
5. Com saldo disponível, conversar, mudar categoria, aceitar uma proposta e testar texto progressivo. Reiniciar e confirmar que a seleção anterior não reaparece.
6. Consultar o pedido de demonstração e uma política com fontes. Não publicar chave ou cadastrar dados pessoais reais para testar.

[Verificação de produção registrada](verificacao-producao.json) e [trace/streaming real](avaliacao-streaming.json). Cold starts, rede e limites do provedor podem aumentar o tempo; as medições locais não são SLA da demo.

## Diagnóstico

- **500 antes de abrir a página:** verificar variáveis Redis obrigatórias, logs de inicialização e deployment ativo.
- **503 de estado:** conferir URL/token REST, permissões de escrita, namespace e disponibilidade Upstash.
- **429 de LLM:** conferir saldo/limites na OpenAI; a aplicação não rotaciona chaves nem troca modelo.
- **Sem traces:** conferir `EMPORIO_TRACING=true`, chave/workspace/endpoint, novo deployment e atraso de ingestão. Trace indisponível não deve derrubar a resposta.
- **RAG falha no build:** conferir download público do encoder e logs de `prepare_vercel.py`; não remover o PDF/modelo do pacote para esconder o erro.
- **Texto não progride:** conferir resposta `text/event-stream`, eventos e proxies que façam buffering. JSON estruturado do classificador permanece privado e não gera deltas.

Referências: [FastAPI](https://vercel.com/docs/frameworks/backend/fastapi), [runtime Python](https://vercel.com/docs/functions/runtimes/python), [limites](https://vercel.com/docs/functions/limitations), [Upstash REST](https://upstash.com/docs/redis/features/restapi).

## Regressão de streaming corrigida

O primeiro teste público de SSE encontrou aquisição de lease/capacidade em uma thread e persistência em outra. Os proprietários Redis são locais à thread; a rota JSON funcionava, mas o stream falhava ao salvar e não liberava a capacidade corretamente. A aquisição, execução, persistência e liberação agora ocorrem no mesmo worker. O preflight ainda devolve 409/429 antes dos headers SSE. Um teste com Redis real reproduziu a falha e depois passou em três turnos consecutivos, verificando histórico, capacidade liberada e bloqueio concorrente. A correção foi confirmada também na URL pública.
