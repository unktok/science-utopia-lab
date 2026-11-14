"""One fresh capacity probe after a retained known thinking-only length stop."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts import diagnose_native_workflow_output_modes_v1 as shared
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import clone
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.workflow-thinking-capacity-probe.v1'
PROTOCOL = 'research/protocols/campaigns/workflow-thinking-capacity-probe-v1.md'
OUTPUT_TOKENS = 16384
MARGIN = 512


def cold_replay(root, source):
    completed = subprocess.run([sys.executable, '-m',
        'scripts.diagnose_native_workflow_output_modes_v1', 'replay', '--output', str(root)],
        cwd=source, env={**os.environ, **shared.ENVIRONMENT},
        capture_output=True, text=True, timeout=120, check=True)
    return json.loads(completed.stdout)


def origin(root, source):
    root, source = Path(root).resolve(), Path(source).resolve()
    files = {str(p.relative_to(root)): file_sha256(p) for p in sorted(root.rglob('*.json'))}
    terminal = cold_replay(root, source)
    plan = shared.read(root / 'plan.json'); free = shared.read(root / 'free-proposal/result.json')
    intent = shared.read(root / 'free-proposal/call.intent.json')
    raw = shared.read(root / 'free-proposal/call.http.json')
    response = raw['transport']['response_payload']
    payload = intent['payload']; prompt = response.get('prompt_eval_count')
    if (terminal != shared.read(root / 'terminal.json')
            or terminal['status'] != 'closed-technical-assay-only'
            or terminal['selected_mode'] != 'schema-thinking'
            or terminal['fresh_model_calls_upper_bound'] != 4
            or terminal['free_proposal_result'] != free['content_sha256']
            or free['status'] != 'failed' or free['completion_unknown']
            or free['literal_submission'] is not None or free['definition'] is not None
            or response.get('done') is not True or response.get('done_reason') != 'length'
            or response.get('eval_count') != payload['options']['num_predict']
            or payload['options']['num_predict'] != 8192 or payload['options']['num_ctx'] != 40960
            or response.get('message', {}).get('content') != ''
            or not response.get('message', {}).get('thinking')
            or payload['think'] is not True or payload['format'] != intent['response_schema']
            or type(prompt) is not int or prompt <= 0
            or prompt + OUTPUT_TOKENS + MARGIN > payload['options']['num_ctx']):
        raise ValueError('known8192 thinking-only length stop with measured context room required')
    if files != {str(p.relative_to(root)): file_sha256(p) for p in sorted(root.rglob('*.json'))}:
        raise ValueError('prior assay changed during original-source cold reconstruction')
    return {'root': str(root), 'frozen_source': str(source), 'source_commit': plan['source_commit'],
        'files_sha256': files, 'terminal': terminal, 'free_result': free,
        'binding': plan['frames']['proposal']['binding'], 'intent': intent,
        'prior_measured_input_tokens': prompt}


def derived_frame(previous):
    payload = clone(previous['intent']['payload'])
    payload['options']['num_predict'] = OUTPUT_TOKENS
    return {'binding': previous['binding'], 'intent': {
        'payload': payload, 'response_schema': previous['intent']['response_schema']}}


def make_plan(root, source, adapter_source):
    previous = origin(root, source)
    return {'schema': SCHEMA + '.plan', 'source_commit': adapter_source,
        'runtime': runtime_binding(), 'script_sha256': file_sha256(__file__),
        'shared_adapter_sha256': file_sha256(shared.__file__),
        'protocol_sha256': file_sha256(ROOT / PROTOCOL), 'origin': previous,
        'payload': derived_frame(previous)['intent']['payload'],
        'changed_fields': {'payload.options.num_predict': [8192, OUTPUT_TOKENS]},
        'minimum_measured_context_margin': MARGIN, 'maximum_fresh_model_calls': 1,
        'http_timeout_seconds': [10, 900], 'wall_seconds': 1200,
        'shared_call_receipt_schema': shared.SCHEMA + '.call',
        'new_scientist_worlds': 0, 'scientific_dispatch_authorized': False,
        'original_study_or_assay_reopened': False, 'environment': shared.ENVIRONMENT}


def require_plan(plan):
    if any(os.environ.get(k) != v for k, v in shared.ENVIRONMENT.items()):
        raise ValueError('declared offline environment required')
    rebuilt = make_plan(plan['origin']['root'], plan['origin']['frozen_source'], pinned_revision(ROOT))
    if {k: v for k, v in plan.items() if k != 'content_sha256'} != rebuilt:
        raise ValueError('capacity-probe source/plan/unchanged original inputs differ')


def terminal(plan, result):
    return {'schema': SCHEMA + '.terminal', 'plan_sha256': plan['content_sha256'],
        'status': 'stopped-completion-unknown' if result['completion_unknown'] else 'closed-technical-probe-only',
        'call_result_sha256': result['content_sha256'], 'proposal_status': result['status'],
        'completion_unknown': result['completion_unknown'], 'fresh_model_calls_upper_bound': 1,
        'new_scientist_worlds': 0, 'new_scientific_losses': 0,
        'original_study_or_assay_reopened': False, 'production_certificate_issued': False,
        'institutional_improvement_or_publication_readiness_established': False}


def run(root):
    root = Path(root).resolve(); plan = shared.read(root / 'plan.json'); require_plan(plan)
    with (root / 'owner.lock').open('a') as owner, (root / 'inference.lock').open('a') as inference:
        for handle in (owner, inference): fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / 'started.json').exists(): raise ValueError('capacity probe already attempted; replay only')
        frame = derived_frame(plan['origin'])
        if backend_binding(frame['binding']['provider']) != frame['binding']['backend']:
            raise ValueError('actual backend differs from retained model binding')
        save(root / 'started.json', {'schema': SCHEMA + '.started',
            'plan_sha256': plan['content_sha256'], 'pid': os.getpid(), 'started_utc': shared.utc()})
        result = shared.inspect_call(root / 'call', plan, frame, 'schema-thinking', execute=True)
        return save(root / 'terminal.json', {**terminal(plan, result), 'ended_utc': shared.utc()})


def replay(root):
    root = Path(root).resolve(); plan = shared.read(root / 'plan.json'); require_plan(plan)
    if shared.read(root / 'started.json')['plan_sha256'] != plan['content_sha256']:
        raise ValueError('capacity probe start differs')
    result = shared.inspect_call(root / 'call', plan, derived_frame(plan['origin']), 'schema-thinking')
    if {p.name for p in root.iterdir() if p.is_dir()} != {'call'}:
        raise ValueError('unexpected/missing capacity probe attempts')
    saved = shared.read(root / 'terminal.json')
    if {k: v for k, v in saved.items() if k not in ('content_sha256', 'ended_utc')} != terminal(plan, result):
        raise ValueError('capacity-probe terminal differs from literal cold reconstruction')
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run', 'replay'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--origin', type=Path); parser.add_argument('--origin-source', type=Path)
    args = parser.parse_args(); out = args.output.resolve()
    if not out.is_relative_to(ROOT / 'outputs'): raise ValueError('fresh ignored output below frozen source required')
    if args.action == 'prepare':
        if args.origin is None or args.origin_source is None: raise ValueError('original assay/source required')
        plan = make_plan(args.origin, args.origin_source, pinned_revision(ROOT))
        out.mkdir(parents=True); result = save(out / 'plan.json', plan)
        print(json.dumps({'prepared_source': result['source_commit'], 'plan_sha256': result['content_sha256'],
            'maximum_fresh_model_calls': 1, 'num_predict': OUTPUT_TOKENS, 'new_scientist_worlds': 0}))
    else:
        print(json.dumps(run(out) if args.action == 'run' else replay(out), sort_keys=True))


if __name__ == '__main__': main()
