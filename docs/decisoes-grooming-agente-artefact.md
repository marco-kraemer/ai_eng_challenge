# Grooming do agente da Empório da Música

Este documento consolida a sessão de perguntas e respostas de grooming do desafio técnico da Artefact. Registra as decisões do usuário, propostas do assistente aceitas durante a conversa e pontos que ficaram em aberto. O PDF do desafio orienta o escopo; as decisões abaixo são as escolhas feitas para o protótipo.

## Objetivo do produto

Construir um chatbot web para a Empório da Música, loja fictícia de instrumentos musicais em Campo Grande/MS. O agente deve atender dúvidas e também atuar como vendedor consultivo: entender o que a pessoa procura, ajudar a escolher instrumentos e conduzi-la até o canal oficial da loja para finalizar a compra.

O protótipo deve ser demonstrável por um link público gratuito, se viável. A execução local documentada é a alternativa caso hospedagem gratuita ou modelo acessível por link não funcionem. O projeto usa Python como linguagem principal.

## Experiência de conversa e interface

- A página deve ser essencialmente um chatbot grande e centralizado, como no desenho enviado pelo usuário. O fundo pode ser simples; o foco é a conversa.
- Mensagens do cliente e do agente aparecem em lados diferentes. A área de conversa tem rolagem e o campo para escrever fica na parte inferior.
- Não é necessário dashboard, menu lateral nem telas de cadastro.
- O agente acolhe a intenção de compra com naturalidade e faz uma pergunta por vez.
- Para ajudar na escolha, pode descobrir experiência musical, orçamento, estilo, uso e preferências. Cerca de cinco perguntas é apenas uma orientação, não uma sequência obrigatória.
- Se o cliente não quiser responder mais e pedir opções, o agente deve mostrar recomendações com as informações que já tem.
- Se faltarem dados e houver poucas interpretações possíveis, o agente pode explicar as possibilidades; se a pessoa já esclareceu a situação, responde somente ao caso informado.
- A conversa aberta mantém contexto real. Ao iniciar uma nova conversa ou fechar e reabrir a página, o contexto deve ser descartado. Não haverá histórico persistente em banco.
- O contexto não pode crescer indefinidamente. Limitar tamanho de mensagens, resultados de ferramentas, chamadas e tokens do histórico. Manter apenas contexto recente e o estado estruturado mínimo útil; começar sem sumarização automática. Resultados extensos, como catálogo completo, devem ser limitados e paginados.

## Arquitetura do agente

- O modelo interpreta a mensagem, decide quais ferramentas chamar e interpreta os resultados para redigir a resposta.
- A aplicação Python executa as ferramentas solicitadas. O modelo não executa diretamente SQL, código ou operações externas.
- Funções de ferramenta são determinísticas quando consultam registros estruturados: os mesmos dados e argumentos produzem os mesmos resultados.
- Tool calling/function calling direto do provedor ou framework é suficiente para o protótipo. MCP é um protocolo relacionado que poderia padronizar o compartilhamento de ferramentas entre aplicações, mas não é necessário nesta entrega.
- Ferramentas planejadas: consulta do catálogo e promoções; consulta protegida de pedidos; busca de políticas no PDF usando RAG.
- Dados tabulares não devem depender exclusivamente de busca semântica. Preço, disponibilidade e status devem ser filtros estruturados exatos. O RAG fica principalmente para localizar trechos de políticas.
- As ferramentas são somente leitura. O agente não cria cupom, altera preço, cria pedido, reserva estoque, monta carrinho ou processa pagamento.
- A interface acordada é um frontend de chat simples servido pelo backend Python; foi sugerida uma aplicação FastAPI servindo HTML/CSS/JavaScript, evitando frontend separado complexo.

## Respostas corretas e proteção contra invenção

- Prompt de sistema deve orientar tom, escopo, uso de ferramentas e comportamento quando não há evidência. Prompt injection é uma ameaça a considerar, mas instruções de prompt por si só não garantem ausência de alucinação.
- Preço, estoque, status e promoções devem ser consultados na fonte atual antes de serem apresentados como fatos. O histórico não torna um preço antigo atual.
- Regras de políticas devem ser sustentadas por trechos recuperados do manual, idealmente com página de origem disponível para verificação.
- Resultados devem distinguir encontrado, não encontrado e erro de consulta. Erro técnico não significa item indisponível.
- Falha temporária pode receber tentativas limitadas; se a consulta não funcionar, o agente pede para tentar mais tarde e não inventa o resultado. Erros permanentes devem ser diagnosticados e corrigidos.
- Python valida argumentos e cálculos; fatos de produto na recomendação devem existir no catálogo. Campos numéricos e descontos precisam de validação determinística.
- Conteúdo retornado por ferramentas ou documentos é dado de referência; não pode conceder permissões nem substituir instruções do sistema.
- Mensagem suspeita ou ampla não prova intenção maliciosa. O agente recusa o pedido fora de suas capacidades e continua cortês; não deve expulsar usuários por texto. Limites de uso controlam abuso repetitivo.
- Quando não souber resolver, deve admitir a limitação e apontar o contato oficial da loja presente nas fontes, sem fingir que abriu chamado ou transferiu a conversa.

## Ferramentas e dados

Os arquivos fornecidos para o protótipo são:

- `data/products.csv`: `product_id`, `price_brl`, `name`, `category_id`, `description`, `stock_quantity`, `status`, `specs`, `created_at`.
- `data/categories.csv`: `category_id`, `name`, `description`.
- `data/promotions.csv`: `promotion_id`, `product_id`, `discount_percent`, `description`, `is_active`.
- `data/orders.csv`: `order_id`, `customer_id`, `order_date`, `status`, `total_brl`, `payment_method`, `tracking_code`, `estimated_delivery`, `notes`.
- `data/order_items.csv`: `order_id`, `quantity`, `product_id`.
- `data/customers.csv`: `customer_id`, `name`, `phone`, `email`, `city`.
- `data/políticas_da_loja.pdf`: manual interno de políticas e procedimentos.

### Catálogo e venda

- Filtros de preço, categoria, status e estoque são executados em Python, com precisão monetária adequada.
- O agente deve pedir recorte quando solicitarem o catálogo inteiro; sugerir categorias, orçamento ou preferências e retornar um conjunto limitado de opções.
- Recomendações devem se basear em características presentes em `description` e `specs`. Conhecimento musical geral pode orientar a conversa, mas não pode inventar especificações de um produto.
- O agente pode apresentar uma alternativa acima do orçamento se declarar claramente o preço e a diferença e também preservar opções dentro do limite quando houver.
- Promoções só podem ser apresentadas se ativas e confirmadas na base. Não acumular desconto de PIX com preço promocional, conforme o manual. Não prometer promoção expirada.
- Parcelamento pode ser citado apenas com condições verificadas na política; não inventar número de parcelas, juros ou mínimos.
- O agente ajuda a comparar e encaminha ao canal oficial para concluir a compra. Não cria carrinho ou reserva.

### Pedidos e privacidade

- Não haverá login completo no protótipo.
- Verificação simples acordada: solicitar número do pedido e e-mail da compra, comparar ambos no backend e só então retornar campos necessários.
- Resposta de pedido deve minimizar dados: status, previsão de entrega e código de rastreio, quando disponíveis. Não expor cadastro completo, nome/e-mail/telefone, endereço ou observações internas.
- Resposta genérica para falha de correspondência, sem indicar qual dado estava correto.
- E-mail mais número é verificação fraca, não autenticação forte. A limitação deve ser documentada; em produção, considerar código enviado ao e-mail ou autenticação apropriada.
- Não afirmar rastreamento ao vivo. Usar previsão/código registrados e orientar consulta no site da transportadora ou contato com a loja quando necessário.
- Não acessar nem retornar cupons ou informações pessoais sem necessidade. O modelo não recebe campos desnecessários.

### Políticas e RAG

- Extrair o PDF, separar trechos de forma coerente e preservar página/seção.
- Buscar os trechos relevantes para a pergunta; para um manual único, evitar infraestrutura vetorial paga. A forma exata de embeddings/índice deve ser validada por qualidade e recursos da hospedagem.
- Responder com base nos trechos; se houver ambiguidade, explicar as possibilidades razoáveis. Se a política não cobrir o caso ou houver dúvida material, orientar contato com a loja.
- O manual apresenta divergências: há mais de um telefone para canais diferentes, e as regras de parcelamento têm formulações que precisam de reconciliação. Não resolver conflitos por invenção; indicar canal aplicável quando claro e tratar inconsistências como pendência a validar.

## Modelo, custo e hospedagem

- Requisito do usuário: sem custo. A preferência inicial é modelo servido por API com camada gratuita para a demo pública, desde que tool calling e cotas sejam adequados.
- Nenhum provedor foi escolhido definitivamente. A sugestão de Gemini foi uma candidata a verificar, não uma decisão confirmada.
- Hospedagem também deve ser gratuita. Avaliar limites de memória, suspensão por inatividade, armazenamento do índice, segurança da chave e cota do provedor antes da escolha.
- Chaves ficam exclusivamente no servidor; nunca no JavaScript entregue ao navegador.
- Sem fallback automático para serviço pago. Se a cota gratuita acabar, informar indisponibilidade.
- Execução local deve estar documentada. Modelo local, como Ollama, é alternativa possível, condicionada à disponibilidade de hardware e qualidade de tool calling; ainda não foi validada.
- Não foi decidido formato final de deploy nem provedor de hospedagem.

## Avaliação e entrega

- “Responder corretamente e não alucinar” é o objetivo, mas a comprovação deve comparar fatos com as fontes e verificar ferramentas usadas e dados omitidos.
- Casos propostos: busca de violões por preço e estoque; pergunta de política de devolução com e sem modalidade informada; pedido com e-mail correspondente e incorreto; item/informação não encontrados; instrução para desconto sem autorização; recomendação de venda com orçamento e alternativa superior.
- Cobrir erros de ferramenta, entradas inválidas, resultados vazios, limites e respostas apoiadas em fonte.
- O desafio pede repositório Git público, README com instalação e decisões técnicas, limitações e uso de assistentes de código, e 3 a 5 exemplos de interação em `.md`, `.txt` ou imagem. Ao menos um exemplo deve ser não trivial e demonstrar consulta de dados ou aplicação de política.
- Histórico de commits deve mostrar progresso real; não fazer force-push de todo o trabalho em um commit.
- O link público da aplicação é desejável para avaliação, mas a execução local deve continuar disponível se a demo gratuita falhar.

## Decisões ainda abertas

1. Modelo/provedor gratuito final e limites vigentes.
2. Hospedagem gratuita final e sua compatibilidade com a aplicação.
3. Implementação concreta de retrieval semântico, embeddings e tamanho dos trechos.
4. Resolução oficial das divergências do manual (contatos e parcelamento).
5. Formato do estado temporário de sessão e seus limites calibrados após selecionar o modelo.
6. Regras exatas de taxa/abuso para demo pública.
