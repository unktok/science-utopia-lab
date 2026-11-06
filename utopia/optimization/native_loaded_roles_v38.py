"""Read-only context evidence plus separately journalled explicit scientist loads."""
from datetime import datetime, timezone
import json
import math
import re
import time
from pathlib import Path

from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic
from .native_designer_roles_v38 import validate_designer_binding
from .native_factory import LocalQwenNativeFactory
from .native_search_v14 import validate_provider_binding

SCHEMA = 'scienceutopia.loaded-role-context.v38'
ENDPOINT = 'http://127.0.0.1:11434/api/ps'
SCIENTIST_DIGEST = '500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41'
CONTEXT_TOKENS = 40960


def _validate_expected(expected):
    if not isinstance(expected, dict) or set(expected) not in ({'scientist'}, {'designer'}, {'scientist', 'designer'}):
        raise ValueError('explicit nonempty known role bindings required')
    if set(expected) == {'designer'}:
        validate_designer_binding(expected['designer'])
        return
    validate_provider_binding(expected['scientist'])
    if expected['scientist']['model_digest'] != SCIENTIST_DIGEST:
        raise ValueError('loaded-context scientist digest differs from the fixed original model')
    if 'designer' in expected:
        validate_designer_binding(expected['designer'], scientist_binding=expected['scientist'])


def _checks(payload, expected):
    models = payload.get('models') if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return {role: False for role in expected}
    return {role: len([m for m in models if isinstance(m, dict)
        and m.get('name') == binding['model'] and m.get('digest') == binding['model_digest']
        and type(m.get('context_length')) is int and m['context_length'] == CONTEXT_TOKENS]) == 1
        for role, binding in expected.items()}


def record_loaded_context(path, *, expected, purpose, session=None):
    """One metadata GET, immutable receipt, then fail closed on absent/unknown."""
    path = Path(path)
    _validate_expected(expected)
    if path.exists():
        raise ValueError('loaded-context evidence already exists; never overwrite/reuse a fresh gate')
    if session is None:
        import requests
        session = requests.Session(); session.trust_env = False
    begin = time.monotonic()
    record = {'schema': SCHEMA, 'endpoint': ENDPOINT, 'purpose': purpose,
        'observed_utc': datetime.now(timezone.utc).isoformat(),
        'expected': clone(expected), 'context_tokens': CONTEXT_TOKENS,
        'new_generation_POSTs': 0, 'automatic_loads': 0, 'metadata_GET_attempts': 1}
    try:
        response = session.get(ENDPOINT, timeout=10)
        record.update(http_status=response.status_code, raw_http_response=response.text)
        response.raise_for_status()
        record['response_payload'] = json.loads(response.text)
    except Exception as error:
        record['error'] = type(error).__name__ + ': ' + str(error)
    record.update(elapsed_seconds=time.monotonic() - begin,
        checks=_checks(record.get('response_payload'), expected))
    record['valid'] = 'error' not in record and record.get('http_status') == 200 and all(record['checks'].values())
    record['content_sha256'] = digest(record)
    write_json_atomic(path, record, sort_keys=True, allow_nan=False)
    if not record['valid']:
        raise ValueError('loaded role/context is absent, wrong or unknown; no automatic load/fallback: ' + str(record['checks']))
    return record


def replay_loaded_context(record, *, expected, purpose):
    _validate_expected(expected)
    core = {k: v for k, v in record.items() if k != 'content_sha256'}
    if (record.get('content_sha256') != digest(core) or record.get('schema') != SCHEMA
            or record.get('endpoint') != ENDPOINT or record.get('purpose') != purpose
            or record.get('expected') != expected or record.get('context_tokens') != CONTEXT_TOKENS
            or any(type(record.get(k)) is not int or record[k] != v for k, v in
                [('new_generation_POSTs', 0), ('automatic_loads', 0), ('metadata_GET_attempts', 1)])):
        raise ValueError('loaded-context receipt binding/hash differs')
    if 'response_payload' in record and json.loads(record['raw_http_response']) != record['response_payload']:
        raise ValueError('loaded-context raw metadata differs')
    checks = _checks(record.get('response_payload'), expected)
    valid = 'error' not in record and record.get('http_status') == 200 and all(checks.values())
    seconds = record.get('elapsed_seconds')
    if (record.get('checks') != checks or record.get('valid') is not valid
            or type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0):
        raise ValueError('loaded-context observation outcome/cost differs')
    return valid


class LocalRoleBoundNativeFactory(LocalQwenNativeFactory):
    """Explicitly load the original context, then delegate unchanged science.

    Designer and scientist inference is serialized. Once a world starts, our
    scheduler runs no other-model generation until that world ends. This does
    not assert immunity to unrelated external backend reconfiguration.
    """
    def __init__(self, *args, designer_provider, **kwargs):
        if kwargs.get('model', 'qwen3:8b') != 'qwen3:8b':
            raise ValueError('researchers must stay Qwen3-8B')
        super().__init__(*args, **kwargs)
        if self.model_digest != SCIENTIST_DIGEST:
            raise ValueError('researcher digest differs from the fixed original model')
        self.scientist_provider = {k: clone(getattr(self, k)) for k in
            ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'corpus_years')}
        self.scientist_provider['image_id'] = designer_provider['image_id']
        validate_designer_binding(designer_provider, scientist_binding=self.scientist_provider)

    def __call__(self, spec, seed, run_id):
        if not isinstance(run_id, str) or not re.fullmatch('[a-zA-Z0-9_-]+', run_id):
            raise ValueError('native run id must be a safe single directory name')
        # Unique observation per construction/resume, never rewrite an old gate.
        root = self.directory / run_id
        from .native_scientist_load_v38 import load_scientist
        index = len(list(root.glob('role-load-*.started.json')))
        load_scientist(root / f'role-load-{index:03d}.json', provider=self.scientist_provider,
            purpose='before-native-world:' + run_id)
        record_loaded_context(root / f'loaded-role-context-{index:03d}.json',
            expected={'scientist': self.scientist_provider}, purpose='before-native-world:' + run_id)
        return super().__call__(spec, seed, run_id)
