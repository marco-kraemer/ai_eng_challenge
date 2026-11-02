# Busca de políticas no manual

## Fluxo implementado

Depois da verificação de escopo, o modelo pode chamar `search_policies(query)`. A descrição e o prompt exigem essa ferramenta antes de informar horários, contatos, pagamentos, frete, devolução ou garantia. A ferramenta lê apenas o manual local; não busca na internet nem consulta dados de clientes. Catálogo e pedidos permanecem consultas estruturadas separadas.

O Python recupera no máximo três trechos, com ID, seção, título, páginas e texto. O modelo recebe esses dados como resultado de ferramenta e redige a resposta. A interface mostra os trechos consultados em blocos expansíveis. As referências e os trechos da interface são produzidos pelo backend, não inventados pelo modelo; a redação livre ainda pode conter erros e não tem verificação determinística de todas as afirmações.

## Extração e limites

`pypdf` usa extração por layout: a extração padrão deste PDF separa palavras em linhas e destrói os títulos. Removemos cabeçalho/rodapé repetidos, preservamos tabelas em texto e segmentamos por seções. O manual atual gera 26 trechos com até 1.800 caracteres cada. Se uma seção continuar em outra página, ambas ficam na referência (por exemplo, seção 5.2 nas páginas 4–5). Títulos sem conteúdo não viram candidatos.

Revisões com seções maiores são divididas por linha; esse fallback precisa de inspeção quando o manual mudar, principalmente para tabelas grandes e regras com exceções. A divisão não deve ser tratada como adequada a qualquer PDF.

Cada consulta admite até 500 caracteres e retorna até 5.000 caracteres de evidência textual. O chat preserva no máximo seis trechos para apresentação por turno, mesmo quando o modelo faz buscas adicionais. O PDF completo não é enviado ao modelo nem servido publicamente.

## Busca híbrida local

- Lexical: SQLite FTS5, BM25 com peso maior para título, normalização de acentos e remoção de palavras frequentes. Um pequeno conjunto explícito de sinônimos ajuda com formas como `abrem` → `horário/funcionamento` e `parcelar` → `parcelamento`. São termos de busca, sem respostas ou fatos comerciais cadastrados no código.
- Semântica: `intfloat/multilingual-e5-small`, usando artefato ONNX quantizado de `Xenova/multilingual-e5-small`, FastEmbed/ONNX Runtime na CPU, duas threads e vetores normalizados de 384 dimensões. Usamos os prefixos `query:` e `passage:` exigidos pela família E5.
- Combinação: até seis candidatos de cada busca, fusão por posição (RRF, constante 60), peso lexical 1,25 e semântico 1,0. Não somamos diretamente BM25 e cosseno, que têm escalas diferentes. Cosseno abaixo de 0,85 é descartado antes da fusão.

O limite e os pesos foram calibrados na bateria de desenvolvimento descrita abaixo. O cosseno não é probabilidade de acerto, e o filtro não comprova que um trecho responde à pergunta. A instrução do atendente exige admitir ausência de evidência suficiente.

Referências: [modelo E5](https://huggingface.co/intfloat/multilingual-e5-small), [artefato ONNX](https://huggingface.co/Xenova/multilingual-e5-small), [FastEmbed](https://qdrant.tech/documentation/embeddings/fastembed/), [SQLite FTS5/BM25](https://sqlite.org/fts5.html).

## Contradições e contexto

Quando o trecho principal é de pagamento, as seções 3 e 3.1 são recuperadas juntas e uma advertência informa a divergência entre os mínimos. O modelo deve pedir confirmação à equipe da loja, sem resolver a inconsistência perguntando apenas o valor da compra.

Para contatos, as seções 1.2 e 7 são recuperadas juntas quando uma delas é o resultado principal. O telefone dos dados da empresa e o do atendimento remoto são apresentados conforme o canal, sem escolher um número universal. Há ainda grafias diferentes do e-mail na capa e nos dados da empresa: uma pendência da fonte, sem correção por adivinhação.

Uma consulta cujo resultado principal é devolução/troca também recebe a seção 4.4 de exceções. A consulta deve preservar a modalidade já informada pelo cliente; se faltar modalidade, o atendente esclarece ou pergunta. Essa expansão é específica da estrutura deste manual e precisa ser revisada se a numeração mudar.

## Cache e operação

O primeiro uso baixa aproximadamente 130 MB de modelo/tokenizador. Depois, as buscas e os embeddings rodam localmente, sem chamada a API de embeddings ou banco pago. Somente classificação e redação usam OpenRouter, consumindo a cota configurada.

O diretório `.cache/` é ignorado pelo Git. O índice de vetores usa hash do PDF, identificador do encoder e versão de extração. Alteração do PDF invalida o índice automaticamente; novos modelos, artefatos ou regras de segmentação exigem alterar a versão do índice. Gravação é atômica e os arrays são lidos sem pickle. Modelo e índice são reutilizados entre solicitações; o índice lexical é reconstruído em memória. `POLICY_CACHE_DIR` permite escolher outro diretório gravável para o cache.

Para preparar e avaliar, na raiz:

```bash
.venv/bin/python scripts/evaluate_policies.py --output docs/avaliacao-busca-politicas.json
```

Em máquina nova, o comando baixa o modelo e cria o índice. Com cache disponível, reutiliza ambos. Se os arquivos de índice forem removidos, o mesmo comando os reconstrói a partir do PDF. O servidor também inicializa tudo sob demanda na primeira consulta de políticas.

Falhas de PDF/modelo/índice retornam `error`, não `not_found`; não há degradação silenciosa para uma resposta inventada. O log registra a classe do erro para diagnóstico, sem chave ou mensagem do cliente. Entradas inválidas retornam `invalid`.

## Qualidade e recursos observados

Resultado registrado em `avaliacao-busca-politicas.json`, com 22 perguntas positivas e quatro negativas. A métrica positiva exige que todas as seções esperadas apareçam nos três trechos retornados:

| Método | Casos positivos com evidências esperadas |
|---|---:|
| Lexical | 18/22 |
| Semântico | 16/22 |
| Híbrido | 20/22 |

São casos de desenvolvimento, usados também na calibração: não são uma avaliação independente nem uma medida de correção das respostas finais. A busca híbrida recupera evidências de arrependimento em paráfrases sem os termos exatos. Ainda perde frases como “meu teclado pifou logo que chegou” e “posso dividir a compra em prestações?”. A formulação da consulta pelo agente pode ajudar, mas não elimina essa limitação.

Nos negativos, estacionamento, criptomoedas e senha de Wi-Fi não tiveram candidatos. “Aulas de canto gratuitas” trouxe a campanha “Volta às Aulas” na lexical e híbrida: é um falso positivo de recuperação, não evidência de que a loja oferece aulas. O modelo precisa reconhecer que esse texto não responde ao pedido. Não anunciamos ausência de alucinação com base em ranking.

Com o cache já baixado, a avaliação mediu cerca de 2,2 s para preparar o índice/modelo, 7,5 ms de média por busca híbrida e pico de RSS do processo de aproximadamente 672 MB. A primeira execução, incluindo download, levou cerca de 13 s em outra medição. Esses tempos variam por hardware e rede. A instalação atual usa cerca de 130 MB no cache do modelo e poucos KB por índice de vetores.

Não cabe presumir compatibilidade com hospedagem de 512 MB. Avaliar pelo menos 1 GB e um worker, medindo o backend completo sob concorrência antes de publicar. Vários workers duplicam o modelo em memória. Hospedagem pública permanece uma decisão aberta.

## Segurança e validação

Conteúdo recuperado permanece em mensagens de ferramenta; não altera instruções do sistema, ferramentas registradas ou permissões. Testes verificam essa separação, erros, ausência de resultado, limites, fontes, tabelas, continuação de páginas, cache e fluxo HTTP. Isso reduz o risco de injeção por documentos, sem provar resistência absoluta do modelo.

A validação real com OpenRouter confirmou horário com referência à página 2, devolução online apoiada no manual, ausência de informação sobre estacionamento e identificação do conflito de parcelamento. Esses casos não validam todo o conteúdo do manual nem substituem revisão humana das regras conflitantes.
