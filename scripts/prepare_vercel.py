"""Prepare offline RAG assets during build, without LLM credentials or Redis access."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.embeddings import LocalEncoder
from app.policies import PolicyIndex
from huggingface_hub import snapshot_download


def prepare(source: Path | None = None):
    bundle = ROOT / '.rag-bundle'
    snapshot = snapshot_download(
        repo_id='Xenova/multilingual-e5-small', revision='761b726dd34fb83930e26aab4e9ac3899aa1fa78',
        cache_dir=str(source / 'embeddings' if source is not None else ROOT / '.cache-build/embeddings'),
        local_files_only=source is not None,
        allow_patterns=['config.json', 'tokenizer.json', 'tokenizer_config.json',
                        'special_tokens_map.json', 'onnx/model_quantized.onnx'])
    # Flatten only the model snapshot: no duplicated HF blobs or cache symlinks in the function.
    shutil.copytree(snapshot, bundle / 'embeddings/model', dirs_exist_ok=True)
    encoder = LocalEncoder(str(bundle / 'embeddings'))
    pdf = ROOT / 'data/políticas_da_loja.pdf'
    index = PolicyIndex(pdf, bundle / 'policies', encoder)
    manifest = {'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
                'model': encoder.model_id, 'chunks': len(index.chunks)}
    (bundle / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    size = sum(path.stat().st_size for path in bundle.rglob('*') if path.is_file())
    print(f'RAG ready: {len(index.chunks)} chunks; {size / 1024**2:.1f} MiB. No LLM calls.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-cache', type=Path, help='Reuse a local embedding cache while validating the build.')
    prepare(parser.parse_args().from_cache)
