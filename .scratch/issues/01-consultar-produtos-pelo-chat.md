# 01 — Consultar produtos pelo chat

**O que construir:**
Entregar um chat web grande e centralizado, servido pelo backend Python (preferência por FastAPI com HTML/CSS/JavaScript), em que uma pergunta sobre produtos aciona tool calling e retorna opções reais do catálogo. Mensagens dos participantes ficam em lados distintos, com rolagem e campo de entrada inferior.

Validar um provedor/modelo com opção gratuita e tool calling antes de escolhê-lo; registrar limites e configuração sem presumir que Gemini já foi escolhido. O backend executa ferramentas somente leitura sobre `data/products.csv` e `data/categories.csv`, com validação de argumentos e precisão monetária (por exemplo, Decimal). O modelo decide chamadas e interpreta resultados, sem executar SQL ou código arbitrário.

Iniciar documentação de execução, configuração e decisões. Usar commits incrementais a partir desta fatia.

**Bloqueado por:**
- Nenhum — pode iniciar imediatamente

**Status:** in-progress

**Referência:** `docs/decisoes-do-projeto-agente-artefact.md`

## Critérios de Aceitação
- [ ] Uma pergunta no navegador consulta produtos por categoria, faixa de preço, status e estoque e retorna registros correspondentes às fontes.
- [x] Testes automatizados cobrem combinações de filtros, limites monetários, argumentos inválidos, resultados vazios e distinção entre encontrado, não encontrado e erro.
- [ ] Preço e disponibilidade são consultados novamente antes de serem apresentados como atuais; histórico não substitui consulta.
- [ ] Resultados são limitados e paginados; pedido de catálogo inteiro provoca pedido de recorte sem enviar toda a base ao modelo.
- [x] O modelo usa apenas ferramentas registradas e validadas pelo Python; nenhuma ferramenta altera dados.
- [x] Tool calling funciona com o modelo escolhido em execução real; configuração gratuita e limitações estão documentadas, com testes determinísticos usando um substituto do provedor.
- [x] A chave permanece no servidor, fora do JavaScript e do versionamento; não há fallback automático pago.
- [x] O README inicial permite instalar, configurar e iniciar o fluxo localmente.

## Progresso e bloqueio

Implementados catálogo, adaptador REST Gemini, loop de ferramentas e chat FastAPI. Cinco testes passam; mypy passa. Não há `GEMINI_API_KEY` configurada. A validação de tool calling real e de cotas gratuitas exige credencial de projeto sem cobrança e modelo elegível. A escolha final permanece aberta. Os critérios de navegador, atualização de fatos e recorte do catálogo precisam de validação integrada com o modelo.

### Validação OpenRouter

Integração real validada com `openrouter/free`: duas chamadas de ferramenta e três produtos até R$ 600 correspondentes ao catálogo. Modelo final reportado: `nvidia/nemotron-3.5-super-vl:free`. O backend carrega `.env` automaticamente. Oito testes passam e mypy passa. O bloqueio de credencial foi removido; demais critérios ainda exigem validação.
