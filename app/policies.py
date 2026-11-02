"""Local, page-preserving PDF retrieval with BM25 + normalized dense vectors."""
import hashlib
import re
import sqlite3
import threading
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from pypdf import PdfReader

MAX_TEXT = 1800
STOPWORDS = set('a o as os de da do das dos em no na nos nas um uma que qual quais quando como por para com se e ou ao aos pelo pela eu me meu minha voce voces loja emporio musica gostaria saber tem ter posso pode quero preciso sobre isso esse essa esta estaos'.split())

@dataclass(frozen=True)
class Chunk:
    id: str
    section: str
    title: str
    pages: tuple[int, ...]
    text: str


def extract_chunks(pdf: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    section, title = 'capa', 'Identificação e contato na capa'
    lines: list[str] = []
    pages: list[int] = []

    def flush():
        if len(lines) < 2:
            return
        # Sections in this manual fit this limit; longer revisions split at line boundaries.
        pieces: list[str] = []
        current = ''
        for line in lines:
            for start in range(0, len(line), MAX_TEXT):
                part = line[start:start + MAX_TEXT]
                if len(current) + len(part) + 1 > MAX_TEXT:
                    pieces.append(current)
                    current = ''
                current = (current + '\n' + part).strip()
        if current:
            pieces.append(current)
        for n, text in enumerate(pieces):
            chunks.append(Chunk(f's{section}-{n}', section, title, tuple(pages), text))

    for page_number, page in enumerate(PdfReader(pdf).pages, 1):
        for line in (page.extract_text(extraction_mode='layout') or '').splitlines():
            line = re.sub(r'[ \t]+', ' ', line).strip()
            if not line or line.startswith('Empório da Música Manual') or re.fullmatch(r'Página\s+\d+', line):
                continue
            heading = re.match(r'^(\d+(?:\.\d+)?)\.?\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ].+)$', line)
            if heading and ':' not in heading[2]:
                flush()
                section, title = heading[1], heading[2]
                lines, pages = [], []
            if page_number not in pages:
                pages.append(page_number)
            lines.append(line)
    flush()
    if not chunks:
        raise ValueError('PDF sem texto extraível.')
    return chunks


class Encoder(Protocol):
    model_id: str
    def passages(self, texts: list[str]) -> np.ndarray: ...
    def query(self, text: str) -> np.ndarray: ...


def unit(vectors: np.ndarray) -> np.ndarray:
    return vectors / np.maximum(np.linalg.norm(vectors, axis=-1, keepdims=True), 1e-12)


def terms(text: str) -> list[str]:
    normalized = ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))
    return sorted({t for t in re.findall(r'[a-z0-9]+', normalized) if len(t) > 1 and t not in STOPWORDS})


class PolicyIndex:
    def __init__(self, pdf: Path, cache: Path, encoder: Encoder):
        self.chunks = extract_chunks(pdf)
        self.encoder = encoder
        self.lock = threading.Lock()
        digest = hashlib.sha256(pdf.read_bytes() + encoder.model_id.encode() + b'chunks-v2').hexdigest()
        cache.mkdir(parents=True, exist_ok=True)
        path = cache / f'{digest}.npy'
        try:
            matrix = np.load(path, allow_pickle=False)
            if matrix.ndim != 2 or matrix.shape[0] != len(self.chunks) or not np.isfinite(matrix).all():
                raise ValueError('Invalid index')
        except (OSError, ValueError):
            matrix = encoder.passages([f'{c.title}\n{c.text}' for c in self.chunks])
            # Write and replace atomically, including when multiple processes build the index.
            import tempfile
            with tempfile.NamedTemporaryFile(dir=cache, suffix='.npy', delete=False) as temp:
                np.save(temp, matrix, allow_pickle=False)
                temp_path = Path(temp.name)
            temp_path.replace(path)
        self.matrix = unit(matrix)
        self.db = sqlite3.connect(':memory:', check_same_thread=False)
        self.db.execute("CREATE VIRTUAL TABLE passages USING fts5(title, body, tokenize='unicode61 remove_diacritics 2')")
        self.db.executemany('INSERT INTO passages(rowid, title, body) VALUES (?, ?, ?)',
                            [(i + 1, c.title, c.text) for i, c in enumerate(self.chunks)])

    def search(self, query: str, limit: int = 3, mode: str = 'hybrid') -> dict:
        if (not isinstance(query, str) or not query.strip() or len(query) > 500 or
                type(limit) is not int or not 1 <= limit <= 3 or mode not in ('hybrid', 'lexical', 'semantic')):
            return {'status': 'invalid', 'items': [], 'warnings': []}
        rankings: list[tuple[list[int], float]] = []
        if mode != 'semantic':
            tokens = terms(query)
            # Small lexical synonym sets complement the learned semantic model.
            synonyms = {
                'abrem': ['horario', 'funcionamento'], 'abre': ['horario', 'funcionamento'],
                'abrir': ['horario', 'funcionamento'], 'abertura': ['horario', 'funcionamento'],
                'fecham': ['horario', 'funcionamento'], 'fecha': ['horario', 'funcionamento'],
                'horas': ['horario'], 'parcelar': ['parcelamento'],
                'arrependi': ['arrependimento'], 'devolver': ['devolucao'],
                'email': ['e-mail'],
            }
            tokens = sorted(set(tokens + [word for t in tokens for word in synonyms.get(t, [])]))
            if tokens:
                match = ' OR '.join('"' + t + '"' for t in tokens)
                with self.lock:
                    lexical = self.db.execute('SELECT rowid FROM passages WHERE passages MATCH ? ORDER BY bm25(passages, 2.0, 1.0) LIMIT 6', (match,)).fetchall()
                rankings.append(([row[0] - 1 for row in lexical], 1.25))
        if mode != 'lexical':
            scores = self.matrix @ unit(self.encoder.query(query))
            rankings.append(([int(i) for i in np.argsort(-scores)[:6] if scores[i] >= 0.85], 1.0))
        # Reciprocal rank fusion avoids treating cosine and BM25 as comparable scores.
        fused: dict[int, float] = {}
        for ranking, weight in rankings:
            for position, i in enumerate(ranking, 1):
                fused[i] = fused.get(i, 0.0) + weight / (60 + position)
        ranked = sorted(fused, key=lambda i: (-fused[i], i))
        selected = ranked[:limit]
        warnings = []
        groups = [({'3', '3.1'}, 'O quadro de pagamento e as regras de parcelamento divergem nos mínimos. Apresente a divergência e peça confirmação à loja; não escolha uma condição por conta própria.'),
                  ({'1.2', '7'}, 'O manual lista contatos diferentes nos dados da empresa e no atendimento WhatsApp. Identifique o canal e a página; não apresente um único número como universal.')]
        # Preserve competing evidence rather than hide a contradiction behind ranking.
        for sections, warning in groups:
            if selected and self.chunks[selected[0]].section in sections:
                required = [i for i, c in enumerate(self.chunks) if c.section in sections]
                if limit >= len(required):
                    selected = (required + [i for i in selected if i not in required])[:limit]
                warnings.append(warning)
        if selected and self.chunks[selected[0]].section in {'4.1', '4.2', '4.3'}:
            exceptions = next((i for i, c in enumerate(self.chunks) if c.section == '4.4'), None)
            if exceptions is not None and exceptions not in selected and limit > 1:
                selected = selected[:limit - 1] + [exceptions]
        items = []
        remaining = 5000
        for i in selected:
            item = asdict(self.chunks[i])
            item['pages'] = list(item['pages'])
            if len(item['text']) > remaining:
                break
            remaining -= len(item['text'])
            items.append(item)
        return {'status': 'found' if items else 'not_found', 'items': items,
                'warnings': warnings, 'method': mode}
