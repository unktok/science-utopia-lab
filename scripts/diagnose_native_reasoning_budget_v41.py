#!/usr/bin/env python3
"""Two separately charged thinking-mode probes; never applies generated actions."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diagnose_native_json_history_v40 as archive
from utopia.optimization.native_designer_decoding_v24 import designer_payload
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_designer_tools_v25 import action_from_body
from utopia.optimization.native_designer_wire import post, wire_record
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_search_generator_v14 import _strict_json
from utopia.optimization.native_staged_author_v15 import build_conversation, call_task, PLAN_ACTION_SCHEMA
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic
from jsonschema import Draft202012Validator

SCHEMA = 'scienceutopia.reasoning-budget-diagnostic.v41'
SEARCH = 'search-adcc272ac49346d7a9f14957d28ee938'
GENERATION = '556d77cfc1696e8eb7a19ec8d892d75d2337ec16273aed5328778f79649fec74'
MODES = (True, False)  # Explicit replicates, not retries/fallbacks after a failure.


def plan(raw, *, audits, writer_ended, provider):
    evidence = archive.closure(raw, audits, writer_ended)
    original = archive.read(raw / 'plan.json')
    if provider != original['designer_provider_binding']:
        raise ValueError('original designer binding differs')
    cell = raw / 'queue' / SEARCH / 'authoring' / ('generation-' + GENERATION)
    binding = archive.hashed(archive.read(cell / 'request.json'), 'binding_sha256')
    started = archive.read(cell / 'step-00.started.json')
    completed = archive.hashed(archive.read(cell / 'step-00.completed.json'))
    old = completed['model_reply']['transport']
    messages = build_conversation(started['prompt'], call_task(0, 8), native_tools=True)
    payload = designer_payload('staged-v15', provider, messages,
        ('native-staged-designer-v15', binding['binding_sha256'], 0),
        max_tokens=8192, temperature=.6, role='planner')
    body = old['response_payload']
    if (binding['provider_binding'] != provider or binding['request_sha256'] != GENERATION
            or digest(binding['request']) != GENERATION
            or started['prompt_sha256'] != digest(started['prompt'])
            or started['response_schema'] != PLAN_ACTION_SCHEMA
            or completed['started_file_sha256'] != hashlib.sha256((cell / 'step-00.started.json').read_bytes()).hexdigest()
            or old['request_payload'] != payload
            or any(old.get(k) != v for k, v in wire_record(payload, PLAN_ACTION_SCHEMA).items())
            or completed['status'] != 'invalid-response' or body.get('done_reason') != 'length'
            or body.get('eval_count') != 8192 or body['message'].get('content') != ''
            or not body['message'].get('thinking')):
        raise ValueError('exact original reasoning-only length witness differs')
    result = {'schema': SCHEMA + '.plan', 'source_commit': pinned_revision(ROOT),
        'runtime': runtime_binding(), 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'raw_root': str(raw), 'closure': evidence, 'provider': clone(provider),
        'backend': old['preflight']['backend'], 'payload': payload,
        'calls': [{'ordinal': i, 'think': mode} for i, mode in enumerate(MODES)],
        'maximum_POSTs': 2, 'maximum_metadata_GETs': 6, 'http_timeout_seconds': [10, 900],
        'network_retries': 0, 'native_worlds': 0, 'actions_applied': 0,
        'scope': 'Same original planner input/seed/options; only explicit think flag varies. No execution/readiness or efficacy claim.'}
    result['content_sha256'] = digest(result)
    return result


def dispatch(session, provider, payload):
    transport = {'request_payload': clone(payload), 'network_retries': 0}
    result = {'transport': transport, 'costs': {'prompt_eval_count': None, 'eval_count': None},
        'complete_envelope': False, 'plan_schema_valid': False, 'action_applied': False}
    begin = time.monotonic()
    try:
        response = post(session, 'http://127.0.0.1:11434/api/chat', payload,
            PLAN_ACTION_SCHEMA, transport, timeout=(10, 900))
        transport.update(http_status=response.status_code, raw_http_response=response.text)
        body = _strict_json(response.text)
        transport['response_payload'] = body
        result['costs'] = {k: body.get(k) for k in result['costs']}
        message = body.get('message') or {}
        result.update(thinking_characters=len(message.get('thinking', '')),
            content_characters=len(message.get('content', '')),
            provider_matches=body.get('model') == provider['model'],
            complete_envelope=body.get('done') is True and body.get('done_reason') != 'length')
        response.raise_for_status()
        action = action_from_body(body)
        Draft202012Validator(PLAN_ACTION_SCHEMA).validate(action)
        result.update(parsed_action=action, plan_schema_valid=True)
    except BaseException as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error)[:4000]}
        result['interrupted'] = not isinstance(error, Exception)
    transport['elapsed_seconds'] = time.monotonic() - begin
    result.update(ended_utc=archive.utc(), missing_cost_not_imputed=True,
        technical_success=transport.get('http_status') == 200 and result['complete_envelope']
            and result.get('provider_matches') is True and result['plan_schema_valid'])
    return result


def run(value, output, *, session=None):
    archive.hashed(value)
    if (value['calls'] != [{'ordinal': i, 'think': mode} for i, mode in enumerate(MODES)]
            or value['maximum_POSTs'] != 2 or value['payload'].get('think') is not True
            or output.resolve().is_relative_to(Path(value['raw_root']))):
        raise ValueError('fixed two-call reasoning probe differs')
    if session is None:
        import requests
        session = requests.Session(); session.trust_env = False
    if backend_binding(value['provider'], session) != value['backend']:
        raise ValueError('live model/backend differs')
    output.mkdir(parents=True, exist_ok=False)
    write_json_atomic(output / 'plan.json', value, sort_keys=True, allow_nan=False)
    records = []
    try:
        for call in value['calls']:
            if pinned_revision(ROOT) != value['source_commit'] or runtime_binding() != value['runtime']:
                raise ValueError('source changed after pinning')
            if backend_binding(value['provider'], session) != value['backend']:
                raise ValueError('model/backend changed')
            payload = {**clone(value['payload']), 'think': call['think']}
            prefix = f"call-{call['ordinal']:02d}"
            write_json_atomic(output / (prefix + '.started.json'), {
                'schema': SCHEMA + '.started', 'plan_sha256': value['content_sha256'],
                'call': call, 'started_utc': archive.utc(), 'http_timeout_seconds': [10, 900],
                **wire_record(payload, PLAN_ACTION_SCHEMA)}, sort_keys=True, allow_nan=False)
            record = dispatch(session, value['provider'], payload)
            record.update(schema=SCHEMA + '.completed', plan_sha256=value['content_sha256'], call=call)
            write_json_atomic(output / (prefix + '.completed.json'), record, sort_keys=True, allow_nan=False)
            records.append(record)
            if record.get('interrupted'):
                raise KeyboardInterrupt('charged probe interrupted; no automatic redispatch')
    finally:
        unchanged = (archive._inventory(Path(value['raw_root'])) == value['closure']['raw_inventory']
            and all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha
                for p, sha in value['closure']['input_files'].items()))
        summary = {'schema': SCHEMA + '.summary', 'plan_sha256': value['content_sha256'],
            'recorded_attempts': len(list(output.glob('call-*.started.json'))),
            'completed_receipts': len(records), 'original_files_unchanged': unchanged,
            'actions_applied': 0, 'native_worlds': 0,
            'results': [{k: r.get(k) for k in ('call', 'technical_success', 'complete_envelope',
                'plan_schema_valid', 'thinking_characters', 'content_characters', 'costs')} for r in records],
            'claim': 'Two fixed-order probes, not proof of universal reliability, reasoning quality or scientific improvement.'}
        write_json_atomic(output / 'summary.json', summary, sort_keys=True, allow_nan=False)
        if not unchanged:
            raise ValueError('original evidence changed')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--audit', type=Path, action='append', required=True)
    parser.add_argument('--writer-ended', type=Path, required=True)
    parser.add_argument('--provider-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run-authorized-reasoning-diagnostic', action='store_true', required=True)
    args = parser.parse_args(); raw = args.raw.resolve()
    with archive.ended_writer_lock(raw):
        config = archive.read(args.provider_config)
        if set(config) != {'provider_binding'}:
            raise ValueError('exact operator-owned provider configuration required')
        value = plan(raw, audits=args.audit, writer_ended=args.writer_ended, provider=config['provider_binding'])
        print(json.dumps(run(value, args.output)), flush=True)


if __name__ == '__main__':
    main()
