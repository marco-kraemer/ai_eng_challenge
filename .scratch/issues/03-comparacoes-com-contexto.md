# 03 — Continuar e comparar opções com estado explícito

**O que construir:**
Usar estado tipado no grafo com preferências, IDs de produtos e assunto por sessão efêmera, preservando os próximos passos da interface.

**Bloqueado por:**
- 01; 02

**Status:** done

## Critérios de Aceitação
- [x] Após busca visual, comparação usa os IDs anteriores e relê catálogo; diferenças monetárias são calculadas em Python.
- [x] Orçamento e modalidade sobrevivem a continuações sem contaminar outras sessões.
- [x] Reset e expiração descartam o estado sem persistência externa.
- [x] Testes de API verificam conversas em múltiplos turnos e ações de continuidade.
