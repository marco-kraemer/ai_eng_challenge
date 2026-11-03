# Experiência do cliente

## Público e linguagem

O chatbot é para o cliente final da Empório da Música. Isso substitui a interpretação anterior de ferramenta de trabalho para atendentes. A interface não apresenta slogans, frases motivacionais, preparação de respostas para outro cliente ou perguntas em terceira pessoa sobre um cliente hipotético.

O atendente virtual se chama Tom e se identifica como inteligência artificial. Sua voz é próxima, tranquila e prática, sem slogans ou pressão de compra. [Personalidade e limites](personalidade-tom.md).

A abertura pergunta apenas “Como posso ajudar?” e oferece quatro caminhos: encontrar um instrumento, acompanhar pedido, dúvidas da compra e informações da loja. O campo de mensagem livre continua disponível em todas as etapas.

## Escolha de instrumento

1. “Encontrar um instrumento” abre as categorias de `data/categories.csv` que possuem produtos ativos com estoque positivo, com esboços SVG monocromáticos.
2. Nada é enviado ao chat ou ao modelo nessa abertura. Não há categoria selecionada automaticamente.
3. Depois de selecionar uma ou mais categorias, ou Todos os instrumentos, e continuar, o cliente escolhe um teto de preço sugerido, digita outro valor ou continua sem orçamento definido. Valores sugeridos não são aplicados sem clique.
4. A busca chama `/api/catalog/search`, com categoria ou união de categorias e, somente quando informado, preço máximo. O backend valida os dados e consulta o CSV de produtos ativos e em estoque.
5. Os resultados aparecem em cards com valores e descrições da fonte. A sessão mantém categoria/orçamento/IDs para perguntas seguintes.

A consulta guiada e a comparação pelo seletor não usam LLM e funcionam mesmo sem saldo/cota. Mensagens livres usam OpenAI direta por padrão.

As imagens representam categorias, não fotos ou especificações de produtos. O SVG é local, não depende de CDN e não foi atribuído a uma marca de instrumento. O cadastro contém nove famílias; no catálogo atual, apenas seis possuem produtos disponíveis: violões, guitarras, baixos, teclados/pianos, bateria/percussão e ukuleles. A seleção é calculada a cada abertura e a consulta revalida estoque. Não há fotos reais de produtos fornecidas.

## Dúvidas e pedidos

“Dúvidas sobre minha compra” abre assuntos explícitos: trocar/devolver, defeito, entrega/frete, pagamento e garantia. “Informações da loja” abre horários, endereço e contato. Só o clique no assunto envia a pergunta correspondente, em linguagem do cliente.

“Acompanhar meu pedido” abre diretamente o formulário de número e e-mail da compra, sem modelo intermediário. As regras de privacidade e minimização continuam iguais.

Ações de continuação usam perguntas naturais como “Qual é a diferença entre essas opções?” e “Tem alguma opção mais barata?”. O endpoint rejeita a antiga ação de rascunho, mesmo se um estado anterior ainda a contiver.

## Validação

73 testes Python e mypy; teste Node de parsing monetário BRL, categoria explícita, orçamento opcional, estado de conversa, fontes e descarte de resposta atrasada. Chromium testa o fluxo real de categorias/ilustrações/catálogo em desktop e celular, com modelo e credenciais de pedido simulados. O teste não afirma que a API de modelo esteja disponível quando sua cota está esgotada.

## Orçamento e comparação

Sem opções dentro do teto, a API encontra o menor preço disponível da mesma categoria considerando todas as páginas e pede confirmação antes de ampliar. A resposta não mostra produtos acima do teto original. Sem estoque, a mensagem é distinta e não sugere aumentar o preço. O resumo da busca permite editar o orçamento preservando instrumento e valor anteriores.

Os cards exibem até três especificações reais com nomes legíveis. Marque entre dois e quatro produtos para comparação determinística em tabela acessível; preços de tabela e estoque são relidos; ofertas não são acumuladas nessa comparação. Em celular, a tabela tem rolagem interna e indicação de gesto. Novos resultados desativam seleções anteriores; reiniciar apaga a seleção. Essas operações não chamam a LLM.

O teste `tests/browser_catalog_smoke.py` valida APIs reais e proíbe chamadas ao chat durante esse fluxo. A avaliação reproduzível está em `scripts/evaluate_journeys.py`, com oito jornadas e inferência simulada explicitamente identificada no relatório.
