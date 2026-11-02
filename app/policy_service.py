"""Reuse the local model/index between requests; invalidate when the PDF changes."""
import hashlib
import os
import threading
from functools import lru_cache
from pathlib import Path
from app.policies import PolicyIndex

ROOT = Path(__file__).resolve().parent.parent
_build_lock = threading.Lock()

@lru_cache(maxsize=1)
def _encoder():
    from app.embeddings import LocalEncoder
    return LocalEncoder(str(Path(os.getenv('POLICY_CACHE_DIR', ROOT / '.cache')) / 'embeddings'))

@lru_cache(maxsize=2)
def _build(pdf: str, fingerprint: str) -> PolicyIndex:
    return PolicyIndex(Path(pdf), Path(os.getenv('POLICY_CACHE_DIR', ROOT / '.cache')) / 'policies', _encoder())

def get_policy_index(directory: Path) -> PolicyIndex:
    pdf = directory / 'políticas_da_loja.pdf'
    fingerprint = hashlib.sha256(pdf.read_bytes()).hexdigest()
    with _build_lock:
        return _build(str(pdf.resolve()), fingerprint)
