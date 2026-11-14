"""Finite output-mode assay; never resumes a stopped scientific campaign.

Three one-shot calibrations, then at most one free proposal. The historical
frames/compiler are literal; only format/think change. No worlds or repairs.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sys

from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_designer_wire import wire_record
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_workflow_designer_v1 import (
    SCHEMA as ORIGINAL_SCHEMA, SETTINGS, WORKER, _payload, _outcome)
from utopia.optimization.native_workflow_submission_v1 import control_submission
from utopia.runtime.bounded_process import run_bounded
from utopia.system.design_patch import clone
from utopia.utils.data_utils import decode_json, file_sha256

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'research/protocols/campaigns/workflow-designer-output-mode-assay-v1.md'
SCHEMA = 'scienceutopia.workflow-output-mode-assay.v1'
ARMS = ('schema-nonthinking', 'json-thinking', 'schema-thinking')
PRIORITY = tuple(reversed(ARMS))
ENVIRONMENT = {'PYTHONHASHSEED': '42', 'CUDA_VISIBLE_DEVICES': '',
    'HF_HUB_OFFLINE': '1', 'HF_DATASETS_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}
HISTORICAL_FILES = ('binding.json', 'call.intent.json', 'call.http.json', 'result.json')


def utc(): return datetime.now(timezone.utc).isoformat()
def read(path): return checked(decode_json(Path(path).read_text(), strict=True, finite_floats=True))


def historical_frame(root, purpose):
    root = Path(root).resolve()
    before = {name: file_sha256(root / name) for name in HISTORICAL_FILES}
    binding, intent, raw, result = [read(root / name) for name in HISTORICAL_FILES]
    current = runtime_binding()
    if (binding['schema'] != ORIGINAL_SCHEMA + '.binding' or binding['purpose'] != purpose
            or binding['settings'] != SETTINGS
            or any(current.get(k) != v for k, v in binding['runtime'].items())):
        raise ValueError('historical compiler/runtime/settings/purpose changed')
    payload, schema, wire = _payload(binding)
    if (intent['schema'] != ORIGINAL_SCHEMA + '.intent'
            or intent['binding_sha256'] != binding['content_sha256']
            or intent['provider'] != binding['provider'] or intent['backend'] != binding['backend']
            or intent['payload'] != payload or intent['response_schema'] != schema
            or intent['request_wire'] != wire or intent['http_timeout_seconds'] != [10, 900]
            or result['schema'] != ORIGINAL_SCHEMA + '.result'
            or result['binding_sha256'] != binding['content_sha256']
            or result['intent_sha256'] != intent['content_sha256']
            or result['raw_http_file_sha256'] != before['call.http.json']):
        raise ValueError('historical original frame/receipt differs')
    outcome = _outcome(binding, intent, result['execution'], raw)
    if any(result.get(k) != v for k, v in outcome.items()) or outcome['completion_unknown']:
        raise ValueError('historical result is changed or completion unknown')
    if before != {name: file_sha256(root / name) for name in HISTORICAL_FILES}:
        raise ValueError('historical input changed while reading')
    return {'root': str(root), 'files_sha256': before,
        'binding': binding, 'intent': intent, 'result': result}


def changed_payload(frame, arm):
    if arm not in ARMS: raise ValueError('undeclared output-mode arm')
    payload = clone(frame['intent']['payload'])
    if arm.startswith('schema-'): payload['format'] = clone(frame['intent']['response_schema'])
    payload['think'] = arm.endswith('-thinking') and arm != 'schema-nonthinking'
    return payload


def choose(results):
    if len(results) != 3 or any(r['completion_unknown'] for r in results): return None
    by_arm = {r['arm']: r for r in results}
    return next((a for a in PRIORITY if by_arm[a]['status'] == 'submitted'), None)


def make_plan(calibration, proposal, source):
    frames = {'calibration': historical_frame(calibration, 'calibration'),
        'proposal': historical_frame(proposal, 'proposal')}
    a, b = (frames[k]['binding'] for k in ('calibration', 'proposal'))
    if any(a[k] != b[k] for k in ('provider', 'backend', 'settings', 'runtime')):
        raise ValueError('historical frames do not use the same backend/runtime')
    return {'schema': SCHEMA + '.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'script_sha256': file_sha256(__file__), 'protocol_sha256': file_sha256(ROOT / PROTOCOL),
        'frames': frames, 'arm_order': list(ARMS), 'technical_priority': list(PRIORITY),
        'maximum_fresh_model_calls': 4, 'new_scientist_worlds': 0,
        'wall_seconds_per_call': 1200, 'http_timeout_seconds': [10, 900],
        'environment': ENVIRONMENT, 'scientific_dispatch_authorized': False,
        'stopped_study_retry_or_refill': False, 'copy_is_dispatch_veto': False}


def require_plan(plan):
    if any(os.environ.get(k) != v for k, v in ENVIRONMENT.items()):
        raise ValueError('declared offline environment required')
    rebuilt = make_plan(*(plan['frames'][k]['root'] for k in ('calibration', 'proposal')),
        source=pinned_revision(ROOT))
    if {k: v for k, v in plan.items() if k != 'content_sha256'} != rebuilt:
        raise ValueError('assay source/plan/original inputs changed')


def inspect_call(root, plan, frame, arm, *, execute=False):
    root = Path(root)
    payload = changed_payload(frame, arm); schema = frame['intent']['response_schema']
    expected = {'schema': SCHEMA + '.intent', 'plan_sha256': plan['content_sha256'],
        'provider': frame['binding']['provider'], 'backend': frame['binding']['backend'],
        'payload': payload, 'response_schema': schema, 'request_wire': wire_record(payload, schema),
        'http_timeout_seconds': [10, 900]}
    if execute:
        root.mkdir()  # Exclusive attempt, including incomplete prior attempts.
        intent = save(root / 'call.intent.json', {**expected, 'started_utc': utc()})
        execution = run_bounded([sys.executable, '-m', WORKER, '--worker',
            str(root / 'call.intent.json'), str(root / 'call.http.json')],
            seconds=1200, cwd=ROOT)
    else:
        intent = read(root / 'call.intent.json')
        execution = read(root / 'result.json')['execution']
    if {k: v for k, v in intent.items() if k not in ('content_sha256', 'started_utc')} != expected:
        raise ValueError('assay literal intent changed')
    raw_path = root / 'call.http.json'
    raw = read(raw_path) if raw_path.is_file() else None
    outcome = _outcome(frame['binding'], intent, execution, raw)
    response = (raw or {}).get('transport', {}).get('response_payload') or {}
    thinking = response.get('message', {}).get('thinking')
    result = {'schema': SCHEMA + '.call', 'arm': arm,
        'plan_sha256': plan['content_sha256'], 'intent_sha256': intent['content_sha256'],
        'execution': execution, 'raw_http_file_sha256': file_sha256(raw_path) if raw else None,
        **outcome, 'copy_equal_diagnostic': (outcome['literal_submission'] ==
            control_submission(frame['binding']['request'])) if frame['binding']['purpose'] == 'calibration' else None,
        'provider_evidence': {k: response.get(k) for k in
            ('done', 'done_reason', 'prompt_eval_count', 'eval_count', 'total_duration')},
        'observed_thinking_characters': len(thinking) if isinstance(thinking, str) else None}
    if execute: return save(root / 'result.json', result)
    saved = read(root / 'result.json')
    if {k: v for k, v in saved.items() if k != 'content_sha256'} != result:
        raise ValueError('assay cold public compiler outcome differs')
    return saved


def summary(plan, results, free):
    unknown = any(r['completion_unknown'] for r in results + ([free] if free else []))
    selected = choose(results)
    return {'schema': SCHEMA + '.terminal', 'plan_sha256': plan['content_sha256'],
        'status': 'stopped-completion-unknown' if unknown else 'closed-technical-assay-only',
        'calibration_results': [r['content_sha256'] for r in results],
        'selected_mode': selected, 'free_proposal_result': free['content_sha256'] if free else None,
        'free_proposal_status': free['status'] if free else None,
        'fresh_model_calls_upper_bound': len(results) + int(free is not None),
        'new_scientist_worlds': 0, 'old_study_repaired_or_refilled': False,
        'institutional_improvement_or_publication_readiness_established': False}


def run(root):
    root = Path(root).resolve(); plan = read(root / 'plan.json'); require_plan(plan)
    with (root / 'owner.lock').open('a') as owner, (root / 'inference.lock').open('a') as inference:
        for handle in (owner, inference): fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / 'started.json').exists():
            raise ValueError('assay already attempted; replay only, never resume or redispatch')
        # Metadata requests only; every worker checks this again before POST.
        if backend_binding(plan['frames']['calibration']['binding']['provider']) != plan['frames']['calibration']['binding']['backend']:
            raise ValueError('actual backend differs from the retained experiment')
        save(root / 'started.json', {'schema': SCHEMA + '.started',
            'plan_sha256': plan['content_sha256'], 'pid': os.getpid(), 'started_utc': utc()})
        results, free = [], None
        for arm in ARMS:
            require_plan(plan)
            result = inspect_call(root / arm, plan, plan['frames']['calibration'], arm, execute=True)
            results.append(result)
            print(json.dumps({'arm': arm, 'status': result['status'],
                'completion_unknown': result['completion_unknown'], 'error': result['technical_error']}), flush=True)
            if result['completion_unknown']: break
        selected = choose(results)
        if selected is not None:
            require_plan(plan)
            free = inspect_call(root / 'free-proposal', plan, plan['frames']['proposal'], selected, execute=True)
        return save(root / 'terminal.json', {**summary(plan, results, free), 'ended_utc': utc()})


def replay(root):
    root = Path(root).resolve(); plan = read(root / 'plan.json'); require_plan(plan)
    start = read(root / 'started.json')
    if start['plan_sha256'] != plan['content_sha256']: raise ValueError('assay start differs')
    terminal = read(root / 'terminal.json'); results, free = [], None
    for arm in ARMS:
        results.append(inspect_call(root / arm, plan, plan['frames']['calibration'], arm))
        if results[-1]['completion_unknown']: break
    selected = choose(results)
    if selected is not None:
        free = inspect_call(root / 'free-proposal', plan, plan['frames']['proposal'], selected)
    allowed = set(ARMS[:len(results)]) | ({'free-proposal'} if free else set())
    actual = {p.name for p in root.iterdir() if p.is_dir()}
    if actual != allowed: raise ValueError('unexpected or missing assay attempts')
    if {k: v for k, v in terminal.items() if k not in ('content_sha256', 'ended_utc')} != summary(plan, results, free):
        raise ValueError('assay terminal differs from literal cold reconstruction')
    return terminal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run', 'replay'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calibration', type=Path)
    parser.add_argument('--proposal', type=Path)
    args = parser.parse_args(); out = args.output.resolve()
    if not out.is_relative_to(ROOT / 'outputs'):
        raise ValueError('fresh ignored output below the frozen source required')
    if args.action == 'prepare':
        if args.calibration is None or args.proposal is None:
            raise ValueError('both exact historical frame roots required')
        plan = make_plan(args.calibration, args.proposal, pinned_revision(ROOT))
        out.mkdir(parents=True)
        result = save(out / 'plan.json', plan)
    else:
        result = run(out) if args.action == 'run' else replay(out)
    print(json.dumps({k: v for k, v in result.items() if k != 'frames'}, sort_keys=True))


if __name__ == '__main__': main()
