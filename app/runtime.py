"""Deployment-aware storage and filesystem configuration; no network on import."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import threading

from app.conversations import ConversationStore
from app.limits import RateLimiter
from app.redis_state import RedisREST, RedisConversationStore, RedisRateLimiter, RedisCapacity

ROOT = Path(__file__).resolve().parent.parent


def build_backends() -> tuple[ConversationStore | RedisConversationStore, RateLimiter | RedisRateLimiter, threading.BoundedSemaphore | RedisCapacity]:
    url = os.getenv('UPSTASH_REDIS_REST_URL', '')
    token = os.getenv('UPSTASH_REDIS_REST_TOKEN', '')
    if not url and not token and os.getenv('VERCEL') != '1':
        return ConversationStore(), RateLimiter(), threading.BoundedSemaphore(4)
    if not url or not token:
        raise RuntimeError('Configure UPSTASH_REDIS_REST_URL e UPSTASH_REDIS_REST_TOKEN para publicar na Vercel.')
    environment = os.getenv('VERCEL_ENV', 'development')
    branch = hashlib.sha256(os.getenv('VERCEL_GIT_COMMIT_REF', 'local').encode()).hexdigest()[:12]
    namespace = os.getenv('STATE_NAMESPACE') or ('emporio-production' if environment == 'production' else f'emporio-{environment}-{branch}')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', namespace):
        raise RuntimeError('STATE_NAMESPACE deve ter até 80 letras, números, hífens ou sublinhados.')
    redis = RedisREST(url, token)
    return RedisConversationStore(redis, namespace), RedisRateLimiter(redis, namespace), RedisCapacity(redis, namespace)


def policy_cache_dir() -> Path:
    default = '/tmp/emporio-policy-cache' if os.getenv('VERCEL') == '1' else str(ROOT / '.cache')
    return Path(os.getenv('POLICY_CACHE_DIR') or default)


def seed_policy_cache(bundle: Path, target: Path):
    if not (bundle / 'embeddings').is_dir() or not (bundle / 'policies').is_dir():
        raise RuntimeError('Cache de RAG ausente. Execute o build de preparação da Vercel.')
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle, target, dirs_exist_ok=True)
