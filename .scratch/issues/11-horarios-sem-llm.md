# 11 — Responder horários gerais e por dia sem modelo

**O que construir:**
Responder horários gerais e por dia sem modelo, integrado ao grafo antes da classificação, mantendo contrato de resposta e fontes da interface.

**Bloqueado por:**
- 10

**Status:** done

## Critérios de Aceitação
- [x] Horários gerais, dias úteis, sábado, domingo e feriados usam dados do manual e fontes sem LLM.
- [x] Datas relativas, exceções e perguntas ambíguas seguem o grafo atual; mudanças no PDF invalidam respostas.
- [x] API preserva contexto, ações e isolamento entre sessões; testes de regressão passam.
