# 08 — Entregar demonstração reproduzível e documentação

**O que construir:**
Consolidar uma entrega avaliável: README com instalação, variáveis, comandos, decisões técnicas, limitações e uso de assistentes de código; 3–5 exemplos reais de interação; avaliação integrada comparando fatos com fontes, ferramentas utilizadas e campos omitidos.

Validar uma hospedagem gratuita compatível com backend, modelo, memória, suspensão e armazenamento/reconstrução do índice. Publicar a demo se viável dentro das contas e autorizações disponíveis, mantendo execução local reproduzível como alternativa. Documentar inviabilidade ou dependências externas de publicação sem fingir que há link público.

Preparar o repositório para entrega pública, verificar exposição de segredos e dados e registrar o estado efetivo da publicação. Preservar histórico incremental de commits, sem force-push que substitua o progresso por um único commit.

**Bloqueado por:**
- 07 — Manter o chat seguro e limitado sob falhas e abuso

**Status:** complete

**Referência:** `docs/decisoes-do-projeto-agente-artefact.md`

## Critérios de Aceitação
- [x] Em ambiente limpo, as instruções do README permitem instalar, configurar, preparar o índice, executar a aplicação e rodar os testes.
- [x] A avaliação integrada cobre violões por preço/estoque, devolução com e sem modalidade, pedido com e-mail correto/incorreto, informação não encontrada, desconto sem autorização e recomendação com alternativa acima do orçamento.
- [x] Erros de ferramenta, entradas inválidas, limites e resultados vazios fazem parte da avaliação; fatos são confrontados com as fontes e dados pessoais omitidos são verificados.
- [x] Existem 3–5 exemplos reais em .md, .txt ou imagem, com pelo menos um caso não trivial de consulta ou aplicação de política, sem divulgar dados pessoais desnecessários.
- [x] Escolha ou inviabilidade de hospedagem gratuita é justificada com limites de memória, suspensão, índice, chave e cotas; a documentação não presume provedor previamente decidido.
- [x] Se publicada, a demo é verificada pelo link público e mantém segredos no servidor; se inviável ou dependente de autorização externa, a situação e a alternativa local ficam explícitas.
- [x] O README documenta verificação fraca de pedidos, divergências do manual, limites do modelo, cotas e ausência de fallback pago.
- [x] A entrega registra o endereço do repositório público quando disponível, ou a pendência concreta de publicação, e preserva commits incrementais reais.

## Entrega e validação

Entrega local reproduzível concluída: 46 testes Python, mypy, Node e verificação em Chromium; instalação validada em ambiente limpo. Docker construído e executado sob limite de 1 GB, com página, endpoint de pedidos e RAG real; sem chave embutida. Cinco exemplos reais e resultados de avaliação estão em docs/.

Aplicação externa não publicada: memória/custo/conta de hospedagem não validados dentro do requisito de custo zero; alternativa local documentada. Consulta anônima ao GitHub retornou 404, então o acesso público ao repositório precisa ser confirmado pelo proprietário; não alteramos sua visibilidade. Esses estados são as alternativas/pendências explicitamente previstas nos critérios condicionais da entrega. OpenRouter retornou 429 na última validação real; não houve fallback pago.
