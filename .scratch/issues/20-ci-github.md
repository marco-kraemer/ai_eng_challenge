# 20 — Verificar alterações automaticamente no GitHub

**O que construir:**
Cada push/PR executa checks reproduzíveis sem chaves de LLM; falhas ficam visíveis antes da entrega.

**Bloqueado por:**
- Nenhum — pode iniciar imediatamente

**Status:** done

## Critérios de Aceitação
- [x] GitHub Actions executa unitários Python, mypy e testes Node.
- [x] Testes opcionais Redis e navegador rodam em ambiente isolado sem serviços pagos.
- [x] Avaliações reais ficam em workflow manual com secrets, limite de consumo e artefatos; nunca em PR de fork.
- [x] Execução do workflow na revisão enviada é verificada, sem alegar sucesso se houver bloqueio de conta.

## Encerramento — 2026-11-03
- Avaliação live ampliada: 26/26 contratos, 40 chamadas, US$ 0,0237872 estimados; `docs/avaliacao-agente.json`.
- Revisão qualitativa e imperfeições: `docs/observabilidade-e-avaliacao.md`. Não é garantia de ausência de alucinação.
- CI remoto aprovado em `185dfcc`, incluindo a regressão adicional de streaming com Redis real.
