# Empório da Música

Protótipo em desenvolvimento: chat FastAPI com catálogo CSV, adaptador Gemini REST e execução de ferramentas no backend. O ticket 01 ainda depende de validação com credencial real; os demais tickets permanecem bloqueados por essa dependência.

## Executar localmente

Requer Python 3.12 ou superior. Na raiz do repositório:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export GEMINI_API_KEY='sua-chave'
export GEMINI_MODEL='identificador-do-modelo-validado-na-sua-conta'
.venv/bin/uvicorn app.web:app --host 127.0.0.1 --port 8000
```

Abra http://127.0.0.1:8000. Sem configuração, a página funciona e o endpoint responde indisponibilidade. Não há resposta simulada apresentada como resposta de modelo real.

## Modelo e custo

Gemini é um candidato implementado, ainda não uma escolha validada. A [documentação de preços](https://ai.google.dev/gemini-api/docs/pricing) lista camada gratuita para determinados modelos, com disponibilidade limitada. Consulte o modelo e as cotas da conta antes de configurar. O backend não pode determinar se a chave pertence a uma conta com faturamento: use exclusivamente projeto sem cobrança habilitada para preservar custo zero. Não existe fallback para outro modelo ou serviço pago.

O adaptador usa o contrato REST `generateContent` e function calling descrito na [documentação oficial](https://ai.google.dev/gemini-api/docs/function-calling). Ainda falta executar chamada real para verificar compatibilidade do modelo escolhido, ida e volta das ferramentas e cotas. Nenhuma chave estava configurada nesta execução.

## Verificação

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/mypy app --check-untyped-defs
```

Testes usam provedor roteirizado e TestClient, sem chamadas externas nem custos. Cobrem filtros de orçamento/estoque, entradas inválidas, consulta vazia/erro, ciclo de ferramenta e indisponibilidade sem credencial. Não comprovam qualidade do modelo ou funcionamento real no navegador.

## Decisões e limites atuais

- FastAPI serve HTML/CSS/JavaScript sem frontend separado. Conteúdo de mensagens é inserido com `textContent`.
- O modelo solicita ferramentas; Python executa somente catálogo e listagem de categorias registrados. CSV é relido a cada consulta; preços usam Decimal.
- Resultados têm no máximo dez produtos por chamada; o loop tem até quatro rodadas e três chamadas por rodada.
- Chave apenas no servidor; erros externos não são enviados ao cliente com detalhes sensíveis.
- O chat ainda não mantém contexto entre mensagens. Políticas, pedidos, promoções, limites públicos e hospedagem serão implementados nos tickets seguintes.
- O prompt orienta fundamentação, mas a resposta livre do modelo ainda não tem garantia determinística contra invenção.
- Sem histórico persistente e sem ferramentas de escrita, carrinho, reserva ou pagamento.

## Uso de assistentes

Codex foi usado para decompor decisões em tickets e implementar testes, catálogo, integração inicial e interface. O progresso e os bloqueios ficam em `.scratch/issues/`; decisões de produto estão em `docs/decisoes-do-projeto-agente-artefact.md`.
