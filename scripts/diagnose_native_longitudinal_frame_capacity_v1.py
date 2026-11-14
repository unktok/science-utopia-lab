"""Two literal late-history SCRIPTED frames on the real approved local designer.

This is a finite capacity diagnostic, never an institution submission, scientific
world, execution-readiness certificate or license to truncate a production frame.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sys

from scripts.analyze_native_open_v7 import _inventory
from scripts.run_pre_scale_search_v1 import require_environment
from utopia.optimization.native_bounded_author_context_v45 import capacity_observation
from utopia.optimization.native_bounded_staged_designer import DurableSession, CompletionUnknown
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_scientist_load_v38 import load_local_role
from utopia.runtime.bounded_process import run_bounded
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import decode_json, file_sha256

ROOT = Path(__file__).resolve().parents[1]
MODULE = 'scripts.diagnose_native_longitudinal_frame_capacity_v1'
SCHEMA = 'scienceutopia.longitudinal-late-frame-capacity.v1'
PROTOCOL = 'research/protocols/campaigns/native-longitudinal-frame-capacity-v1.md'
ARMS = ('scalar', 'parent-trajectory')
TIMEOUT = (10, 900)


def read(path): return checked(decode_json(Path(path).read_text(), strict=True, finite_floats=True))


def late_frames(root, audits):
    root = Path(root).resolve(); audits = [Path(p).resolve() for p in audits]
    if len(audits) != 2 or audits[0].read_bytes() != audits[1].read_bytes():
        raise ValueError('two original matching SCRIPTED development audits required')
    a, p = read(audits[0]), read(root/'plan.json'); inventory = _inventory(root)
    if (a['schema'] != 'scienceutopia.native-longitudinal-comparison-audit.v1'
            or a['plan_sha256'] != p['content_sha256'] or a['source_commit'] != p['source_commit']
            or a['source_proof']['status'] != 'verified-exact-source-closure'
            or a['raw_inventory_sha256'] != digest(inventory)
            or a['closure']['terminal']['status'] != 'closed'
            or a['closure']['terminal']['consumed_slots'] != 12
            or p.get('origin') != {'SCRIPTED': 'upstream fixture'}):
        raise ValueError('exact closed SCRIPTED fixture, never a scientific optimization archive, required')
    frames = []
    for arm in ARMS:
        candidates = []
        for intent in sorted((root/'search'/arm).glob('*/authoring/proposal-*/editor-session/intent.json')):
            d = read(intent); req = d['request']
            if d['kind'] != 'proposal' or len(req.get('history', [])) != 2:
                continue
            if req['native_longitudinal_evidence_v1']['access_contract']['mode'] != arm:
                raise ValueError('original arm binding differs')
            for path in sorted((intent.parent/'wire').glob('dispatch-*.intent.json')):
                w = read(path); wire = w['wire_utf8']; payload = decode_json(wire, strict=True, finite_floats=True)
                if (payload['model'] != p['designer']['model'] or payload.get('stream') is not False
                        or payload.get('truncate') is not False or payload.get('shift') is not False
                        or payload['options']['num_ctx'] != 40960 or payload['options']['num_predict'] != 8192
                        or payload.get('think') is not False or w['timeout_seconds'] != list(TIMEOUT)):
                    raise ValueError('literal production decoding/context/timeout frame differs')
                candidates.append({'arm': arm, 'generation': req['generation'], 'history_records': 2,
                    'request_sha256': digest(req), 'source_file': str(path), 'source_file_sha256': file_sha256(path),
                    'wire_utf8': wire, 'wire_utf8_bytes': len(wire.encode()), 'wire_sha256': digest(wire)})
        if not candidates: raise ValueError('complete late-history frames absent for '+arm)
        # Predeclared byte-largest late frame; ties keep lexical input order.
        frames.append(max(candidates, key=lambda v: v['wire_utf8_bytes']))
    if inventory != _inventory(root): raise ValueError('original fixture changed while selecting frames')
    return p, frames, {str(path): file_sha256(path) for path in [root/'plan.json', *audits]}


def make_plan(root, audits, source):
    p, frames, inputs = late_frames(root, audits)
    return {'schema': SCHEMA+'.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'script_sha256': file_sha256(__file__), 'protocol_sha256': file_sha256(ROOT/PROTOCOL),
        'origin_run': str(Path(root).resolve()), 'origin_source_commit': p['source_commit'],
        'origin_audits': [str(Path(v).resolve()) for v in audits], 'input_files': inputs,
        'provider': clone(p['designer']), 'backend': backend_binding(p['designer']), 'frames': frames,
        'http_timeout_seconds': list(TIMEOUT), 'worker_wall_seconds': 2100,
        'empty_prompt_load_POSTs_upper_bound': 1, 'capacity_chat_POSTs_upper_bound': 2,
        'all_POSTs_upper_bound': 3, 'scientific_worlds': 0, 'actions_executed': 0,
        'network_retries': 0, 'output_salvage': False, 'automatic_truncation': False,
        'production_certificate_issued': False, 'scientific_dispatch_authorized': False}


def require_plan(root):
    require_environment(); p = read(root/'plan.json')
    expected = make_plan(p['origin_run'], p['origin_audits'], pinned_revision(ROOT))
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('capacity diagnostic source/runtime/backend/literal input changed')
    return p


def require_resources(directory):
    root = Path(directory); start, end = read(root/'started.json'), read(root/'ended.json')
    if (start['schema'] != 'scienceutopia.native-feedback-resource-observation.v2'
            or start['new_inference_POSTs'] != 0 or end['status'] != 'two-observations-ready'
            or end['new_inference_POSTs'] != 0):
        raise ValueError('fresh declared two-observation resource proof required')
    for index in (1, 2):
        c = read(root/f'check-{index}.json')
        if (c['ready_under_declared_shared_resource_profile'] is not True
                or c['unclassified_python_or_model_executables'] or c['loaded_models']['models']
                or c['total_host_cpu_percent'] > 250 or c['free_plus_inactive_bytes'] < 38*1024**3):
            raise ValueError('resource observation is not ready under its unchanged profile')
    elapsed = (datetime.now(timezone.utc)-datetime.fromisoformat(end['ended_utc'])).total_seconds()
    if not 0 <= elapsed <= 120: raise ValueError('resource observation stale or future-dated')
    return {str(p): file_sha256(p) for p in sorted(root.glob('*.json'))}


def result_from_http(frame, record):
    body = decode_json(record['raw_http_response'], strict=True, finite_floats=True)
    payload = decode_json(frame['wire_utf8'], strict=True, finite_floats=True)
    observed = capacity_observation(payload, body)
    final = (record['http_status'] == 200 and body.get('model') == payload['model']
        and body.get('done') is True and body.get('done_reason') == 'stop' and not body.get('error'))
    return {'arm': frame['arm'], 'wire_sha256': frame['wire_sha256'],
        'http_status': record['http_status'], 'done': body.get('done'), 'done_reason': body.get('done_reason'),
        'observed_prompt_tokens': body.get('prompt_eval_count'), 'observed_output_tokens': body.get('eval_count'),
        'capacity': observed, 'final_stop_observed': final,
        'capacity_supported_for_this_literal_frame': final and observed['full_output_reservation_fits_observed_prompt'] is True,
        'returned_action_executed': False}


def worker(root, *, require_plan_fn=None):
    import requests
    p = (require_plan if require_plan_fn is None else require_plan_fn)(root); results = []
    schema = p.get('schema', SCHEMA+'.plan').removesuffix('.plan')
    try:
        session = requests.Session(); session.trust_env = False
        load_local_role(root/'designer-load.json', provider=p['provider'], role='designer',
            purpose='two-literal-late-frame-capacity-only', session=session)
        transport = DurableSession(session, root/'wire', maximum_posts=2)
        for frame in p['frames']:
            if backend_binding(p['provider'], session=session) != p['backend']:
                raise ValueError('actual capacity backend/model changed')
            transport.post('http://127.0.0.1:11434/api/chat', data=frame['wire_utf8'].encode(),
                headers={'Content-Type': 'application/json'}, timeout=TIMEOUT)
            raw = read(root/'wire'/f'dispatch-{len(results):03d}.http.json')
            results.append(result_from_http(frame, raw))
            save(root/f'frame-{len(results)-1}.json', results[-1])
    except BaseException as error:
        save(root/'worker-terminal.json', {'schema': schema+'.worker-terminal', 'results': results,
            'status': 'stopped', 'error_type': type(error).__name__, 'error': str(error),
            'completion_unknown': (isinstance(error, CompletionUnknown)
                or ((root/'designer-load.started.json').exists()
                    and (not (root/'designer-load.json').exists()
                         or not read(root/'designer-load.json')['valid_empty_prompt_load']))),
            'no_retry': True})
        raise
    save(root/'worker-terminal.json', {'schema': schema+'.worker-terminal', 'results': results,
        'status': 'closed-diagnostic-only', 'no_retry': True, 'completion_unknown': False,
        'two_literal_frames_supported': all(r['capacity_supported_for_this_literal_frame'] for r in results),
        'production_certificate_issued': False, 'scientific_dispatch_authorized': False})


def run(root, resources, *, require_plan_fn=None, worker_module=MODULE, resource_check_fn=None):
    p = (require_plan if require_plan_fn is None else require_plan_fn)(root)
    evidence = (require_resources if resource_check_fn is None else resource_check_fn)(resources)
    schema = p.get('schema', SCHEMA+'.plan').removesuffix('.plan')
    with (root/'writer.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root/'started.json').exists(): raise ValueError('diagnostic already attempted; never redispatch')
        save(root/'started.json', {'schema': schema+'.started', 'plan_sha256': p['content_sha256'],
            'pid': os.getpid(), 'resource_files': evidence, 'started_utc': datetime.now(timezone.utc).isoformat()})
        execution = run_bounded([sys.executable, '-m', worker_module, 'worker', '--output', str(root)],
            seconds=p['worker_wall_seconds'], cwd=ROOT)
        terminal = read(root/'worker-terminal.json') if (root/'worker-terminal.json').exists() else None
        save(root/'terminal.json', {'schema': schema+'.terminal', 'execution': execution,
            'worker_terminal': terminal, 'source_commit': p['source_commit'],
            'status': 'closed-diagnostic-only' if terminal and execution['returncode'] == 0 else 'stopped',
            'redispatch_allowed': False, 'scientific_worlds': 0, 'actions_executed': 0,
            'production_certificate_issued': False, 'scientific_dispatch_authorized': False})
        if execution['returncode'] != 0:
            raise ValueError('capacity diagnostic worker stopped; no retry or scientific dispatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run', 'worker'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--origin-run', type=Path); parser.add_argument('--audit', type=Path, action='append')
    parser.add_argument('--resources', type=Path)
    args = parser.parse_args(); out = args.output.resolve()
    if not out.is_relative_to(ROOT/'outputs'): raise ValueError('fresh ignored output below diagnostic source required')
    if args.command == 'prepare':
        require_environment()
        if out.exists() or args.origin_run is None or not args.audit: raise ValueError('fresh output/original fixture required')
        p = make_plan(args.origin_run, args.audit, pinned_revision(ROOT))
        out.mkdir(parents=True); save(out/'plan.json', p); require_plan(out)
        print(json.dumps({'prepared': str(out), 'maximum_chat_POSTs': 2, 'new_model_POSTs': 0}))
    elif args.command == 'run':
        if args.resources is None: raise ValueError('fresh resource proof required')
        run(out, args.resources)
    else: worker(out)


if __name__ == '__main__': main()
