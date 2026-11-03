# Respostas institucionais sem inferência

`app/direct_faq.py` reconhece um conjunto conservador de perguntas completas por intenção. O nó `faq` de `StoreAssistant` executa antes do classificador LangChain. Uma correspondência retorna mensagem, fontes e canais no mesmo contrato usado pela interface; o grafo termina sem chamar o modelo. As ações e a sessão são atualizadas normalmente pela API.

## Cobertura

- Endereço: “Qual é o endereço da loja?”, “Onde vocês ficam?”, “Onde fica a Empório da Música?”.
- Horários: perguntas gerais, abertura/fechamento e horários regulares por dia da semana, sábado, domingo e feriados. As respostas deixam explícitas as condições regulares e as possíveis alterações em datas especiais.
- Contatos: telefone, WhatsApp, e-mail e formas de falar com a loja. Os dois telefones são identificados pelos respectivos canais. As duas grafias de e-mail presentes no manual são preservadas e a divergência é informada.

Maiúsculas, acentos, espaços, pontuação final e algumas formas de saudação/polidez são normalizados. As regras exigem correspondência da pergunta inteira. Não há comparação de similaridade, classificação por LLM ou consulta de embeddings nesse caminho, nem na primeira requisição.

Não é um cache semântico genérico de respostas geradas. Variações não cadastradas seguem pelo modelo; reconhecer um termo isolado não basta. “Onde fica o captador?”, “Qual o endereço de entrega do meu pedido?”, perguntas mistas com programação, comandos para enviar mensagens e instruções para mudar regras não recebem uma resposta institucional automática.

Perguntas como “Vocês abrem hoje?”, “E no sábado?” e datas especiais seguem o fluxo de interpretação existente, que recebe o contexto. Esse encaminhamento não garante que o modelo interprete todo caso corretamente; os limites anteriores continuam valendo.

## Fonte e invalidação

A primeira pergunta reconhecida extrai o PDF local e prepara as respostas institucionais. Endereço e horários são extraídos das seções identificadas, com páginas de origem. Contatos reutilizam a mesma extração determinística das ferramentas existentes (`contacts_from_chunks`). A regra não preenche horários ou endereço ausentes com valores embutidos no código.

O cache LRU é local ao processo e limitado a duas combinações de caminho, SHA-256 do PDF e versão das regras. O hash é calculado a cada pergunta reconhecida: ainda existe leitura do arquivo, mas não nova extração ou chamada ao modelo em um acerto de cache. Alterar o PDF gera uma nova entrada. O processo também verifica que a fonte não mudou durante a extração.

Arquivo ausente, ilegível ou erro de extração não servem a versão antiga: a API retorna indisponibilidade. Se o formato de uma seção deixar de ser reconhecido, aquela resposta não é preparada e a pergunta segue ao fluxo normal. Reiniciar o processo apaga o cache.

Cada resposta é copiada antes de retornar, impedindo que alterações em uma resposta modifiquem as próximas. O cache contém apenas dados institucionais da fonte; não contém histórico de clientes, e-mails de compras ou respostas personalizadas. Produtos, preços, estoque e pedidos mantêm suas consultas existentes.

## Verificação

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/mypy app --check-untyped-defs
node tests/test_frontend.js
```

Os testes cobrem variações, chamadas de modelo zeradas, invalidar/reconstruir após mudança de fonte, arquivo removido/ilegível, cópias isoladas, dias regulares, datas relativas, perguntas mistas, canais divergentes e preservação da sessão. Os testes anteriores de políticas usam uma pergunta sobre datas especiais para continuar exercitando a busca híbrida e a geração, sem passar pelo novo atalho.

Com Playwright/Chromium instalados:

```bash
PYTHONPATH=. .venv/bin/python tests/browser_faq_smoke.py
```

O script inicia um servidor temporário com inferência desativada e usa navegador, API e PDF reais. Valida endereço, horários, WhatsApp, conflito de e-mail, fontes, celular e reinício da conversa; exige zero chamadas ao modelo. Nenhuma chave OpenRouter é enviada. Não foi adicionado serviço externo de cache.
