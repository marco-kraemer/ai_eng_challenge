"""Allowlisted UI continuations. Labels never execute arbitrary tools or permissions."""
REGISTRY = {
    'draft': ('Preparar resposta ao cliente', 'Prepare apenas uma mensagem curta, pronta para o atendente revisar e encaminhar ao cliente, com base na dúvida e nas evidências deste atendimento. Consulte novamente as fontes antes de escrever. Preserve condições, limites e divergências relevantes; não prometa ações não realizadas e não inclua instruções internas.'),
    'compare': ('Comparar opções', 'Compare os instrumentos que acabamos de consultar. Releia os dados atuais com compare_products e respeite meu orçamento.'),
    'cheaper': ('Buscar mais baratos', 'Busque opções mais baratas na mesma categoria, preservando meu orçamento e preferências. Consulte preço e estoque novamente.'),
    'policy_details': ('Entender a regra', 'Explique a regra principal que acabamos de consultar e suas exceções relevantes. Busque novamente no manual antes de responder.'),
    'contact': ('Ver canais de contato', 'Consulte o manual e apresente os canais de contato da loja para esse atendimento, identificando eventuais divergências.'),
    'categories': ('Explorar instrumentos', 'Quais categorias de instrumentos vocês têm? Consulte as categorias disponíveis.'),
    'hours': ('Horários da loja', 'Quais são os horários de atendimento da loja? Consulte o manual.'),
    'online': ('Compra online', 'A compra foi feita online.'),
    'physical': ('Loja física', 'A compra foi feita presencialmente na loja física.'),
}

def next_actions(result: dict) -> list[dict]:
    if result.get('needs_return_channel'):
        identifiers=['online','physical']
    elif len(result.get('products',[]))>=2:
        identifiers=['compare','cheaper','draft'] if not result.get('draft') else ['compare','cheaper','contact']
    elif result.get('sources'):
        identifiers=['policy_details','draft','contact'] if not result.get('draft') else ['policy_details','contact']
    elif result.get('products'):
        identifiers=['cheaper','contact']
    else:
        identifiers=['categories','hours']
    return [{'id':key,'label':REGISTRY[key][0],'message':REGISTRY[key][1]} for key in identifiers]

def resolve_action(identifier: str, state: dict) -> str:
    if identifier not in REGISTRY or identifier not in state.get('allowed_actions',[]):
        raise ValueError('Essa opção não está disponível neste atendimento. Escolha uma opção atual ou escreva sua pergunta.')
    return REGISTRY[identifier][1]
