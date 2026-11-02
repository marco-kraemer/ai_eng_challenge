# Experiência do cliente

## Público e linguagem

O chatbot é para o cliente final da Empório da Música. Isso substitui a interpretação anterior de ferramenta de trabalho para atendentes. A interface não apresenta slogans, frases motivacionais, preparação de respostas para outro cliente ou perguntas em terceira pessoa sobre um cliente hipotético.

A abertura pergunta apenas “Como posso ajudar?” e oferece quatro caminhos: encontrar um instrumento, acompanhar pedido, dúvidas da compra e informações da loja. O campo de mensagem livre continua disponível em todas as etapas.

## Escolha de instrumento

1. “Encontrar um instrumento” abre a lista das categorias reais de `data/categories.csv`, com ilustrações SVG próprias de cada família.
2. Nada é enviado ao chat ou ao modelo nessa abertura. Não há categoria selecionada automaticamente.
3. Depois de escolher o instrumento, o cliente escolhe um teto de preço sugerido, digita outro valor ou continua sem orçamento definido. Valores sugeridos não são aplicados sem clique.
4. A busca chama `/api/catalog/search`, com categoria e, somente quando informado, preço máximo. O backend valida os dados e consulta o CSV de produtos ativos e em estoque.
5. Os resultados aparecem em cards com valores e descrições da fonte. A sessão mantém categoria/orçamento/IDs para perguntas seguintes.

A consulta guiada não usa OpenRouter e funciona mesmo sem saldo/cota de modelo. Comparações e outras respostas conversacionais ainda usam o modelo configurado, que não foi alterado.

As imagens representam categorias, não fotos ou especificações de produtos. O SVG é local, não depende de CDN e não foi atribuído a uma marca de instrumento. As nove famílias são violões, guitarras, baixos, teclados/pianos, bateria/percussão, ukuleles, cordas orquestrais e os dois grupos de sopro fornecidos no CSV.

## Dúvidas e pedidos

“Dúvidas sobre minha compra” abre assuntos explícitos: trocar/devolver, defeito, entrega/frete, pagamento e garantia. “Informações da loja” abre horários, endereço e contato. Só o clique no assunto envia a pergunta correspondente, em linguagem do cliente.

“Acompanhar meu pedido” abre diretamente o formulário de número e e-mail da compra, sem modelo intermediário. As regras de privacidade e minimização continuam iguais.

Ações de continuação usam perguntas naturais como “Qual é a diferença entre essas opções?” e “Tem alguma opção mais barata?”. O endpoint rejeita a antiga ação de rascunho, mesmo se um estado anterior ainda a contiver.

## Validação

49 testes Python e mypy; teste Node de parsing monetário BRL, categoria explícita, orçamento opcional, estado de conversa, fontes e descarte de resposta atrasada. Chromium testa o fluxo real de categorias/ilustrações/catálogo em desktop e celular, com modelo e credenciais de pedido simulados. O teste não afirma que a API de modelo esteja disponível quando sua cota está esgotada.
