# 03 — Responder políticas com fontes do manual

**O que construir:**
Permitir perguntas de políticas pelo chat usando RAG sobre `data/políticas_da_loja.pdf`. Extrair texto, segmentar trechos coerentes e preservar página/seção. Escolher recuperação e eventual índice/embeddings por qualidade em perguntas representativas e recursos disponíveis, sem infraestrutura vetorial paga.

O retorno da ferramenta inclui evidências e suas páginas; a resposta apresenta referências verificáveis. Identificar divergências de contatos e parcelamento no manual e registrar pendências sem inventar resolução. Conteúdo recuperado é referência, não instrução com autoridade sobre o sistema.

**Bloqueado por:**
- 01 — Consultar produtos pelo chat

**Status:** complete

**Referência:** `docs/decisoes-do-projeto-agente-artefact.md`

## Critérios de Aceitação
- [x] Perguntas sobre devolução recuperam os trechos pertinentes com página/seção e recebem resposta apoiada na evidência.
- [x] Quando a modalidade não foi informada, a resposta esclarece possibilidades razoáveis ou pede o dado; quando já foi informada, responde ao caso específico.
- [x] Pergunta sem cobertura ou com dúvida material recebe indicação da limitação e contato oficial sustentado pela fonte, quando disponível.
- [x] Contatos de canais distintos são usados conforme contexto quando isso estiver claro; condições conflitantes de parcelamento não são reconciliadas por invenção.
- [x] Testes automatizados verificam recuperação em casos representativos, referências de origem, falta de evidência e tratamento de conflitos.
- [x] O índice pode ser reconstruído localmente; escolha técnica, qualidade observada e custo/recursos são documentados.
- [x] Resultados recuperados têm tamanho limitado e não permitem substituir instruções do sistema.

## Validação consolidada

RAG híbrido implementado e validado: horário, devolução online, modalidade não informada, informação ausente e conflito de parcelamento. 24 testes Python e mypy passam; teste Node cobre continuação da modalidade e referências na interface. Qualidade e limitações de recuperação registradas em docs/busca-politicas.md. A resposta livre e a classificação continuam probabilísticas.
