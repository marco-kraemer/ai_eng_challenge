# 21 — Preparar apresentação e validar entrega final

**O que construir:**
Recrutador encontra demo pública, arquitetura, decisões, resultados e 3–5 conversas reais atuais, além de instruções verificadas para executar o projeto.

**Bloqueado por:**
- 14
- 15
- 16
- 17
- 18
- 19
- 20

**Status:** done

## Critérios de Aceitação
- [x] README personalizado mostra demo, screenshot, arquitetura e decisões justificadas, com uso de assistentes explícito.
- [x] Exemplos reais atuais cobrem catálogo/contexto, política não trivial, pedido e recusa, com limitações honestas.
- [x] Documentação de deploy e métricas corresponde ao estado publicado; referências históricas não contradizem a entrega.
- [x] Repositório público e demo anônima são conferidos; suíte completa, tipos, navegador e CI validados.
- [x] Pendências externas, riscos e próximos passos documentados; não enviar e-mail ou submeter candidatura automaticamente.

## Evidência — 2026-11-03
- README, screenshots reais desktop/mobile, cinco exemplos literais e documentação atualizados.
- GitHub público autorizado e histórico revisado; URL anônima conferida no navegador.
- 156 testes com Redis real, mypy 31 arquivos e Node/Chromium passaram. CI remoto confirmado; ver badge para a revisão atual.
- Backend `185dfcc` verificado em produção: três turnos OpenAI/SSE/Upstash + reset, sem falhas (`docs/verificacao-producao.json`).
- Sem e-mail ou submissão automática. Limites e próximos passos publicados.
