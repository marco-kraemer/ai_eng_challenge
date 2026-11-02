# 08 — Entregar demonstração reproduzível e documentação

**O que construir:**
Consolidar uma entrega avaliável: README com instalação, variáveis, comandos, decisões técnicas, limitações e uso de assistentes de código; 3–5 exemplos reais de interação; avaliação integrada comparando fatos com fontes, ferramentas utilizadas e campos omitidos.

Validar uma hospedagem gratuita compatível com backend, modelo, memória, suspensão e armazenamento/reconstrução do índice. Publicar a demo se viável dentro das contas e autorizações disponíveis, mantendo execução local reproduzível como alternativa. Documentar inviabilidade ou dependências externas de publicação sem fingir que há link público.

Preparar o repositório para entrega pública, verificar exposição de segredos e dados e registrar o estado efetivo da publicação. Preservar histórico incremental de commits, sem force-push que substitua o progresso por um único commit.

**Bloqueado por:**
- 07 — Manter o chat seguro e limitado sob falhas e abuso

**Status:** ready-for-agent

**Referência:** `docs/decisoes-do-projeto-agente-artefact.md`

## Critérios de Aceitação
- [ ] Em ambiente limpo, as instruções do README permitem instalar, configurar, preparar o índice, executar a aplicação e rodar os testes.
- [ ] A avaliação integrada cobre violões por preço/estoque, devolução com e sem modalidade, pedido com e-mail correto/incorreto, informação não encontrada, desconto sem autorização e recomendação com alternativa acima do orçamento.
- [ ] Erros de ferramenta, entradas inválidas, limites e resultados vazios fazem parte da avaliação; fatos são confrontados com as fontes e dados pessoais omitidos são verificados.
- [ ] Existem 3–5 exemplos reais em .md, .txt ou imagem, com pelo menos um caso não trivial de consulta ou aplicação de política, sem divulgar dados pessoais desnecessários.
- [ ] Escolha ou inviabilidade de hospedagem gratuita é justificada com limites de memória, suspensão, índice, chave e cotas; a documentação não presume provedor previamente decidido.
- [ ] Se publicada, a demo é verificada pelo link público e mantém segredos no servidor; se inviável ou dependente de autorização externa, a situação e a alternativa local ficam explícitas.
- [ ] O README documenta verificação fraca de pedidos, divergências do manual, limites do modelo, cotas e ausência de fallback pago.
- [ ] A entrega registra o endereço do repositório público quando disponível, ou a pendência concreta de publicação, e preserva commits incrementais reais.
