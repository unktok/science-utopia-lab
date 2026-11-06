#!/usr/bin/env python3
"""Optional six-POST paired interface diagnostic; never applies model actions."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jsonschema import Draft202012Validator
from scripts.analyze_native_staged_search_v15 import SCHEMA as AUDIT_SCHEMA, ROLE_CLASSIFICATION
from scripts.analyze_native_autonomous_search_v14 import _inventory, read
from utopia.optimization.native_designer_decoding_v24 import designer_payload
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_designer_roles_v38 import validate_designer_binding
from utopia.optimization.native_designer_tools_v25 import (
    LEGACY_HISTORY, PLAIN_JSON_HISTORY, CHANNEL, action_from_body, conversation_schema,
)
from utopia.optimization.native_designer_wire import post, wire_record
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_staged_author_v15 import ACTION_SCHEMA, build_conversation, call_task
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic

SCHEMA = 'scienceutopia.paired-history-diagnostic.v40'
ORIGINAL_SOURCE = 'd29d7917c3c22b246106378ac4b988c92ba53c35'
SEARCH = 'search-237987af18ce4f0d9d9a0185ed0b0a9d'
G0 = '343aa017b35a4b892658611eec646630b86226e28c6046d117180fe36fd81531'
G1 = '9492906885969bb0128370ff47add44216d3a1cd44732304a2277a0a1e6a537c'
FRAMES = (('g0-step01-eof', G0, 1), ('g1-step03-eof', G1, 3), ('g0-step03-write', G0, 3))
# Three per profile; alternating global order; each pair uses the identical original seed.
ORDER = ((0, LEGACY_HISTORY), (1, PLAIN_JSON_HISTORY), (2, LEGACY_HISTORY),
         (0, PLAIN_JSON_HISTORY), (1, LEGACY_HISTORY), (2, PLAIN_JSON_HISTORY))


def utc():
    return datetime.now(timezone.utc).isoformat()


def hashed(value, field='content_sha256'):
    if value.get(field) != digest({k: v for k, v in value.items() if k != field}):
        raise ValueError('original record hash differs')
    return value


def git_hashes(names):
    return {name: hashlib.sha256(subprocess.check_output(
        ['git', 'show', ORIGINAL_SOURCE + ':' + name], cwd=ROOT)).hexdigest() for name in names}


@contextmanager
def ended_writer_lock(raw):
    # Read-only open: do not create or alter any original evidence/lock bytes.
    with (raw / 'pilot-writer.lock').open('rb') as handle:
        fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        yield


def closure(raw, audits, writer_ended):
    if len(audits) != 2 or audits[0].resolve() == audits[1].resolve():
        raise ValueError('two separate matching original full audits required')
    if any(p.is_symlink() or p.resolve().is_relative_to(raw) for p in audits):
        raise ValueError('original audits must be regular files outside raw evidence')
    first, second = [hashed(read(path)) for path in audits]
    proof = first.get('audit', {})
    if (first != second or first.get('schema') != AUDIT_SCHEMA
            or first.get('source_commit') != ORIGINAL_SOURCE
            or first.get('classification') != ROLE_CLASSIFICATION
            or first.get('engineering_revision') != 'v39-a1'
            or first.get('budget_terminal') is not True or first.get('queue_terminal') is not True
            or first.get('planned_native_slots') != 8 or first.get('consumed_native_slots') != 8
            or first.get('status') not in ('complete', 'budget-complete-with-failures')
            or Path(proof.get('raw_root', '')).resolve() != raw
            or proof.get('new_model_calls') != 0 or proof.get('new_container_executions') != 0
            or proof.get('exact_raw_tools_draft_source_definition_replayed') is not True
            or proof.get('own_history_loss_and_all_ties_replayed') is not True):
        raise ValueError('matching original-source terminal audit evidence required')
    files = proof.get('source_proofs', {}).get('files', {})
    required = set(subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', ORIGINAL_SOURCE,
        '--', 'utopia'], cwd=ROOT, text=True).splitlines())
    required = {name for name in required if name.endswith('.py')} | {
        'scripts/analyze_native_staged_search_v15.py', 'scripts/run_native_designer_roles_v38.py',
        'scripts/run_native_staged_search_v15.py',
        'research/protocols/campaigns/native-execution-readiness-v39-a1.md'}
    if (proof.get('source_proofs', {}).get('status') != 'verified-exact-staged-runtime-driver-helper-source-blobs'
            or not required <= set(files)):
        raise ValueError('original audit source proofs incomplete')
    hashes = git_hashes(files)
    if any(files[name] != {'actual_source_sha256': sha, 'analysis_source_sha256': sha}
            for name, sha in hashes.items()) or proof.get('analysis_source_sha256') != hashes[
                'scripts/analyze_native_staged_search_v15.py']:
        raise ValueError('audit was not produced by the exact original source')
    if writer_ended.resolve().parent != raw or writer_ended.is_symlink():
        raise ValueError('explicit original ended-writer receipt required')
    ends = []
    for started in sorted(raw.glob('writer*.started.json')):
        start = read(started)
        ended = started.with_name(started.name.replace('.started.json', '.ended.json'))
        receipt = read(ended)
        if (start.get('source_commit') != ORIGINAL_SOURCE or receipt.get('source_commit') != ORIGINAL_SOURCE
                or receipt.get('status') != 'exited' or type(receipt.get('exit_code')) is not int
                or receipt['exit_code'] not in (0, 1) or not receipt.get('ended_utc')
                or any(receipt.get(k) != start.get(k) for k in start if k != 'status')):
            raise ValueError('original writer has not exited with its source-matched receipt')
        ends.append(ended.resolve())
    if not ends or writer_ended.resolve() not in ends:
        raise ValueError('explicit ended writer does not match original launch')
    inventory = _inventory(raw)
    if (inventory != proof.get('raw_input_sha256s') or digest(inventory) != proof.get('raw_inventory_sha256')
            or proof.get('raw_files_verified_unchanged') != len(inventory)):
        raise ValueError('original raw evidence differs from its terminal audits')
    return {'audit_sha256': first['content_sha256'], 'raw_inventory_sha256': digest(inventory),
        'input_files': {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [*audits, writer_ended]}, 'raw_inventory': inventory}


def build_plan(raw, *, audits, writer_ended, provider, source_commit):
    raw = raw.resolve()
    evidence = closure(raw, audits, writer_ended)
    original_plan = read(raw / 'plan.json')
    validate_designer_binding(provider, scientist_binding=original_plan['provider_binding'])
    if original_plan.get('source_commit') != ORIGINAL_SOURCE or provider != original_plan['designer_provider_binding']:
        raise ValueError('diagnostic provider/original pilot differs')
    frames, expected_backend = [], None
    for identity, generation, step in FRAMES:
        cell = raw / 'queue' / SEARCH / 'authoring' / ('generation-' + generation)
        binding = hashed(read(cell / 'request.json'), 'binding_sha256')
        started = read(cell / f'step-{step:02d}.started.json')
        completed = hashed(read(cell / f'step-{step:02d}.completed.json'))
        transport = completed['model_reply']['transport']
        task = call_task(step, 8)
        seed = ('native-staged-designer-v15', binding['binding_sha256'], step)
        if (binding['provider_binding'] != provider or binding['request_sha256'] != generation
                or digest(binding['request']) != generation or binding['settings']['max_steps'] != 8
                or binding['settings']['max_tokens'] != 8192 or started['step'] != step
                or started['binding_sha256'] != binding['binding_sha256']
                or started['prompt_sha256'] != digest(started['prompt']) or started['response_schema'] != ACTION_SCHEMA
                or completed['started_file_sha256'] != hashlib.sha256(
                    (cell / f'step-{step:02d}.started.json').read_bytes()).hexdigest()):
            raise ValueError('fixed original diagnostic frame binding differs')
        payloads = {}
        for profile in (LEGACY_HISTORY, PLAIN_JSON_HISTORY):
            messages = build_conversation(started['prompt'], task, native_tools=True, conversation_profile=profile)
            payloads[profile] = designer_payload('staged-v15', provider, messages, seed,
                max_tokens=8192, temperature=.6, role='editor')
        if (transport['request_payload'] != payloads[LEGACY_HISTORY]
                or any(transport.get(k) != v for k, v in wire_record(payloads[LEGACY_HISTORY], ACTION_SCHEMA).items())
                or transport.get('http_timeout_seconds') != [10, 900]):
            raise ValueError('original legacy request/prompt/wire reconstruction differs')
        if identity.endswith('eof'):
            if (completed['status'] != 'transport-error' or transport.get('http_status') != 500
                    or transport.get('raw_http_response') != '{"error":"EOF"}'):
                raise ValueError('fixed historical EOF evidence differs')
        elif completed['status'] != 'applied' or completed['model_reply']['output'].get('tool') != 'write_file':
            raise ValueError('fixed successful historical write differs')
        backend = transport['preflight']['backend']
        if expected_backend is not None and backend != expected_backend:
            raise ValueError('original frames have different backend bindings')
        expected_backend = backend
        frames.append({'id': identity, 'generation': generation, 'step': step,
            'prompt': started['prompt'], 'task': task, 'seed_ctx': list(seed), 'payloads': payloads})
    plan = {'schema': SCHEMA + '.plan', 'source_commit': source_commit, 'runtime': runtime_binding(),
        'diagnostic_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'raw_root': str(raw), 'original_source_commit': ORIGINAL_SOURCE, 'closure': evidence,
        'provider': clone(provider), 'backend': expected_backend, 'frames': frames,
        'calls': [{'ordinal': i, 'frame': f, 'conversation_profile': p} for i, (f, p) in enumerate(ORDER)],
        'maximum_POSTs': 6, 'maximum_metadata_GETs': 14, 'http_timeout_seconds': [10, 900],
        'max_tokens': 8192, 'temperature': .6, 'network_retries': 0,
        'native_worlds': 0, 'scientist_POSTs': 0, 'actions_applied': 0,
        'scope': 'Separately charged paired replicates; no candidate execution, adoption, repair or scientific inference.'}
    plan['content_sha256'] = digest(plan)
    return plan


def dispatch(session, plan, call):
    frame, profile = plan['frames'][call['frame']], call['conversation_profile']
    transport = {'request_payload': clone(frame['payloads'][profile]), 'endpoint': 'http://127.0.0.1:11434/api/chat',
        'model_digest': plan['provider']['model_digest'], 'network_retries': 0, 'response_channel': CHANNEL,
        'conversation_profile': profile, 'conversation_schema': conversation_schema('author', profile)}
    record = {'call': clone(call), 'transport': transport, 'action_applied': False,
        'http_200': None, 'complete_envelope': None, 'provider_matches': None,
        'strict_action_parse': False, 'action_schema_valid': False}
    begin = time.monotonic()
    try:
        response = post(session, transport['endpoint'], transport['request_payload'], ACTION_SCHEMA,
            transport, timeout=(10, 900))
        transport.update(http_status=response.status_code, raw_http_response=response.text)
        record['http_200'] = response.status_code == 200
        # Preserve even incomplete provider envelopes/counters; never salvage an action.
        from utopia.optimization.native_search_generator_v14 import _strict_json
        body = _strict_json(response.text)
        transport['response_payload'] = body
        record['costs'] = {k: body.get(k) for k in ('prompt_eval_count', 'eval_count')}
        record['provider_matches'] = body.get('model') == plan['provider']['model']
        record['complete_envelope'] = body.get('done') is True and body.get('done_reason') != 'length'
        response.raise_for_status()
        action = action_from_body(body)
        record.update(parsed_action=action, strict_action_parse=True)
        Draft202012Validator(ACTION_SCHEMA).validate(action)
        record['action_schema_valid'] = True
    except BaseException as error:
        record['error'] = {'type': type(error).__name__, 'message': str(error)[:4000]}
        record['interrupted'] = not isinstance(error, Exception)
    transport['elapsed_seconds'] = time.monotonic() - begin
    record.setdefault('costs', {'prompt_eval_count': None, 'eval_count': None})
    record['technical_success'] = all(record[k] is True for k in (
        'http_200', 'complete_envelope', 'provider_matches', 'strict_action_parse', 'action_schema_valid'))
    record['missing_cost_not_imputed'] = True
    record['ended_utc'] = utc()
    return record


def run(plan, output, *, session=None):
    hashed(plan)
    if output.resolve().is_relative_to(Path(plan['raw_root'])):
        raise ValueError('diagnostic output must be outside immutable original evidence')
    if output.exists() or output.is_symlink():
        raise FileExistsError('fresh diagnostic output required; no resume or redispatch')
    if plan.get('maximum_POSTs') != 6 or plan.get('calls') != [
            {'ordinal': i, 'frame': f, 'conversation_profile': p} for i, (f, p) in enumerate(ORDER)]:
        raise ValueError('fixed six-call diagnostic plan differs')
    if session is None:
        import requests
        session = requests.Session()
        session.trust_env = False
    if backend_binding(plan['provider'], session) != plan['backend']:
        raise ValueError('diagnostic live model/backend differs from original frames')
    output.mkdir(parents=True, exist_ok=False)  # No resume/retry of any charged intent.
    write_json_atomic(output / 'plan.json', plan, sort_keys=True, allow_nan=False)
    records = []
    try:
        for call in plan['calls']:
            if pinned_revision(ROOT) != plan['source_commit'] or runtime_binding() != plan['runtime']:
                raise ValueError('diagnostic source changed after plan pinning')
            if backend_binding(plan['provider'], session) != plan['backend']:
                raise ValueError('diagnostic model/backend changed before dispatch')
            intent = {'schema': SCHEMA + '.started', 'plan_sha256': plan['content_sha256'],
                'call': call, 'started_utc': utc(), 'http_timeout_seconds': [10, 900],
                **wire_record(plan['frames'][call['frame']]['payloads'][call['conversation_profile']], ACTION_SCHEMA)}
            prefix = f"call-{call['ordinal']:02d}"
            write_json_atomic(output / (prefix + '.started.json'), intent, sort_keys=True, allow_nan=False)
            record = dispatch(session, plan, call)
            record.update(schema=SCHEMA + '.completed', plan_sha256=plan['content_sha256'])
            write_json_atomic(output / (prefix + '.completed.json'), record, sort_keys=True, allow_nan=False)
            records.append(record)
            if record.get('interrupted'):
                raise KeyboardInterrupt('paired diagnostic interrupted; no automatic redispatch')
    finally:
        unchanged = (_inventory(Path(plan['raw_root'])) == plan['closure']['raw_inventory']
            and all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha
                for path, sha in plan['closure']['input_files'].items()))
        summary = {'schema': SCHEMA + '.summary', 'plan_sha256': plan['content_sha256'],
            'recorded_attempts': len(list(output.glob('call-*.started.json'))), 'completed_receipts': len(records),
            'strict_schema_successes': sum(r.get('action_schema_valid', False) for r in records),
            'technical_successes': sum(r['technical_success'] for r in records),
            'profiles': {profile: {'recorded_receipts': sum(
                r['call']['conversation_profile'] == profile for r in records),
                **{key: sum(r.get(key) is True for r in records
                if r['call']['conversation_profile'] == profile) for key in
                ('http_200', 'complete_envelope', 'strict_action_parse', 'action_schema_valid', 'technical_success')}}
                for profile in (LEGACY_HISTORY, PLAIN_JSON_HISTORY)},
            'original_files_unchanged': unchanged, 'actions_applied': 0, 'native_worlds': 0,
            'claim': 'Small-N diagnostic only; no universal transport fix or scientific benefit established.'}
        write_json_atomic(output / 'summary.json', summary, sort_keys=True, allow_nan=False)
        if not unchanged:
            raise ValueError('original evidence changed during paired diagnostic')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--audit', type=Path, action='append', required=True)
    parser.add_argument('--writer-ended', type=Path, required=True)
    parser.add_argument('--provider-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run-authorized-paired-diagnostic', action='store_true', required=True)
    args = parser.parse_args()
    source = pinned_revision(ROOT)
    raw = args.raw.resolve()
    with ended_writer_lock(raw):
        config = read(args.provider_config)
        if set(config) != {'provider_binding'}:
            raise ValueError('exact operator-owned provider configuration required')
        plan = build_plan(raw, audits=args.audit, writer_ended=args.writer_ended,
            provider=config['provider_binding'], source_commit=source)
        result = run(plan, args.output)
    print(json.dumps(result), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
