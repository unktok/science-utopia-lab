"""Frozen four-history selections and two references on the reserved unused seed."""
import argparse
import fcntl
import json
from pathlib import Path

from scripts import run_native_longitudinal_comparison_v1 as development
from scripts import run_native_workflow_fixed_evaluation_v1 as workflow
from scripts.analyze_native_open_v7 import _inventory
from scripts.native_benchmark_seed_usage import usage_inventory, software_fixture_policy, require_inventory_policy
from scripts.run_native_objective_fixed_evaluation_v1 import jobs_for, run as run_shared
from utopia.optimization.common_content_observer import make_contract
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = development.ROOT
SCHEMA = 'scienceutopia.native-longitudinal-fixed-evaluation.v1'
PROTOCOL = 'research/protocols/campaigns/native-longitudinal-fixed-evaluation-v1.md'
REFERENCES = workflow.REFERENCES
read, save, utc = development.read, development.save, development.utc
observe, interval = workflow.observe, workflow.interval


def fixed_selection(original, audit):
    from utopia.optimization.native_numeric_designer import checked
    checked(original); checked(audit)
    selected = audit['selection']; checked(selected)
    keys = ['::'.join(k) for k in development.history_keys(original)]
    if (original['schema'] != development.SCHEMA+'.plan' or audit['schema'] != development.AUDIT_SCHEMA
            or audit['source_commit'] != original['source_commit']
            or audit['plan_sha256'] != original['content_sha256']
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['closure']['terminal']['status'] != 'closed'
            or audit['closure']['terminal']['consumed_slots'] != 12
            or audit['new_model_calls'] or audit['new_code_executions'] or audit['held_out_evaluation']
            or selected['plan_sha256'] != original['content_sha256']
            or selected['schema'] != development.SCHEMA+'.selection'
            or selected['baseline_fallback'] or selected['held_out_evaluation']
            or set(selected['selected']) != set(keys)):
        raise ValueError('normally closed exact four-history own selection required')
    for arm, objective in development.history_keys(original):
        pool = [w for w in audit['worlds'] if w['role'] == 'workflow-own-proposal'
            and w['arm'] == arm and w['objective'] == objective and w['status'] == 'complete']
        best = min((w['scores'][objective] for w in pool), default=None)
        ties = [w for w in pool if w['scores'][objective] == best]
        expected = {'arm': arm, 'objective': objective, 'loss': best, 'completed_submissions': len(pool),
            'all_tied_ids': [w['identity'] for w in ties],
            'selected_id': ties[0]['identity'] if ties else None,
            'system': clone(ties[0]['system']) if ties else None}
        if selected['selected'][arm+'::'+objective] != expected:
            raise ValueError('literal own minimum/chronological-first-tie pool differs')
    return clone(selected)


def origin_evidence(origin):
    root, source = Path(origin['run']), Path(origin['source'])
    if pinned_revision(source) != origin['source_commit']:
        raise ValueError('frozen comparison source changed')
    audits = [read(p) for p in origin['audit_files']]
    if (len(audits) != 2 or audits[0] != audits[1]
            or any(file_sha256(p) != h for p, h in origin['audit_files'].items())):
        raise ValueError('two unchanged matching comparison audits required')
    a = audits[0]; p = read(root/'plan.json'); before = _inventory(root)
    if (digest(before) != a['raw_inventory_sha256'] or len(before) != a['raw_files']
            or read(root/'started.json') != a['closure']['started']
            or read(root/'terminal.json') != a['closure']['terminal']
            or read(root/'selection.json') != a['selection']):
        raise ValueError('audited comparison raw/closure/selection changed')
    fixed_selection(p, a)
    return p, a


def build_plan(original, audit, *, source, origin, usages, seeds, observer_backend, source_proof,
        software_exclusions=None):
    selected = fixed_selection(original, audit)
    if (seeds != original['reserved_unused_seeds'] or len(seeds) != 1
            or type(seeds[0]) is not int or not 0 <= seeds[0] < 2**31 or seeds[0] == development.SEED
            or original['objectives'] != list(development.OBJECTIVES)
            or original['arms'] != list(development.ARMS) or original['reference_order'] != REFERENCES
            or source_proof['original_source'] != original['source_commit']
            or len(source) != 40 or any(c not in '0123456789abcdef' for c in source)
            or not usages or any(not u['valid'] or u['errors'] or u['prior_matching_runs']
                or u['seeds'] != seeds for u in usages)):
        raise ValueError('reserved unused condition and exact prospective source/inventories required')
    observer = make_contract(source_commit=source,
        provider={k: original['scientist'][k] for k in ('model', 'model_digest')},
        backend=observer_backend, maximum_posts=3000, critics=3)
    ignore = {'source_commit', 'content_sha256', 'maximum_posts'}
    if {k: v for k, v in original['observer_contract'].items() if k not in ignore} != {
            k: v for k, v in observer.items() if k not in ignore}:
        raise ValueError('fixed common content observer changed')
    experiment = {'protocol': PROTOCOL, 'role': 'selection-frozen-longitudinal-comparison-evaluation'}
    p = {'schema': SCHEMA+'.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT/PROTOCOL), 'origin': clone(origin),
        'origin_audit_content_sha256': audit['content_sha256'], 'origin_selection_sha256': selected['content_sha256'],
        'original_native_sources': clone(source_proof), 'fixed_selection': selected,
        **{k: clone(original[k]) for k in ('scientist', 'designer', 'data_cache', 'losses', 'objectives',
            'catalog', 'initial_system', 'reference_systems', 'arms')},
        'selection_order': ['::'.join(k) for k in development.history_keys(original)],
        'origin_authoring_scope': development.base.OPEN_SCOPE,
        'world': {**clone(original['world']), 'source_commit': source, 'experiment': experiment,
            'measurement_adapter_contract': observer, 'classification': 'actual-native-longitudinal-fixed-evaluation-v1'},
        'experiment': experiment, 'observer_contract': observer,
        'evaluation': {'seeds': clone(seeds), 'reference_labels': clone(REFERENCES),
            'maximum_physical_worlds': 6, 'seed_usage': [u['content_sha256'] for u in usages]},
        'budget': {'scientist_HTTP_attempts_per_world': 1024, 'world_wall_seconds': 7200,
            'observer_POSTs_upper_bound': 3000, 'designer_generation_POSTs': 0, 'replace_failed_slots': False},
        'claims': {'independent_optimizer_replications': False, 'scientific_truth': False,
            'publication_ready': False, 'candidate_reselection': False, 'new_institution_design': False}}
    if 'scientist_transport' in original:
        p['scientist_transport'] = clone(original['scientist_transport'])
        p['operational_protocol'] = clone(original['operational_protocol'])
    if software_exclusions is not None:
        policy = software_fixture_policy(software_exclusions)
        for u in usages: require_inventory_policy(u, policy)
        p['seed_software_exclusions'] = clone(policy)
        p['seed_inventory_protocol'] = {'path': workflow.SEED_SOFTWARE_PROTOCOL,
            'sha256': file_sha256(ROOT/workflow.SEED_SOFTWARE_PROTOCOL)}
    p['jobs'] = jobs_for(p)
    from utopia.optimization.native_workflow_domain_v4 import require_workflow_candidate
    for job in p['jobs']:
        require_workflow_candidate(workflow.seeded_anchor(p, job['seed']),
            SystemSpec.from_dict(job['system']), structure_only=False)
    return p


def require_plan(root):
    p = read(root/'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean longitudinal fixed source/runtime required')
    original, audit = origin_evidence(p['origin'])
    usages = [read(root/f'seed-usage-{i:02}.json') for i in range(len(p['evaluation']['seed_usage']))]
    expected = build_plan(original, audit, source=p['source_commit'], origin=p['origin'], usages=usages,
        seeds=p['evaluation']['seeds'], observer_backend=p['observer_contract']['backend'],
        source_proof=development.base.native_sources(original['source_commit']),
        software_exclusions=p.get('seed_software_exclusions'))
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal longitudinal fixed reconstruction differs')
    return p


def prepare(args):
    development.base.require_environment(); source = pinned_revision(ROOT)
    if (args.output.exists() or args.output.resolve().is_relative_to(args.origin_run.resolve())
            or not args.seed_usage_root or any(not p.is_dir() for p in args.seed_usage_root)):
        raise ValueError('fresh separate fixed output and explicit broad inventory roots required')
    a = read(args.audit_one)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
        'source_commit': a['source_commit'], 'audit_files': {
            str(p.resolve()): file_sha256(p) for p in (args.audit_one, args.audit_two)}}
    with (args.origin_run/'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original, audit = origin_evidence(origin)
        policy = None if args.seed_software_exclusions is None else software_fixture_policy(read(args.seed_software_exclusions))
        usages = [usage_inventory(p, original['reserved_unused_seeds'], **({} if policy is None else {
            'software_exclusions': policy})) for p in args.seed_usage_root]
        args.output.mkdir(parents=True)
        save(args.output/'preparation-started.json', {'started_utc': utc(), 'source_commit': source, 'new_model_calls': 0})
        for i, u in enumerate(usages):
            save(args.output/f'seed-usage-{i:02}.json', {k: v for k, v in u.items() if k != 'content_sha256'})
        try:
            p = build_plan(original, audit, source=source, origin=origin, usages=usages,
                seeds=original['reserved_unused_seeds'], observer_backend=backend_binding(original['scientist']),
                source_proof=development.base.native_sources(original['source_commit']), software_exclusions=policy)
            save(args.output/'plan.json', p); require_plan(args.output)
        except BaseException as error:
            save(args.output/'preparation-ended.json', {'status': 'stopped', 'ended_utc': utc(),
                'error_type': type(error).__name__, 'error': str(error), 'new_model_calls': 0})
            raise
        save(args.output/'preparation-ended.json', {'status': 'prepared', 'ended_utc': utc(), 'new_model_calls': 0})
    print(json.dumps({'source': source, 'physical_jobs': len(p['jobs']), 'designer_POSTs': 0}), flush=True)


def run(root):
    p = require_plan(root)
    extra = {} if 'seed_software_exclusions' not in p else {'inventory_fn': lambda r, seeds:
        usage_inventory(r, seeds, software_exclusions=p['seed_software_exclusions'])}
    return run_shared(root, require_plan_fn=require_plan, observe_fn=observe, schema=SCHEMA, **extra)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('stage', choices=('prepare', 'run'))
    parser.add_argument('--output', type=Path, required=True)
    for name in ('origin-run', 'origin-source', 'audit-one', 'audit-two'): parser.add_argument('--'+name, type=Path)
    parser.add_argument('--seed-usage-root', type=Path, action='append')
    parser.add_argument('--seed-software-exclusions', type=Path)
    args = parser.parse_args()
    if args.stage == 'prepare':
        if any(getattr(args, n) is None for n in ('origin_run', 'origin_source', 'audit_one', 'audit_two')):
            parser.error('explicit closed comparison origin and two audits required')
        prepare(args)
    else: run(args.output)


if __name__ == '__main__': main()
