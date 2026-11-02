# Entrega, validação e hospedagem

## Estado da aplicação

Execução local documentada e remoto configurado em [GitHub](https://github.com/marco-kraemer/ai_eng_challenge). A consulta anônima à API GitHub retornou 404: o acesso público ao repositório ainda precisa ser confirmado pelo proprietário; não alteramos sua visibilidade. Não há URL pública da aplicação em hospedagem externa. Não foi contratado recurso pago.

Funcionalidades: abertura por quatro caminhos de cliente, seletor ilustrado de instrumento e orçamento; consultas estruturadas de catálogo e promoções; comparação com diferença monetária calculada; RAG híbrido no manual; canais oficiais com fontes; contexto efêmero; próximos passos voltados ao comprador; consulta protegida de pedidos fora do modelo; limites e tratamento de erro.

Público confirmado pelo usuário: CLIENTE FINAL. A interpretação anterior de apoio ao atendente foi corrigida. Foram removidos slogans, perguntas em terceira pessoa sobre outro cliente e o recurso de preparar/copiar rascunhos. A escolha de instrumento abre etapas explícitas de categoria e orçamento; não envia uma busca fixa de violão até R$ 600.

## Validações

- Imagem Docker construída e executada com limite de 1 GB: página, API protegida de pedidos, ausência de chave embutida e recuperação híbrida com embeddings reais passam; pico de RSS aproximado de 531 MB no teste com cache montado.
- Instalação das dependências em um segundo ambiente Python 3.12 limpo, sem usar pacotes da `.venv` do projeto.
- 49 testes Python; verificação de tipos com mypy; teste Node de seletor, valores BRL, orçamento opcional, IDs de conversa, fontes e descarte de resposta atrasada.
- Chromium real: desktop 1440×1000, celular 390×844, navegação por teclado, seleção entre nove categorias ilustradas, escolha/edição de preço e ausência de orçamento, catálogo real, ações contextuais, fontes expansíveis, reinício, repetição após erro, movimento reduzido e formulário de pedido sem enviar e-mail ao chat. Apenas as APIs do modelo e de verificação de pedido são simuladas nessa verificação; categorias, ilustrações e busca de catálogo são reais e não consomem cota do modelo.
- Avaliação local de recuperação com embeddings reais: 20/22 casos de desenvolvimento positivos na busca híbrida. Casos perdidos e falsos positivos estão publicados no JSON e na documentação da busca.
- Cinco exemplos reais com OpenRouter documentados separadamente. O teste de continuação da versão anterior recebeu 429 do provedor. Nesta revisão, o catálogo guiado funciona independentemente dessa cota; o recurso de rascunho foi removido. Os testes não são apresentados como prova de disponibilidade contínua da API de modelo.

A contagem de testes não comprova ausência de alucinação. Verificações do provedor e do navegador têm escopos diferentes, descritos acima.

## Memória e custo

A avaliação de recuperação mediu pico de cerca de 672 MB no processo e 130 MB de cache do modelo. Modelo local na CPU, sem API de embeddings paga. Um worker evita duplicação do modelo. Recomenda-se medir o backend completo com pelo menos 1 GB disponível antes de escolher hospedagem.

As chaves permanecem como variáveis secretas no servidor. O OpenRouter só aceita a seleção gratuita nesta aplicação; sem fallback automático pago. O roteador varia o modelo e as cotas, podendo receber 429. Os limites do processo não garantem uma cota diária de terceiros nem substituem autenticação e proteção distribuída.

## Opções avaliadas em 2 de novembro de 2026

**Hugging Face Spaces / Docker:** a documentação informa CPU Basic com 2 vCPU, 16 GB de RAM e 50 GB de disco não persistente, sem custo por hora. Entretanto, a mesma página informa que criar Spaces com computação (Docker/Gradio) exige plano pago, com uma exceção específica ligada ao free tier de ZeroGPU. Não há conta/credencial de hospedagem elegível configurada nesta sessão. Portanto, isso não foi tratado como opção garantidamente sem custo, nem contratado. A memória seria compatível, mas elegibilidade/custo da conta e funcionamento público precisam ser confirmados. [Fonte](https://huggingface.co/docs/hub/spaces-overview).

**Render gratuito:** suporta serviços web Python, mas suspende após 15 minutos sem tráfego, perde alterações do disco local e tem limites de uso. O cache precisa ser reconstruível. Não foi validado um plano gratuito com memória suficiente para a aplicação atual; não se deve presumir que 512 MB bastem. [Fonte](https://render.com/docs/free).

O índice e o modelo podem ser reconstruídos no primeiro uso após perda de cache, com custo de download e inicialização. Não há necessidade de persistir conversas ou pagar por banco. Uma futura hospedagem também deve servir a aplicação e as APIs na mesma origem, respeitar a porta do container e manter as chaves fora do frontend. Publicação embutida em iframe exigirá revisar a política `frame-ancestors`, hoje restrita.

## Pendência de publicação

A alternativa local atende à decisão de entrega quando a demo gratuita não é viável. Publicação externa fica condicionada a uma conta elegível sem custo, recursos de memória adequados e configuração dos segredos. O pacote Docker serve como ponto de partida; ele não representa um deploy já realizado. Não há uma URL de demonstração externa para registrar neste momento.

## Execução e checks

Use os comandos do README para instalar e iniciar. Os comandos do README reproduzem testes Python, mypy e Node sem chave de modelo. A validação visual é opcional e requer Playwright/Chromium. A instalação do navegador é apenas para desenvolvimento.

Os CSVs e o PDF são os fornecidos no desafio. A verificação de pedidos exige número e e-mail, retorna campos mínimos e mantém esses dados fora do modelo pelo formulário. Para produção, isso deve ser substituído por autenticação ou código de uso único, além de revisão dos dados e das regras comerciais conflitantes.

## Ambientes com proxy TLS

O Dockerfile admite um certificado público de confiança como secret temporário de build, sem gravá-lo na imagem:

```bash
docker buildx build --load --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt -t emporio-demo:local .
```

Se o ambiente de execução também exigir essa CA, monte o bundle somente para leitura e configure os clientes Python, mantendo a verificação TLS:

```bash
docker run --rm --env-file .env -p 127.0.0.1:8000:8000 \
  --mount type=bind,src=/etc/ssl/certs/ca-certificates.crt,dst=/run/proxy-ca.pem,readonly \
  -e SSL_CERT_FILE=/run/proxy-ca.pem \
  -e REQUESTS_CA_BUNDLE=/run/proxy-ca.pem emporio-demo:local
```

Esse detalhe é específico de ambientes com proxy que termina TLS; não é necessário copiar certificados de sessão para o repositório. O comando padrão de inicialização e o comando do healthcheck do Docker também foram executados com sucesso, sem chave de modelo na imagem.
