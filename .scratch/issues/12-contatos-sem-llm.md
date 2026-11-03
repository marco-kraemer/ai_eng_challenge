# 12 — Responder contatos oficiais por canal sem modelo

**O que construir:**
Responder contatos oficiais por canal sem modelo, integrado ao grafo antes da classificação, mantendo contrato de resposta e fontes da interface.

**Bloqueado por:**
- 10

**Status:** done

## Critérios de Aceitação
- [x] Telefone, WhatsApp e e-mail têm respostas sem LLM com páginas e grafias da fonte.
- [x] Divergências entre canais e grafias não são resolvidas por suposição.
- [x] Testes Python, tipos, JavaScript e navegador verificam o fluxo completo e documentação registra limites.

## Validação
- API e navegador com inferência desativada: zero chamadas ao modelo para FAQ reconhecida.
- Respostas com fonte, mudança de PDF, leitura indisponível, cópias isoladas e fallback para perguntas mistas verificados.
