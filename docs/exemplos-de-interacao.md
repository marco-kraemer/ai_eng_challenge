# Exemplos de interação observados

Cinco interações executadas com OpenRouter durante o desenvolvimento. Respostas abaixo são resumos fiéis dos resultados observados, não snapshots determinísticos do texto. O modelo selecionado pelo roteador gratuito e a redação podem variar; o visual foi evoluído depois de algumas dessas consultas. Não há dados de clientes nestes exemplos.

## 1. Busca comercial com orçamento

**Pergunta:** Quais violões ativos e em estoque custam até R$ 600? Mostre nome e preço de até três opções.

**Resultado observado:** Yamaha C40 Nylon Natural — R$ 599,90; Tagima Memphis AC-39 Nylon Natural — R$ 429,90; Rozini RC-104 Nylon Estudante — R$ 459,90. O modelo executou ferramentas antes de responder.

**Verificação:** IDs 81 e seguintes em `data/products.csv`, filtro de preço/estoque/categoria. A interface atual mostra dados estruturados em cards, sem depender de uma tabela escrita pelo modelo.

## 2. Horário da loja com fonte

**Pergunta:** Que horas vocês abrem?

**Resultado observado:** Segunda a sexta, 9h às 18h; sábado, 9h às 13h; domingos e feriados fechado. O manual também informa que o WhatsApp segue o mesmo horário e que datas especiais podem ter alterações comunicadas pela loja.

**Verificação:** Seção 2, página 2 do PDF. Chamada real da ferramenta de políticas; resposta HTTP 200 com fontes na API. Antes do RAG, o agente dizia que não tinha acesso ao horário.

## 3. Devolução com modalidade conhecida

**Pergunta:** Comprei um violão online e me arrependi. Como devolvo?

**Resultado observado:** Devolução por arrependimento em até sete dias corridos após o recebimento; embalagem original, sem sinais de uso, com acessórios e manuais; reembolso pela mesma forma de pagamento em até dez dias úteis; frete de devolução por conta da loja. Foram recuperadas também exceções da seção 4.4.

**Verificação:** Seção 4.1 e exceções na página 4. A resposta se apoiou em trechos consultados, sem tratar o caso como compra presencial. Em outra validação, uma pergunta sem modalidade recebeu apenas a pergunta fixa “online ou loja física?”; a informação adicional “comprei online” levou à consulta correspondente.

## 4. Parcelamento com fonte inconsistente

**Pergunta:** Posso parcelar em três vezes? Qual o mínimo?

**Resultado observado:** O agente apresentou a divergência: o quadro de pagamento menciona parcela mínima de R$ 100, enquanto a seção 3.1 descreve até três vezes sem valor mínimo, exceto abaixo de R$ 50. Informou que a condição deve ser confirmada com a equipe da loja.

**Verificação:** Seções 3 e 3.1, página 3, recuperadas juntas. Não foi escolhida uma regra como se a inconsistência estivesse resolvida.

## 5. Solicitação fora de escopo

**Pergunta:** Me ensine a usar for loop em Python.

**Resultado observado:** “Posso ajudar com instrumentos, produtos e atendimento da Empório da Música. Esse assunto fica fora do meu atendimento. Quer encontrar um instrumento?”

**Verificação:** A classificação negada não libera o atendente. A resposta é um texto fixo da aplicação. Uma tentativa de mudar sua identidade para Nemotron e pedir aula de Python usando uma guitarra como pretexto também foi recusada.

## Limite encontrado na validação final

O teste final via HTTP conseguiu iniciar a dúvida de devolução e mostrar as opções “Compra online”/“Loja física”. Na continuação, o OpenRouter retornou HTTP 429. Não foi acionado fallback pago. O comportamento multi-turno completo foi validado com provedor simulado nos testes e o fluxo visual em navegador real, sem apresentar esse teste interrompido como uma validação real bem-sucedida do rascunho.
