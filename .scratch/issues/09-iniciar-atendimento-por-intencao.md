# 09 — Iniciar atendimento por intenção em uma página com identidade própria

**O que construir:**
Reformular a abertura para assistente híbrido da loja. Quatro cards de intenção (instrumentos, políticas, situações de clientes, informações da loja) enviam perguntas reais ao endpoint existente. Integrar identidade visual, estado inicial, acesso ao campo de texto e layout responsivo nesta jornada.

**Bloqueado por:**
- Nenhum — pode iniciar imediatamente

**Status:** complete

## Critérios de Aceitação
- [x] Os quatro cards abrem consultas úteis dentro das capacidades existentes, sem simular dados ou oferecer funcionalidades indisponíveis.
- [x] A abertura comunica apoio ao atendimento e consulta de produtos, com linguagem neutra sobre quem usa a página.
- [x] O fluxo de clique, envio, carregamento e resposta é testado; a página funciona por teclado e em desktop/celular.

## Validação

Teste de contrato da página passa. Playwright executado com Chromium em desktop 1440×1000 e celular 390×844: quatro intenções, clique/envio/resposta/reinício e ausência de overflow horizontal/erros JS. Backend simulado somente na verificação visual; consultas reais das fontes já validadas nos tickets 01/03. Capturas inspecionadas visualmente.
