"""Selection-fixed workflow evaluation, independent of stopped other studies.

No author, repair, reselection or scientific dispatch by preparation. All
declared controls/own labels stay; only exact policy identity shares jobs.
"""
import argparse
import fcntl
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.native_benchmark_seed_usage import usage_inventory, software_fixture_policy, require_inventory_policy
from scripts.run_native_objective_fixed_evaluation_v1 import fixed_selection, jobs_for, run as run_shared
from scripts.run_native_objective_instrument_loop_v1 import measure_with, utc
from scripts.run_native_workflow_objective_loop_v1 import scientist_factory, native_sources, open_institutions, OPEN_SCOPE
from scripts.run_pre_scale_search_v1 import require_environment
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.common_content_observer import make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_workflow_domain_v4 import require_workflow_candidate, verify_workflow_interval
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-workflow-fixed-evaluation.v1'
PROTOCOL = 'research/protocols/campaigns/native-workflow-fixed-evaluation-v1.md'
OPEN_PROTOCOL = 'research/protocols/campaigns/native-open-workflow-fixed-evaluation-v1.md'
SEED_SOFTWARE_PROTOCOL = 'research/protocols/campaigns/native-workflow-feedback-fixed-evaluation-v3.md'
REFERENCES = ['R7-original', 'post-funding-cost']


def read(path): return checked(json.loads(Path(path).read_text()))


def seeded_anchor(plan, seed):
    value = clone(plan['initial_system']); value['initial_state']['seed'] = seed
    return SystemSpec.from_dict(value)


def interval(plan, system, events, seed):
    return verify_workflow_interval(seeded_anchor(plan, seed), system, events, years=4)


def build_plan(original, audit, *, source, origin, usages, seeds, observer_backend, source_proof,
        software_exclusions=None):
    opened = open_institutions(original)
    protocol = OPEN_PROTOCOL if opened else PROTOCOL
    selected = fixed_selection(original, audit, study='workflow-v1')
    if (original['objectives'] != ['throughput', 'content-utility'] or original['generations'] != 3
            or original['reference_order'] != REFERENCES or original['held_out_evaluation']
            or audit['closure']['terminal']['consumed_slots'] != 6
            or source_proof['original_source'] != original['source_commit']
            or not isinstance(seeds, list) or not 1 <= len(seeds) <= 3
            or len(set(seeds)) != len(seeds) or any(type(s) is not int or not 0 <= s < 2**31 or s == 61001 for s in seeds)):
        raise ValueError('normally closed six-slot workflow and explicit unused finite world seeds required')
    if (len(source) != 40 or any(c not in '0123456789abcdef' for c in source) or not usages
            or any(not u['valid'] or u['errors'] or u['prior_matching_runs'] or u['seeds'] != seeds for u in usages)):
        raise ValueError('exact source and unconsumed seed inventories required')
    observer = make_contract(source_commit=source, provider={k: original['scientist'][k] for k in ('model', 'model_digest')},
        backend=observer_backend, maximum_posts=3000, critics=3)
    ignore = {'source_commit', 'content_sha256', 'maximum_posts'}
    if {k: v for k, v in original['observer_contract'].items() if k not in ignore} != {
            k: v for k, v in observer.items() if k not in ignore}:
        raise ValueError('fixed native content observer changed')
    experiment = {'protocol': protocol, 'role': 'selection-frozen-workflow-evaluation'}
    result = {'schema': SCHEMA + '.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': protocol, 'protocol_sha256': file_sha256(ROOT / protocol), 'origin': clone(origin),
        'origin_audit_content_sha256': audit['content_sha256'],
        'origin_selection_sha256': selected['content_sha256'], 'original_native_sources': clone(source_proof),
        **{k: clone(original[k]) for k in ('scientist', 'designer', 'data_cache', 'losses', 'objectives', 'catalog', 'initial_system')},
        'fixed_selection': selected, 'reference_systems': clone(original['reference_systems']),
        'world': {**clone(original['world']), 'source_commit': source, 'experiment': experiment,
            'measurement_adapter_contract': observer, 'classification': ('actual-native-open-workflow-fixed-evaluation-v1'
                if opened else 'actual-native-workflow-fixed-evaluation-v1')},
        'experiment': experiment, 'observer_contract': observer,
        'evaluation': {'seeds': clone(seeds), 'reference_labels': clone(REFERENCES),
            'maximum_physical_worlds': 4 * len(seeds), 'seed_usage': [u['content_sha256'] for u in usages]},
        'budget': {'scientist_HTTP_attempts_per_world': 1024, 'world_wall_seconds': 7200,
            'observer_POSTs_upper_bound': 3000, 'designer_generation_POSTs': 0, 'replace_failed_slots': False},
        'claims': {'independent_optimizer_replications': False, 'scientific_truth': False,
            'publication_ready': False, 'candidate_reselection': False, 'new_institution_design': False}}
    if opened: result['origin_authoring_scope'] = OPEN_SCOPE
    if software_exclusions is not None:
        policy = software_fixture_policy(software_exclusions)
        for u in usages: require_inventory_policy(u, policy)
        result['seed_software_exclusions'] = clone(policy)
        result['seed_inventory_protocol'] = {'path': SEED_SOFTWARE_PROTOCOL,
            'sha256': file_sha256(ROOT / SEED_SOFTWARE_PROTOCOL)}
    if 'scientist_transport' in original:
        from utopia.optimization.native_scientist_transport_v1 import contract, validate, PROTOCOL as operational
        transport = validate(original['scientist_transport'])
        if (transport != contract(read_seconds=900) or original['operational_protocol'] != {
                'path': operational, 'sha256': file_sha256(ROOT / operational)}):
            raise ValueError('literal original scientist900 profile and operational protocol required')
        result['scientist_transport'] = transport
        result['operational_protocol'] = clone(original['operational_protocol'])
    result['jobs'] = jobs_for(result)
    for job in result['jobs']:
        require_workflow_candidate(seeded_anchor(result, job['seed']), SystemSpec.from_dict(job['system']), structure_only=not opened)
    return result


def origin_evidence(origin):
    root, source = Path(origin['run']), Path(origin['source'])
    if pinned_revision(source) != origin['source_commit']: raise ValueError('original workflow source changed')
    audits = [read(path) for path in origin['audit_files']]
    if (len(audits) != 2 or audits[0] != audits[1]
            or any(file_sha256(Path(path)) != h for path, h in origin['audit_files'].items())):
        raise ValueError('two unchanged matching original workflow audits required')
    a = audits[0]; p = read(root / 'plan.json'); before = _inventory(root)
    if (digest(before) != a['raw_inventory_sha256'] or len(before) != a['raw_files']
            or read(root / 'started.json') != a['closure']['started']
            or read(root / 'terminal.json') != a['closure']['terminal'] or read(root / 'selection.json') != a['selection']):
        raise ValueError('audited workflow raw/closure/selection changed')
    fixed_selection(p, a, study='workflow-v1'); return p, a


def require_plan(root):
    p = read(root / 'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean workflow evaluation source/runtime required')
    original, audit = origin_evidence(p['origin'])
    usages = [read(root / f'seed-usage-{i:02}.json') for i in range(len(p['evaluation']['seed_usage']))]
    expected = build_plan(original, audit, source=p['source_commit'], origin=p['origin'], usages=usages,
        seeds=p['evaluation']['seeds'], observer_backend=p['observer_contract']['backend'],
        source_proof=native_sources(original['source_commit']),
        software_exclusions=p.get('seed_software_exclusions'))
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal workflow evaluation reconstruction differs')
    return p


def prepare(args):
    require_environment(); source = pinned_revision(ROOT)
    if (args.output.exists() or args.output.is_relative_to(args.origin_run.resolve())
            or not args.seed_usage_root or any(not p.is_dir() for p in args.seed_usage_root)):
        raise ValueError('fresh separate output and existing explicit seed roots required')
    a = read(args.audit_one)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
        'source_commit': a['source_commit'], 'audit_files': {
            str(p.resolve()): file_sha256(p) for p in (args.audit_one, args.audit_two)}}
    with (args.origin_run / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB); original, audit = origin_evidence(origin)
        policy_file = getattr(args, 'seed_software_exclusions', None)
        policy = None if policy_file is None else software_fixture_policy(read(policy_file))
        usages = [usage_inventory(p, args.evaluation_seed, **({} if policy is None else {
            'software_exclusions': policy})) for p in args.seed_usage_root]
        # The optional prospective policy route retains inventories even when
        # they reject preparation. No failed seed proof disappears from memory.
        if policy is not None:
            args.output.mkdir(parents=True)
            save(args.output / 'preparation-started.json', {'started_utc': utc(),
                'source_commit': source, 'software_fixture_policy_sha256': policy['content_sha256'],
                'new_model_calls': 0})
            for i, u in enumerate(usages):
                save(args.output / f'seed-usage-{i:02}.json', {k: v for k, v in u.items() if k != 'content_sha256'})
        try:
            p = build_plan(original, audit, source=source, origin=origin, usages=usages, seeds=args.evaluation_seed,
                observer_backend=backend_binding({k: original['scientist'][k] for k in ('model', 'model_digest')}),
                source_proof=native_sources(original['source_commit']), software_exclusions=policy)
            if policy is None:
                args.output.mkdir(parents=True)
                for i, u in enumerate(usages):
                    save(args.output / f'seed-usage-{i:02}.json', {k: v for k, v in u.items() if k != 'content_sha256'})
            save(args.output / 'plan.json', p); require_plan(args.output)
        except BaseException as error:
            if policy is not None:
                save(args.output / 'preparation-ended.json', {'status': 'stopped', 'ended_utc': utc(),
                    'error_type': type(error).__name__, 'error': str(error), 'new_model_calls': 0})
            raise
        if policy is not None:
            save(args.output / 'preparation-ended.json', {'status': 'prepared', 'ended_utc': utc(),
                'new_model_calls': 0})
    print(json.dumps({'prepared_source': source, 'physical_jobs': len(p['jobs']), 'designer_POSTs': 0}), flush=True)


def observe(root, p, job, observer):
    directory = root / 'evaluation' / job['identity']
    if (directory / 'started.json').exists(): raise ValueError('consumed workflow evaluation job; no redispatch')
    suggestion = Suggestion(job['identity'], job['system'], 0, 'selection-fixed-evaluation')
    save(directory / 'started.json', {**clone(job), 'suggestion': suggestion.to_dict(), 'started_utc': utc()})
    measure = measure_with(observer, p['observer_contract'])
    def measured(sim, base):
        return {**measure(sim, base), 'native_workflow_interval': interval(p, sim.native_system.spec,
            sim.native_system.events, job['seed'])}
    o = evaluate_native_suggestion(suggestion, seeds=[job['seed']],
        simulation_factory=scientist_factory(directory / 'worlds', p, root),
        loss_spec=p['losses']['throughput'], measurement_adapter=measured).to_dict()
    save(directory / 'observation.json', o)
    save(directory / 'cross-scores.json', {k: evaluate_loss(v, o['metadata']['measurements']) for k, v in p['losses'].items()})


def run(root):
    p = require_plan(root)
    extra = {}
    if 'seed_software_exclusions' in p:
        extra['inventory_fn'] = lambda inventory_root, seeds: usage_inventory(inventory_root, seeds,
            software_exclusions=p['seed_software_exclusions'])
    return run_shared(root, require_plan_fn=require_plan, observe_fn=observe, schema=SCHEMA, **extra)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('stage', choices=('prepare', 'run'))
    parser.add_argument('--output', type=Path, required=True)
    for key in ('origin-run', 'origin-source', 'audit-one', 'audit-two'): parser.add_argument('--' + key, type=Path)
    parser.add_argument('--seed-usage-root', type=Path, action='append')
    parser.add_argument('--evaluation-seed', type=int, action='append')
    parser.add_argument('--seed-software-exclusions', type=Path)
    args = parser.parse_args(); args.output = args.output.resolve()
    if args.stage == 'prepare':
        if any(getattr(args, k) is None for k in ('origin_run', 'origin_source', 'audit_one', 'audit_two', 'evaluation_seed')):
            parser.error('explicit normally closed workflow origin and unused seeds required')
        prepare(args)
    else: run(args.output)


if __name__ == '__main__': main()
