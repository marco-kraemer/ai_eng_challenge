"""Customer-facing, allowlisted continuations; no internal staff actions."""
REGISTRY = {
    'compare': ('Comparar opções', 'Qual é a diferença entre essas opções?'),
    'cheaper': ('Ver opções mais baratas', 'Tem alguma opção mais barata?'),
    'policy_details': ('Entender melhor', 'Pode explicar melhor essa informação?'),
    'contact': ('Falar com a loja', 'Como posso falar com a loja?'),
    'categories': ('Escolher um instrumento', 'Quero escolher um instrumento.'),
    'hours': ('Horários da loja', 'Quais são os horários da loja?'),
    'online': ('Comprei online', 'Comprei online.'),
    'physical': ('Comprei na loja física', 'Comprei na loja física.'),
}

def next_actions(result: dict) -> list[dict]:
    if result.get('needs_return_channel'):
        identifiers=['online','physical']
    elif len(result.get('products',[]))>=2:
        identifiers=['compare','cheaper','contact']
    elif result.get('sources'):
        identifiers=['policy_details','contact']
    elif result.get('products'):
        identifiers=['cheaper','contact']
    else:
        identifiers=['categories','hours']
    return [{'id':key,'label':REGISTRY[key][0],'message':REGISTRY[key][1]} for key in identifiers]

def resolve_action(identifier: str, state: dict) -> str:
    if identifier not in REGISTRY or identifier not in state.get('allowed_actions',[]):
        raise ValueError('Essa opção não está disponível nesta conversa. Escolha uma opção atual ou escreva sua pergunta.')
    return REGISTRY[identifier][1]
