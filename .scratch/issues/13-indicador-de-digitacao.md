# 13 — Mostrar atividade no chat durante a espera

**O que construir:**
Exibir uma mensagem temporária de digitação com três pontos animados após o envio. Confirmar o envio, impedir pedidos duplicados e remover o indicador em resposta, falha, cancelamento ou nova conversa, preservando acessibilidade e preferência por movimento reduzido.

**Bloqueado por:**
- Nenhum — pode iniciar imediatamente

**Status:** done

## Critérios de Aceitação
- [x] Indicador aparece imediatamente após a mensagem e desaparece antes da resposta ou erro.
- [x] Cliques e Enter repetidos não criam novas requisições enquanto há uma em andamento.
- [x] Reinício remove indicador e respostas antigas não alteram uma espera mais recente.
- [x] Texto de espera é acessível; pontos respeitam movimento reduzido; testes Node e navegador passam.
