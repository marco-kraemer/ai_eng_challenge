"""Conservative institutional FAQ before inference; bounded, PDF-versioned cache.

This is an intent shortcut, not fuzzy reuse of arbitrary generated responses.
Only complete, known questions match. Documents remain the source of facts.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from functools import lru_cache
from pathlib import Path
import re
import threading
import unicodedata

from app.policies import extract_chunks
from app.contacts import contacts_from_chunks

_lock = threading.RLock()
_STORE = r'(?:da loja|de voces|d[ao] emporio(?: da musica)?)'
_ADDRESS = (
    rf'qual(?: e)? o endereco {_STORE}',
    r'onde voces ficam',
    r'onde fica (?:a loja|o emporio(?: da musica)?|a emporio(?: da musica)?)',
    r'qual(?: e)? a localizacao da loja',
)

_GENERAL_HOURS = (
    r'que horas voces (?:abrem|fecham)',
    r'que horas (?:a loja|o emporio(?: da musica)?) (?:abre|fecha)',
    rf'quais(?: sao)? os horarios {_STORE}',
    r'qual(?: e)? o horario (?:de funcionamento|de atendimento)(?: da loja)?',
    r'quais(?: sao)? os horarios de (?:atendimento|funcionamento)(?: da loja)?',
)
_DAYS = {'segunda': 'weekday', 'terca': 'weekday', 'quarta': 'weekday', 'quinta': 'weekday',
         'sexta': 'weekday', 'sabado': 'saturday', 'domingo': 'sunday', 'feriado': 'holiday'}
_DAY_QUESTIONS = (
    r'(?:voces abrem|a loja abre|abrem) (?:no|na|aos|as|nos|nas) (.+)',
    r'qual(?: e)? o horario (?:no|na|aos|as|nos|nas) (.+)',
)

_CONTACTS = {
    'contact_phone': (rf'qual(?: e)? o (?:telefone|numero de telefone) {_STORE}',),
    'contact_whatsapp': (rf'qual(?: e)? o (?:whatsapp|numero do whatsapp|zap) {_STORE}',),
    'contact_email': (rf'qual(?: e)? o (?:e-mail|email) {_STORE}',),
    'contact_all': (r'como posso falar com a loja', r'como (?:entro|entrar) em contato com a loja',
                    rf'quais(?: sao)? os contatos {_STORE}'),
}


def _normalize(message: str) -> str:
    text = ''.join(c for c in unicodedata.normalize('NFKD', message.casefold()) if not unicodedata.combining(c))
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^(?:ola|oi|bom dia|boa tarde|boa noite)[,! ]+', '', text)
    text = re.sub(r'^(?:por favor,? |pode me dizer |gostaria de saber )', '', text)
    text = re.sub(r'[?!.]+$', '', text).strip()
    return re.sub(r',? por favor$', '', text).strip()


def _intent(message: str) -> str | None:
    text = _normalize(message)
    if any(re.fullmatch(pattern, text) for pattern in _ADDRESS):
        return 'address'
    if any(re.fullmatch(pattern, text) for pattern in _GENERAL_HOURS):
        return 'hours'
    for intent, patterns in _CONTACTS.items():
        if any(re.fullmatch(pattern, text) for pattern in patterns):
            return intent
    for pattern in _DAY_QUESTIONS:
        match = re.fullmatch(pattern, text)
        if match:
            day = re.sub(r'-feira$', '', match[1])
            day = day[:-1] if day.endswith('s') else day
            if day in _DAYS:
                return 'hours_' + day
    return None


def _response(message: str, sources: list[dict], contacts: list[dict] | None = None) -> dict:
    return {'message': message, 'products': [], 'sources': sources, 'contacts': contacts or []}


@lru_cache(maxsize=2)
def _load(path: str, fingerprint: str, version: str) -> dict[str, dict]:
    pdf = Path(path)
    chunks = extract_chunks(pdf)
    responses: dict[str, dict] = {}
    addresses = [(chunk, match[1]) for chunk in chunks if chunk.section == '1.2'
                 for match in re.finditer(r'^Endereço\s+(.+)$', chunk.text, re.MULTILINE)]
    if len(addresses) == 1:
        chunk, address = addresses[0]
        source = {'id': chunk.id + '-address', 'section': chunk.section, 'title': 'Endereço da loja',
                  'pages': list(chunk.pages), 'text': address}
        responses['address'] = _response('Estamos na ' + address + '.', [source])
    hour_chunks = [chunk for chunk in chunks if chunk.section == '2']
    if len(hour_chunks) == 1:
        chunk = hour_chunks[0]
        weekday = re.search(r'^Segunda a Sexta-feira (\d{2}:\d{2} às \d{2}:\d{2})$', chunk.text, re.MULTILINE)
        saturday = re.search(r'^Sábado (\d{2}:\d{2} às \d{2}:\d{2})$', chunk.text, re.MULTILINE)
        closed = re.search(r'^Domingo e Feriados (Fechado)$', chunk.text, re.MULTILINE)
        if weekday and saturday and closed:
            source = {'id': chunk.id, 'section': chunk.section, 'title': chunk.title,
                      'pages': list(chunk.pages), 'text': chunk.text}
            exception = ' Em datas especiais, confirme eventuais alterações com a loja.'
            responses['hours'] = _response(f'O horário regular é: Segunda a sexta, {weekday[1]}; Sábado, {saturday[1]}; Domingo e feriados: {closed[1]}.' + exception, [source])
            labels = {'segunda': 'segunda-feira', 'terca': 'terça-feira', 'quarta': 'quarta-feira',
                      'quinta': 'quinta-feira', 'sexta': 'sexta-feira', 'sabado': 'sábado',
                      'domingo': 'domingo', 'feriado': 'feriados'}
            for day, group in _DAYS.items():
                hours = weekday[1] if group == 'weekday' else saturday[1] if group == 'saturday' else closed[1]
                holiday_note = f' Em feriados: {closed[1]}.' if group in ('weekday', 'saturday') else ''
                responses['hours_' + day] = _response(f'Horário regular de {labels[day]}: {hours}.' + holiday_note + exception, [source])
    contact_chunks = [chunk for chunk in chunks if chunk.section in ('capa', '1.2', '7')]
    contacts = contacts_from_chunks(contact_chunks)
    if contacts['status'] == 'found':
        lines = []
        for contact in contacts['channels']:
            label = 'WhatsApp de atendimento remoto' if contact['kind'] == 'remote' else 'Telefone / WhatsApp dos dados da empresa'
            lines.append(label + ': ' + contact['phone'] + '.')
        channel_note = ' O manual informa números diferentes para os canais; confirme o canal desejado.' if len({c['phone'] for c in contacts['channels']}) > 1 else ''
        phones = ' '.join(lines) + channel_note
        for kind, selected in (('contact_phone', 'store'), ('contact_whatsapp', 'remote'), ('contact_all', None)):
            channels = [c for c in contacts['channels'] if selected is None or c['kind'] == selected]
            if channels:
                responses[kind] = _response(phones, contacts['items'], channels)
        emails = contacts['emails']
        if emails:
            message = ' '.join('E-mail informado no manual (p. ' + ', '.join(str(page) for page in item['pages']) + '): ' + item['email'] + '.' for item in emails)
            if len({item['email'] for item in emails}) > 1:
                message += ' Há grafias diferentes no manual. Confirme o endereço de e-mail com a loja antes de usar.'
            responses['contact_email'] = _response(message, contacts['items'])
            if 'contact_all' in responses:
                responses['contact_all']['message'] += ' ' + message
    # A document modified while being parsed must not be published under its previous hash.
    if hashlib.sha256(pdf.read_bytes()).hexdigest() != fingerprint:
        raise RuntimeError('A fonte da loja foi alterada durante a consulta. Tente novamente.')
    return responses


def answer_faq(message: str, directory: Path) -> dict | None:
    intent = _intent(message)
    if intent is None:
        return None
    try:
        pdf = directory / 'políticas_da_loja.pdf'
        fingerprint = hashlib.sha256(pdf.read_bytes()).hexdigest()
        with _lock:
            response = _load(str(pdf.resolve()), fingerprint, 'faq-v1').get(intent)
        return deepcopy(response) if response is not None else None
    except RuntimeError:
        raise
    except Exception:
        # Never serve a previous version if the authoritative source cannot be read.
        raise RuntimeError('Não foi possível consultar as informações da loja.') from None
