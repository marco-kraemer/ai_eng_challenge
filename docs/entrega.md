# Conferência da entrega

Projeto do desafio técnico AI Engineer Artefact. A publicação prepara a avaliação; não envia candidatura ou e-mail automaticamente.

- Demo: https://emporiomusica.vercel.app
- Código público: https://github.com/marco-kraemer/ai_eng_challenge
- [Arquitetura, instalação e uso de IA](../README.md)
- [Cinco interações reais](exemplos-de-interacao.md)
- [Avaliação, métricas e limites](observabilidade-e-avaliacao.md)
- [Produção](verificacao-producao.json)
- [CI](https://github.com/marco-kraemer/ai_eng_challenge/actions/workflows/checks.yml)

## O que foi verificado

Em 2026-11-03, o repositório foi tornado público após autorização e revisão dos arquivos históricos. A inspeção de 309 blobs não encontrou chaves nos padrões verificados nem os segredos presentes no `.env`; o arquivo não está versionado. Isso é uma inspeção pontual, não garantia universal sobre qualquer dado sensível futuro.

A loja e os dados são de demonstração do desafio. O formulário de pedido retorna campos mínimos e mantém as credenciais fora da LLM. O README explicita a verificação fraca, as divergências do manual/catálogo e as limitações do protótipo. Não usar cadastros pessoais reais nesta demonstração.

`Checks` passou no GitHub para `185dfcc`, incluindo Python/Redis real, mypy, Node e Chromium. [Execução](https://github.com/marco-kraemer/ai_eng_challenge/actions/runs/41691393208). A revisão final também deve passar pelo workflow; o badge do README aponta seu estado atual.

Localmente: 156 testes Python passaram com Redis real, mypy sem erro em 31 arquivos, testes Node e navegadores de categoria, streaming e fluxo com RAG real. Inferência simulada nesses testes não é apresentada como avaliação do modelo.

A avaliação live usa GPT-4.1 mini e dados reais do desafio; o JSON registra versão/fingerprint, usage, custo estimado e respostas literais. A revisão qualitativa e as imperfeições estão documentadas. Não há promessa de ausência de alucinação ou resistência completa a ataques.

A URL pública foi aberta em navegador sem autenticação: categorias múltiplas, catálogo real, mobile, reset e FAQ via SSE. O teste HTTPS com OpenAI e Upstash verifica aceitação de orçamento e troca de escopo. O build da função observado tem 145,89 MB. Os assets do RAG são pré-calculados no build, sem download em execução.

## Antes de compartilhar com o avaliador

Conferir saldo da API OpenAI e disponibilidade da Vercel/Upstash. A quota/saldo são externos e podem mudar. A rota health não os comprova. Para continuar testando, o workflow pago é manual e precisa do secret `OPEN_AI_KEY` no GitHub; o CI comum não usa esse segredo.

Abrir a demo em janela anônima e seguir o roteiro de três minutos do README. Ler os exemplos e as limitações, confirmar o commit público e o último deployment Ready. Preparar a mensagem de apresentação pessoal e respeitar o prazo informado pelo recrutador; não foi registrada uma submissão automática nesta execução.

## Próximos passos de produto

1. Corrigir fontes comerciais conflitantes com o responsável pela loja e substituir verificação de pedido por autenticação/OTP.
2. Ampliar avaliação independente, com revisão humana cega de grounding/persona, casos inéditos e comportamento sob carga.
3. Melhorar concisão e reduzir ofertas de ajuda ambíguas na redação; a aplicação não realiza transferências ou contato externo.
4. Medir cold start/latência/custo em tráfego representativo; revisar número de chamadas de planejamento sem perder correção contextual.
5. Definir políticas de retenção, operação de incidentes e orçamento global antes de uso comercial.

Esses pontos são limites e evolução posterior; a demo entregue não se apresenta como operação comercial pronta.
