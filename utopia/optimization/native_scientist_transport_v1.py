"""Explicit prospective scientist HTTP time allowances outside institution space.

Original native/role factories remain literal. Configure the existing SDK
client before scientific HTTP, without replacing its recorded/serialized
create callback or changing a completion payload. No retries or salvage.
"""
from importlib.metadata import version
import math
import json
from pathlib import Path
import sqlite3
import time

import httpx

from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest

SCHEMA = 'scienceutopia.native-scientist-transport.v1'
ENDPOINT = 'http://127.0.0.1:11434/v1'
PROTOCOL = 'research/protocols/campaigns/native-workflow-scientist-transport-v3.md'


def contract(*, read_seconds):
    return validate({'schema': SCHEMA, 'http_timeout_seconds': {
        'connect': 10, 'read': read_seconds, 'write': 30, 'pool': 30},
        'sdk_max_retries': 0, 'scientific_payload_changes': False,
        'unknown_completion_retry_or_salvage': False})


def validate(value):
    fields = {'schema', 'http_timeout_seconds', 'sdk_max_retries',
        'scientific_payload_changes', 'unknown_completion_retry_or_salvage'}
    if (not isinstance(value, dict) or set(value) != fields or value['schema'] != SCHEMA
            or type(value['sdk_max_retries']) is not int or value['sdk_max_retries'] != 0
            or value['scientific_payload_changes'] is not False
            or value['unknown_completion_retry_or_salvage'] is not False):
        raise ValueError('explicit zero-retry scientist transport contract required')
    times = value['http_timeout_seconds']
    if (not isinstance(times, dict) or set(times) != {'connect', 'read', 'write', 'pool'}
            or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
                or v > (3600 if k == 'read' else 60) for k, v in times.items())):
        raise ValueError('finite positive bounded scientist timeout components required')
    return clone(value)


def configure_existing_client(client, value):
    """Keep the same client and wrappers; SDK forwards this to HTTPX extensions.

    The installed SDK behavior is independently tested through MockTransport,
    including the actual emitted body and timeout extension, not a fake setter.
    """
    value = validate(value)
    if type(client.max_retries) is not int or client.max_retries != 0:
        raise ValueError('existing scientist SDK must already forbid retries')
    if str(client.base_url).rstrip('/') != ENDPOINT:
        raise ValueError('local original scientist endpoint required')
    before = client.chat.completions.create
    client.timeout = httpx.Timeout(**value['http_timeout_seconds'])
    if client.chat.completions.create != before:
        raise ValueError('scientist recording/serialization callback changed')
    actual = client.timeout.as_dict()
    if actual != value['http_timeout_seconds']:
        raise ValueError('actual scientist timeout differs from explicit contract')
    return {'http_timeout_seconds': actual, 'sdk_max_retries': client.max_retries,
        'client_object_replaced': False, 'completion_callback_replaced': False,
        'request_body_modified': False}


def record_value(value, *, source, system_fingerprint, seed, run_id, cache_binding, applied):
    return {'schema': SCHEMA + '.application', 'contract': validate(value),
        'source_commit': source, 'system_fingerprint': system_fingerprint,
        'world_seed': seed, 'run_id': run_id, 'cache_binding_sha256': digest(cache_binding),
        'model': cache_binding['model'], 'model_digest': cache_binding['model_revision'],
        'endpoint': ENDPOINT, 'sdk_package': 'openai', 'sdk_version': version('openai'),
        'applied': clone(applied), 'configured_before_scientific_generation': True,
        'scientific_generation_POSTs_by_configuration': 0,
        'original_empty_role_load_timeout_unchanged': True}


def require_record(record, value, *, source, system_fingerprint, seed, run_id, cache_binding):
    checked(record); expected = validate(value)
    applied = {'http_timeout_seconds': expected['http_timeout_seconds'], 'sdk_max_retries': 0,
        'client_object_replaced': False, 'completion_callback_replaced': False, 'request_body_modified': False}
    rebuilt = record_value(expected, source=source, system_fingerprint=system_fingerprint,
        seed=seed, run_id=run_id, cache_binding=cache_binding, applied=applied)
    if {k: v for k, v in record.items() if k != 'content_sha256'} != rebuilt:
        raise ValueError('original scientist transport application differs from plan/source/cache')
    return clone(record)


class LocalTransportBoundNativeFactory(LocalRoleBoundNativeFactory):
    """Unchanged original scientist world with a separately bound HTTP profile."""
    def __init__(self, *args, scientist_transport, **kwargs):
        self.scientist_transport = validate(scientist_transport)
        super().__init__(*args, **kwargs)

    def __call__(self, spec, seed, run_id):
        sim = super().__call__(spec, seed, run_id)
        try:
            applied = configure_existing_client(sim.llm.client, self.scientist_transport)
            value = record_value(self.scientist_transport, source=self.source_commit,
                system_fingerprint=spec.fingerprint, seed=seed, run_id=run_id,
                cache_binding=sim.llm.response_cache.binding, applied=applied)
            save(Path(self.directory) / run_id / 'scientist-transport.json', value)
        except BaseException:
            sim.llm.response_cache.close()
            raise
        return sim


def factory_for_profile(directory, plan, root):
    """Same original role factory arguments and safe-point budget, new transport."""
    factory = LocalTransportBoundNativeFactory(directory, Path(plan['data_cache']), years=4, corpus_years=4,
        designer_provider=plan['designer'], record_wire=True, record_code=True, maximum_http_attempts=1024,
        experiment_binding=plan['experiment'], inference_lock=root / 'inference.lock',
        world_conditions=plan['world']['world_conditions'], scientist_transport=plan['scientist_transport'])
    if factory.model_digest != plan['scientist']['model_digest'] or factory.corpus_sha256 != plan['scientist']['corpus_sha256']:
        raise ValueError('actual researcher/corpus differs from plan')
    def construct(spec, seed, run_id):
        sim = factory(spec, seed, run_id)
        if sim.llm.response_cache.stop is not sim.portable_stop:
            raise ValueError('native safe-point binding differs')
        sim.portable_stop.deadline = time.monotonic() + plan['budget']['world_wall_seconds']
        return sim
    return construct


def require_cell_transport(cell, plan, spec, *, seed, failed):
    """Validate the operator-owned profile without rerunning or repairing it."""
    path = cell / 'scientist-transport.json'; value = plan.get('scientist_transport')
    if value is None:
        if path.exists():
            raise ValueError('unplanned scientist transport application')
        return None
    if not path.exists():
        # Original role loading can fail before a client/cache is constructed.
        # Any dispatched scientist wire requires the profile's original record.
        wire = cell / 'wire-requests.jsonl'
        if not failed or (wire.exists() and wire.stat().st_size):
            raise ValueError('scientist transport application missing after dispatch')
        return {'status': 'not-configured-before-scientific-dispatch', 'scientific_POSTs': 0}
    with sqlite3.connect((cell / 'replies/responses.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
        bindings = db.execute('SELECT binding FROM metadata').fetchall()
    if len(bindings) != 1:
        raise ValueError('one original cache binding required for scientist transport')
    return require_record(json.loads(path.read_text()), value, source=plan['source_commit'],
        system_fingerprint=spec.fingerprint, seed=seed, run_id=cell.name, cache_binding=json.loads(bindings[0][0]))
