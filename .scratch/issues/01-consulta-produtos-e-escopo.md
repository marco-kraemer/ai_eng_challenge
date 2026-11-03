# 01 — Consultar produtos com LangChain e LangGraph

**O que construir:**
Migrar POST /api/chat para um StateGraph compilado com classificação de escopo, identidade, ferramentas LangChain e cards reais, preservando OpenRouter gratuito e a busca visual sem LLM.

**Bloqueado por:**
- Nenhum — pode iniciar imediatamente

**Status:** done

## Critérios de Aceitação
- [x] Pergunta sobre violões executa ferramenta LangChain no grafo e retorna cards reais pela API.
- [x] Fora do escopo, classificação inválida e identidade encerram sem ferramentas comerciais.
- [x] Chamadas mantêm IDs nativos; argumentos inválidos não executam consultas.
- [x] Busca visual continua sem modelo; testes RED-GREEN-REFACTOR passam.
