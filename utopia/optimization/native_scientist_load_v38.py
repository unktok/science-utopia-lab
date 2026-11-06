"""Explicit bounded empty-prompt scientist loading, never scientific inference."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time

from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic, decode_json
from .native_search_v14 import validate_provider_binding

SCHEMA = 'scienceutopia.explicit-scientist-load.v38'
ENDPOINT = 'http://127.0.0.1:11434/api/generate'
SCIENTIST_DIGEST = '500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41'
TIMEOUT = (10, 120)


def payload_for(provider):
    validate_provider_binding(provider)
    if provider['model_digest'] != SCIENTIST_DIGEST:
        raise ValueError('explicit load must retain the original researcher weights')
    return {'model': provider['model'], 'prompt': '', 'stream': False, 'think': False,
        'options': {'num_ctx': 40960}, 'keep_alive': '5m'}


def _wire(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _valid(record):
    body = record.get('response_payload')
    return ('error' not in record and record.get('http_status') == 200 and isinstance(body, dict)
        and body.get('model') == record['provider']['model'] and body.get('done') is True
        and body.get('done_reason') == 'load' and not body.get('response') and not body.get('thinking')
        and not body.get('error') and all(type(body[k]) is int and body[k] == 0
            for k in ('eval_count','prompt_eval_count') if k in body))


def load_scientist(path, *, provider, purpose, session=None):
    path = Path(path); started = path.with_suffix('.started.json')
    if path.exists() or started.exists():
        raise ValueError('explicit load already dispatched; no overwrite or hidden retry')
    payload = payload_for(provider); wire = _wire(payload)
    intent = {'schema': SCHEMA + '.intent', 'provider': clone(provider), 'purpose': purpose,
        'endpoint': ENDPOINT, 'request_payload': payload, 'request_wire_utf8': wire,
        'request_wire_sha256': hashlib.sha256(wire.encode()).hexdigest(),
        'http_timeout_seconds': list(TIMEOUT), 'network_retries': 0,
        'started_utc': datetime.now(timezone.utc).isoformat()}
    intent['content_sha256'] = digest(intent)
    write_json_atomic(started, intent, sort_keys=True, allow_nan=False)
    if session is None:
        import requests
        session = requests.Session(); session.trust_env = False
    begin = time.monotonic()
    record = {'schema': SCHEMA, 'provider': clone(provider), 'purpose': purpose,
        'intent_sha256': intent['content_sha256']}
    try:
        response = session.post(ENDPOINT, data=wire.encode(), headers={'Content-Type': 'application/json'}, timeout=TIMEOUT)
        record.update(http_status=response.status_code, raw_http_response=response.text)
        response.raise_for_status()
        record['response_payload'] = decode_json(response.text, strict=True, finite_floats=True)
    except Exception as error:
        record['error'] = type(error).__name__ + ': ' + str(error)
    record.update(elapsed_seconds=time.monotonic() - begin,
        ended_utc=datetime.now(timezone.utc).isoformat())
    record['valid_empty_prompt_load'] = _valid(record)
    record['content_sha256'] = digest(record)
    write_json_atomic(path, record, sort_keys=True, allow_nan=False)
    if not record['valid_empty_prompt_load']:
        raise ValueError('explicit empty-prompt load failed/unknown; no retry or scientific loss')
    return record


def replay_load(intent, record, *, provider, purpose):
    wire = _wire(payload_for(provider))
    if (intent.get('schema') != SCHEMA + '.intent' or intent.get('provider') != provider
            or intent.get('purpose') != purpose or intent.get('endpoint') != ENDPOINT
            or intent.get('request_payload') != payload_for(provider) or intent.get('request_wire_utf8') != wire
            or intent.get('request_wire_sha256') != hashlib.sha256(wire.encode()).hexdigest()
            or intent.get('http_timeout_seconds') != list(TIMEOUT) or intent.get('network_retries') != 0
            or intent.get('content_sha256') != digest({k:v for k,v in intent.items() if k!='content_sha256'})):
        raise ValueError('explicit load intent/source/provider differs')
    if record is None:
        return {'status': 'dispatched-response-unknown', 'empty_prompt_load_confirmed': False}
    if (record.get('schema') != SCHEMA or record.get('provider') != provider or record.get('purpose') != purpose
            or record.get('intent_sha256') != intent['content_sha256']
            or record.get('content_sha256') != digest({k:v for k,v in record.items() if k!='content_sha256'})):
        raise ValueError('explicit load completion binding differs')
    if 'response_payload' in record and decode_json(record['raw_http_response'], strict=True, finite_floats=True) != record['response_payload']:
        raise ValueError('explicit load raw response differs')
    seconds = record.get('elapsed_seconds')
    if (record.get('valid_empty_prompt_load') is not _valid(record)
            or type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<0):
        raise ValueError('explicit load outcome/cost differs')
    return {'status':'completed-load' if _valid(record) else 'failed-or-unknown-load',
        'empty_prompt_load_confirmed': _valid(record)}
