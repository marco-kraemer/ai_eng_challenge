# 04 — Acompanhar pedidos e concluir a migração com limites verificáveis

**O que construir:**
Concluir rota de pedido para formulário verificado e validar atendimento sob erros e limites. Documentar grafo real e reprodução dos fluxos, removendo o loop manual substituído.

**Bloqueado por:**
- 01; 02; 03

**Status:** done

## Critérios de Aceitação
- [x] Pedido abre verificação; e-mail é interceptado antes do modelo e omitido do contexto reutilizável.
- [x] Consulta por número e e-mail segue determinística, sem LLM e sem dados pessoais na resposta.
- [x] Loops, ferramentas e contexto têm limites; HTTP 429 mantém mensagem clara sem fallback pago.
- [x] Suíte Python, tipos, JavaScript e smoke de navegador passam; documentação distingue mocks, dados reais e limites.

## Validação executada
- 64 testes Python e mypy passaram também no segundo ambiente Python com requirements.txt instalado.
- Testes Node e dois smokes Chromium passaram; no smoke do grafo, apenas inferência foi simulada, com API, catálogo e recuperação do PDF reais.
- Dependências verificadas com pip check; servidor local reiniciado com esta versão.
