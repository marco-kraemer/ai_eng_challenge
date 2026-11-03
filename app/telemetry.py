"""Request-local, content-free traces; explicit bounded LangSmith export."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import lru_cache, wraps
import hashlib
import logging
import os
import re
import time
from uuid import uuid4

from langsmith import Client, tracing_context
from urllib3.util.retry import Retry

_active: ContextVar = ContextVar('emporio_turn', default=None)
_parent: ContextVar = ContextVar('emporio_span', default=None)
_events: ContextVar = ContextVar('emporio_events', default=None)
_cancel: ContextVar = ContextVar('emporio_cancel', default=None)
SAFE = {'ls_model_name', 'ls_provider', 'thread_id', 'intent', 'category_id', 'category_ids', 'max_price', 'min_price', 'product_ids',
        'status', 'model', 'input_tokens', 'output_tokens', 'cached_tokens', 'total_tokens', 'cost_usd',
        'known_cost_usd', 'first_token_ms', 'faq_hit', 'duration_ms', 'llm_calls', 'usage_missing', 'product_count', 'source_count', 'tool_count', 'cache_hit', 'provider'}


def safe_metadata(values):
    result: dict = {}
    for key, value in values.items():
        if key not in SAFE:
            continue
        if isinstance(value, (bool, int, float)) or value is None:
            result[key] = value
        elif isinstance(value, list) and all(type(v) is int for v in value):
            result[key] = value[:32]
        elif isinstance(value, str) and len(value) <= 100 and re.fullmatch(r'[\w./:-]+', value) and not value.startswith('sk-'):
            result[key] = value
    return result


@lru_cache(maxsize=2)
def smith_client(key, endpoint, workspace):
    return Client(api_key=key, api_url=endpoint, workspace_id=workspace or None,
                  timeout_ms=1200, retry_config=Retry(total=0), auto_batch_tracing=False,
                  hide_inputs=True, hide_outputs=True, hide_metadata=safe_metadata, omit_traced_runtime_info=True)


def export_runs(records):
    key = os.getenv('LANGSMITH_API_KEY')
    if not key or os.getenv('EMPORIO_TRACING', 'true').lower() != 'true':
        return
    endpoint = os.getenv('LANGSMITH_ENDPOINT', 'https://api.smith.langchain.com')
    if endpoint not in ('https://api.smith.langchain.com', 'https://eu.api.smith.langchain.com'):
        raise ValueError('Unsupported LangSmith endpoint')
    smith_client(key, endpoint, os.getenv('LANGSMITH_WORKSPACE_ID', '')).batch_ingest_runs(create=records)


def current_turn():
    return _active.get()


def streaming_enabled():
    return _events.get() is not None


def first_token():
    trace = current_turn()
    record = _parent.get()
    if trace and record and not record.get('events'):
        record['events'] = [{'name': 'new_token', 'time': datetime.now(timezone.utc)}]
        trace.metrics.setdefault('first_token_ms', round((time.monotonic() - trace.started) * 1000, 2))


class StreamCancelled(RuntimeError):
    pass


def raise_if_cancelled():
    flag = _cancel.get()
    if flag is not None and flag.is_set():
        raise StreamCancelled('Request cancelled')


def emit(kind, **payload):
    raise_if_cancelled()
    callback = _events.get()
    if callback:
        callback({'type': kind, **payload})


@contextmanager
def event_sink(callback, cancelled=None):
    token = _events.set(callback)
    cancel_token = _cancel.set(cancelled)
    try:
        yield
    finally:
        _events.reset(token)
        _cancel.reset(cancel_token)


class Turn:
    def __init__(self, session):
        self.id = str(uuid4())
        self.thread_id = hashlib.sha256(session.encode()).hexdigest()[:24]
        self.records: list[dict] = []
        self.status = 'ok'
        self.started = time.monotonic()
        self.metrics: dict = {'llm_calls': 0, 'usage_missing': 0, 'cost_usd': 0.0, 'known_cost_usd': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'cached_tokens': 0}

    def new_record(self, name, kind, metadata):
        now = datetime.now(timezone.utc)
        parent = _parent.get()
        identity = self.id if not self.records else str(uuid4())
        order = now.strftime('%Y%m%dT%H%M%S%fZ') + identity
        record = {'id': identity, 'trace_id': self.id, 'name': name, 'run_type': kind,
                  'session_name': os.getenv('LANGSMITH_PROJECT', 'emporio-musica'),
                  'start_time': now, 'dotted_order': parent['dotted_order'] + '.' + order if parent else order,
                  'inputs': {}, 'outputs': {}, 'extra': {'metadata': safe_metadata({'thread_id': self.thread_id, **metadata})}}
        if parent:
            record['parent_run_id'] = parent['id']
        self.records.append(record)
        return record


@contextmanager
def span(name, kind='chain', **metadata):
    trace = current_turn()
    if trace is None:
        yield None
        return
    record = trace.new_record(name, kind, metadata)
    parent = _parent.set(record)
    start = time.monotonic()
    try:
        emit('progress', stage=name)
        yield record
    except BaseException as error:
        record['error'] = type(error).__name__
        raise
    finally:
        record['end_time'] = datetime.now(timezone.utc)
        record['extra']['metadata']['duration_ms'] = round((time.monotonic() - start) * 1000, 2)
        _parent.reset(parent)


@contextmanager
def turn(session):
    trace = Turn(session)
    token = _active.set(trace)
    try:
        # Automatic LangChain tracing could include raw prompts and customer text.
        # Only our explicit sanitized records are exported.
        with tracing_context(enabled=False), span('customer_turn'):
            try:
                yield trace
            except BaseException:
                trace.status = 'error'
                raise
    finally:
        trace.records[0]['extra']['metadata'].update(safe_metadata({**trace.metrics, 'status': trace.status}))
        _active.reset(token)
        logging.getLogger('emporio.metrics').info('%s', __import__('json').dumps({'trace_id': trace.id, **safe_metadata(trace.records[0]['extra']['metadata'])}))
        try:
            export_runs(trace.records)
        except Exception:
            logging.getLogger(__name__).warning('Trace export unavailable')


def observed(name, function):
    @wraps(function)
    def execute(*args, **kwargs):
        with span(name) as record:
            result = function(*args, **kwargs)
            if name == 'faq' and isinstance(result, dict) and result.get('result'):
                current_turn().metrics['faq_hit'] = True
            if record and isinstance(result, dict):
                record['extra']['metadata'].update(safe_metadata(result))
            return result
    return execute


def traced_request(function):
    @wraps(function)
    def execute(*args, **kwargs):
        body = next(iter(args), None) or next(iter(kwargs.values()), None)
        values = body.model_dump() if body is not None and hasattr(body, 'model_dump') else {}
        with turn(values.get('conversation_id') or str(uuid4())) as trace:
            with span(function.__name__, 'tool', **safe_metadata(values)):
                result = function(*args, **kwargs)
            if isinstance(result, dict):
                if result.get('conversation_id'):
                    thread = hashlib.sha256(result['conversation_id'].encode()).hexdigest()[:24]
                    for record in trace.records:
                        record['extra']['metadata']['thread_id'] = thread
                trace.metrics.update({'product_count': len(result.get('products', [])), 'source_count': len(result.get('sources', []))})
                result['trace_id'] = trace.id
            return result
    return execute
