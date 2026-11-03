# 20 — Verificar alterações automaticamente no GitHub

**O que construir:**
Cada push/PR executa checks reproduzíveis sem chaves de LLM; falhas ficam visíveis antes da entrega.

**Bloqueado por:**
- Nenhum — pode iniciar imediatamente

**Status:** ready-for-agent

## Critérios de Aceitação
- [ ] GitHub Actions executa unitários Python, mypy e testes Node.
- [ ] Testes opcionais Redis e navegador rodam em ambiente isolado sem serviços pagos.
- [ ] Avaliações reais ficam em workflow manual com secrets, limite de consumo e artefatos; nunca em PR de fork.
- [ ] Execução do workflow na revisão enviada é verificada, sem alegar sucesso se houver bloqueio de conta.
