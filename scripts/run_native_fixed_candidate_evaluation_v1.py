"""Prospective evaluation of fixed submissions from an explicitly stopped pilot.

No authoring, calibration, refills or fallback. This is a separate study, not
completion of the original search. Failed-only arms have no selected policy.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.native_benchmark_seed_usage import usage_inventory
from scripts.native_design_benchmark_plan import policy_identity
from scripts.run_pre_scale_search_v1 import require_environment, observe, evaluation_jobs
from utopia.optimization.native_designer_preflight import runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-fixed-candidate-evaluation.v1'
PROTOCOL = 'research/protocols/campaigns/native-fixed-candidate-evaluation-v1.md'
SEEDS = (62001, 62011, 62017)
REFERENCES = ('open-seed', 'legacy', 'reviewed-accept-all', 'no-review-accept-all',
              'routed-one-accept-all', 'routed-two-accept-all')


def read(path): return checked(json.loads(Path(path).read_text()))
def utc(): return datetime.now(timezone.utc).isoformat()


def fixed_selection(original, audit):
    """Original chronological first tie, completed authored submissions only."""
    if (audit['schema'] != 'scienceutopia.native-institution-loop-stopped-audit.v1'
            or audit['plan_sha256'] != original['content_sha256']
            or audit['source_commit'] != original['source_commit']
            or audit['closure'].get('scientific_study_closed') is not False
            or audit['closure']['terminal']['status'] != 'stopped'
            or audit.get('selection') is not None or audit.get('logical_evaluation') != []
            or audit['new_model_calls'] != 0 or audit['new_code_executions'] != 0
            or audit['source_proof']['status'] != 'verified-exact-source-closure'):
        raise ValueError('exact stopped-prefix audit required; never manufacture closed search')
    rows = audit['worlds']; selected = {}
    for arm in original['arm_order']:
        objective = original['assignments'][arm]['objective']
        pool = [w for w in rows if w['role'] == 'search:'+arm]
        valid = [w for w in pool if w['status'] == 'complete' and w['scores'][objective] is not None]
        best = min((w['scores'][objective] for w in valid), default=None)
        tied = [w for w in valid if w['scores'][objective] == best]
        first = tied[0] if tied else None
        selected[arm] = {'loss': best, 'submitted_worlds': len(pool),
            'complete_candidates': len(valid), 'all_tied_ids': [w['identity'] for w in tied],
            'selected_id': None if first is None else first['identity'],
            'system': None if first is None else clone(first['system']),
            'policy_sha256': None if first is None else policy_identity(first['system']),
            'status': 'no-completed-submission' if first is None else 'selected'}
    return {'selected': selected, 'all_attempts': clone(audit['closure']['progress']['candidate_slots']),
        'unsubmitted_slots': audit['closure']['unsubmitted_slots'],
        'missing_slot': clone(audit['closure']['next_unsubmitted_slot']),
        'reference_systems': {k: clone(original['reference_systems'][k]) for k in REFERENCES},
        'selection_rule': 'minimum original assigned loss among completed submissions; first chronological tie',
        'common_initial_in_selection': False, 'baseline_fallback': False}


def build_plan(original, audit, *, source, origin, usages):
    if not isinstance(source, str) or len(source) != 40 or any(c not in '0123456789abcdef' for c in source):
        raise ValueError('exact full evaluation source revision required')
    selection = fixed_selection(original, audit)
    if not usages or any(not u['valid'] or u['errors'] or u['prior_matching_runs'] or u['seeds'] != list(SEEDS)
                         for u in usages):
        raise ValueError('explicit unused evaluation seeds required')
    experiment = {'protocol': PROTOCOL, 'role': 'fixed-submissions-after-known-search-stop'}
    world = {**clone(original['world']), 'source_commit': source, 'experiment': experiment,
        'classification': 'actual-native-fixed-candidate-evaluation-v1'}
    result = {'schema': SCHEMA+'.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT/PROTOCOL),
        'origin': clone(origin), 'origin_audit_content_sha256': audit['content_sha256'],
        'scientist': clone(original['scientist']), 'designer': clone(original['designer']),
        'data_cache': original['data_cache'], 'world': world, 'experiment': experiment,
        'losses': clone(original['losses']), 'objectives': ['throughput', 'efficiency'],
        'arm_order': list(original['arm_order']),
        'fixed_selection': selection, 'reference_systems': selection['reference_systems'],
        'evaluation': {'seeds': list(SEEDS), 'reference_labels': list(REFERENCES),
            'maximum_physical_worlds': 30, 'seed_usage': [u['content_sha256'] for u in usages]},
        'budget': {'native_worlds_upper_bound': 30, 'scientist_HTTP_attempts_per_world': 1024,
            'designer_generation_POSTs': 0, 'years': 4, 'researchers': 5, 'refill': False},
        'claims': {'original_study_completed': False, 'equal_search_budgets': False,
            'independent_optimizer_replications': False, 'method_superiority': False,
            'scientific_truth': False, 'loss_or_objective_changed': False}}
    # Reuse only exact policy deduplication and seed projection, not selection.
    result['jobs'] = jobs_for(result)
    return result


def jobs_for(plan):
    # Bind the input to this pure projection before jobs are part of final plan.
    # Both arguments satisfy the reused helper's actual content-hash contract.
    projection = {k:v for k,v in plan.items() if k not in ('content_sha256','jobs')}
    projection['content_sha256'] = digest(projection)
    selection = {'plan_sha256':projection['content_sha256'],
        'selected':{arm:plan['fixed_selection']['selected'][arm] for arm in plan['arm_order']}}
    selection['content_sha256'] = digest(selection)
    return evaluation_jobs(projection, selection)


def origin_evidence(origin):
    root, source = Path(origin['run']), Path(origin['source'])
    if pinned_revision(source) != origin['source_commit']:
        raise ValueError('original scientific source changed')
    if any(file_sha256(Path(p)) != h for p, h in origin['audit_files'].items()):
        raise ValueError('original stopped audit changed')
    audits = [read(p) for p in origin['audit_files']]
    if len(audits) != 2 or audits[0] != audits[1]:
        raise ValueError('two matching exact stopped audits required')
    a = audits[0]
    if (digest(_inventory(root)) != a['raw_inventory_sha256']
            or read(root/'terminal.json') != a['closure']['terminal']):
        raise ValueError('stopped raw origin differs from audited bytes')
    return read(root/'plan.json'), a


def prepare(args):
    require_environment()
    source = pinned_revision(ROOT)
    if args.output.exists(): raise ValueError('new evaluation output required')
    if args.output.is_relative_to(args.origin_run.resolve()) or args.output.is_relative_to(args.origin_source.resolve()):
        raise ValueError('new evaluation cannot write inside the stopped source/raw')
    if args.audit_a.read_bytes() != args.audit_b.read_bytes(): raise ValueError('cold audits differ')
    a = read(args.audit_a)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
        'source_commit': a['source_commit'],
        'audit_files': {str(p.resolve()): file_sha256(p) for p in (args.audit_a, args.audit_b)}}
    with (args.origin_run/'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original, audit = origin_evidence(origin)
        usages = [usage_inventory(p, SEEDS) for p in args.seed_usage_root]
        plan = build_plan(original, audit, source=source, origin=origin, usages=usages)
        args.output.mkdir(parents=True)
        for i, u in enumerate(usages):
            save(args.output/f'seed-usage-{i}.json', {k:v for k,v in u.items() if k != 'content_sha256'})
        save(args.output/'plan.json', plan)
    print(json.dumps({'prepared': source, 'jobs': len(plan['jobs']), 'designer_POSTs': 0}), flush=True)


def require_plan(root):
    p = read(root/'plan.json')
    if (p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding()
            or p['protocol_sha256'] != file_sha256(ROOT/PROTOCOL) or p['jobs'] != jobs_for(p)):
        raise ValueError('fixed evaluation source/runtime/protocol/jobs changed')
    return p


def run(root):
    require_environment(); p = require_plan(root); p['_output'] = str(root)
    with (root/'writer.lock').open('a') as owner, (Path(p['origin']['run'])/'writer.lock').open('r') as origin_lock:
        for handle in (owner, origin_lock): fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original, audit = origin_evidence(p['origin'])
        if fixed_selection(original, audit) != p['fixed_selection']:
            raise ValueError('fixed selection differs from stopped submissions')
        usage_paths = sorted(root.glob('seed-usage-*.json'))
        usages = [read(path) for path in usage_paths]
        if [u['content_sha256'] for u in usages] != p['evaluation']['seed_usage']:
            raise ValueError('original seed-usage receipts changed or disappeared')
        rebuilt = build_plan(original, audit, source=p['source_commit'], origin=p['origin'], usages=usages)
        if rebuilt != {k:v for k,v in p.items() if k not in ('content_sha256','_output')}:
            raise ValueError('evaluation plan differs from deterministic original-source reconstruction')
        for path in usage_paths:
            receipt = usage_inventory(read(path)['root'], SEEDS)
            if not receipt['valid']:
                raise ValueError('evaluation seeds consumed after preparation; do not dispatch')
            save(root/('pre-dispatch-'+path.name), {k:v for k,v in receipt.items() if k != 'content_sha256'})
        save(root/'started.json', {'schema': SCHEMA+'.start', 'pid': os.getpid(),
            'plan_sha256': p['content_sha256'], 'started_utc': utc()})
        end = {'schema': SCHEMA+'.terminal', 'status': 'closed'}; completed = 0
        try:
            for job in p['jobs']:
                require_plan(root)
                write_json_atomic(root/'progress.json', {'stage':'fixed-evaluation', 'active':job['identity'],
                    'observed_utc':utc(), 'complete_jobs':completed, 'total_jobs':len(p['jobs'])})
                o = observe(root/'evaluation'/job['identity'], p, job['identity'], job['system'], job['seed'],
                            'selection-fixed-evaluation')
                if o['status'] != 'complete': raise ValueError('evaluation failed; no retry, refill or next world')
                completed += 1
                print(json.dumps({'complete_jobs':completed, 'total_jobs':len(p['jobs']),
                    'identity':job['identity'], 'labels':job['labels']}), flush=True)
        except BaseException as error:
            end.update(status='stopped', error_type=type(error).__name__, error=str(error))
            raise
        finally:
            end.update(ended_utc=utc(), completed_jobs=completed)
            save(root/'terminal.json', end)
            write_json_atomic(root/'progress.json', {'stage':end['status'], 'active':None,
                'observed_utc':utc(), 'complete_jobs':completed, 'total_jobs':len(p['jobs'])})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('prepare','run')); p.add_argument('--output', type=Path, required=True)
    for name in ('origin-run','origin-source','audit-a','audit-b'): p.add_argument('--'+name, type=Path)
    p.add_argument('--seed-usage-root', type=Path, action='append', default=[])
    a = p.parse_args(); a.output = a.output.resolve()
    if a.stage == 'prepare':
        if not all(getattr(a, k) for k in ('origin_run','origin_source','audit_a','audit_b','seed_usage_root')):
            p.error('prepare requires original source/raw, two audits, explicit seed-usage roots')
        prepare(a)
    else: run(a.output)


if __name__ == '__main__': main()
