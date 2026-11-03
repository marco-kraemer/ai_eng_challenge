"""Extract official contact channels exactly as recorded, without choosing away conflicts."""
import hashlib
import logging
import re
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from app.policies import extract_chunks

@lru_cache(maxsize=2)
def _chunks(path: str,fingerprint: str):return extract_chunks(Path(path))

class Contacts:
    def __init__(self,directory: Path):self.directory=directory

    def lookup(self,channel='all') -> dict:
        if channel not in ('all','remote','store'):return {'status':'invalid','channels':[],'items':[]}
        try:
            pdf=self.directory/'políticas_da_loja.pdf'
            sections=[chunk for chunk in _chunks(str(pdf.resolve()),hashlib.sha256(pdf.read_bytes()).hexdigest()) if chunk.section in ('capa','1.2','7')]
            return contacts_from_chunks(sections,channel)
        except Exception as exc:
            logging.getLogger(__name__).error('Contact extraction failed (%s)',type(exc).__name__)
            return {'status':'error','channels':[],'items':[]}


def contacts_from_chunks(sections, channel='all') -> dict:
    channels=[];emails=[]
    for chunk in sections:
        if chunk.section in ('1.2','7'):
            phone=re.search(r'\(\d{2}\)\s*\d{4,5}-\d{4}',chunk.text)
            if phone:channels.append({'kind':'remote' if chunk.section=='7' else 'store',
                'label':'WhatsApp de atendimento remoto' if chunk.section=='7' else 'Telefone / WhatsApp dos dados da empresa',
                'phone':phone[0],'pages':list(chunk.pages)})
        for email in re.findall(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',chunk.text):
            emails.append({'email':email,'pages':list(chunk.pages)})
    warnings=[]
    if len({c['phone'] for c in channels})>1:warnings.append('O manual informa telefones diferentes para dados da empresa e atendimento remoto. Identifique o canal, sem apresentar um número como universal.')
    if len({e['email'] for e in emails})>1:warnings.append('Há grafias diferentes de e-mail na capa e nos dados da empresa. Não corrija por adivinhação; confirme o endereço antes de usá-lo.')
    selected=[c for c in channels if channel=='all' or c['kind']==channel]
    items=[dict(asdict(chunk),pages=list(chunk.pages)) for chunk in sections]
    return {'status':'found' if selected else 'not_found','channels':selected,'emails':emails,'items':items,'warnings':warnings}
