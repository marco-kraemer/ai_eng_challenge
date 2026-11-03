# 10 — Responder endereço com cache por intenção

**O que construir:**
Responder endereço com cache por intenção, integrado ao grafo antes da classificação, mantendo contrato de resposta e fontes da interface.

**Bloqueado por:**
- Nenhum

**Status:** done

## Critérios de Aceitação
- [x] Variações explícitas de endereço recebem resposta e fonte via API sem chamar modelo ou embeddings.
- [x] Cache limitado em memória é invalidado pelo hash do PDF e não serve dados antigos quando a leitura falha.
- [x] Pedidos mistos, instruções suspeitas, dados pessoais e continuações ambíguas seguem pelo fluxo atual.
