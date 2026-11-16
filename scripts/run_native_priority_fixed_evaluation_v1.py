"""Unused-condition evaluation of the exact twelve mixed-study own selections.

Preparation is read-only with respect to the original study. No authoring,
repair, reselection, failed-slot refill or reference fallback is possible.
This new route needs public native/cold verification before real dispatch.
"""
import argparse
import fcntl
from pathlib import Path
import subprocess

from scripts.analyze_native_open_v7 import _inventory
from scripts.native_benchmark_seed_usage import usage_inventory, software_fixture_policy, require_inventory_policy
from scripts.native_priority_fixed_bank_v1 import freeze_bank, planned_jobs
from scripts.reports.native_priority_method_readout_v1 import collect, analyze, SCHEMA as READOUT_SCHEMA
from scripts.run_native_objective_fixed_evaluation_v1 import run as run_shared
from scripts.run_native_objective_instrument_loop_v1 import measure_with, utc
from scripts.run_native_topic_free_optimization_v1 import require_candidate, verify_interval
from scripts.run_native_workflow_objective_loop_v1 import scientist_factory, native_sources as original_native_sources
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.common_content_observer import make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_resource_cost import measure as resource_measure
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import decode_json, file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-priority-fixed-evaluation.v1'
PROTOCOL = 'research/protocols/campaigns/native-priority-fixed-evaluation-v1.md'
SEEDS = [83003, 83011]


def read(path):
    return checked(decode_json(Path(path).read_text(), strict=True, finite_floats=True))


def native_sources(original):
    # Fixed evaluation never calls the designer. Still bind the prospective
    # visibility fix explicitly rather than excluding another file or allowing
    # arbitrary native drift. Same-source closure needs no invented adapter.
    source = pinned_revision(ROOT)
    names = {
        'utopia/optimization/native_authoring_recovery_v44.py': 'Designer-only workflow visibility correction',
        'utopia/optimization/native_component_lab_v1.py': 'Explicit optional designer component parameter contexts',
        'utopia/optimization/native_post_edit_feedback_v1.py': 'Explicit optional designer post-edit parameter diagnostics',
        'utopia/optimization/native_workflow_staged_designer_v1.py': 'Explicit attributed designer fixture-bank overlay',
    }
    adapters = {}
    for name, role in names.items():
        before = subprocess.check_output(['git', 'show', original + ':' + name], cwd=ROOT)
        if (ROOT / name).read_bytes() != before:
            adapters[name] = {'source_commit': source, 'role': role + '; designer is not called by fixed evaluation'}
    return original_native_sources(original, adapters=adapters)


def evidence_files(origin):
    raw, analysis, reports = (Path(origin[k]) for k in ('run', 'analysis', 'readouts'))
    return ([raw / name for name in ('plan.json', 'started.json', 'terminal.json', 'selection.json')]
        + [analysis / name for name in ('started.json', 'ended.json', 'audit-1.json', 'audit-2.json', 'costs-1.json', 'costs-2.json')]
        + [reports / name for name in ('started.json', 'ended.json')]
        + [reports / ('report-' + str(i)) / name for i in (1, 2) for name in ('report.json', 'slots.csv', 'manifest.json')])


def origin_evidence(origin):
    raw, analysis, reports = (Path(origin[k]).resolve() for k in ('run', 'analysis', 'readouts'))
    if pinned_revision(Path(origin['source'])) != origin['source_commit']:
        raise ValueError('exact original mixed-study scientific source required')
    files = evidence_files(origin)
    if {str(p): file_sha256(p) for p in files} != origin['input_files']:
        raise ValueError('original science/paired closure/readouts changed')
    p, a, cost = read(raw / 'plan.json'), read(analysis / 'audit-1.json'), read(analysis / 'costs-1.json')
    rs, re = read(reports / 'started.json'), read(reports / 'ended.json')
    # Closure's exclusive orchestration journals are plain JSON, not the sealed
    # scientific save API. Read their exact schema without fabricating a seal.
    end = decode_json((analysis / 'ended.json').read_text(), strict=True, finite_floats=True)
    before = _inventory(raw)
    if (p['source_commit'] != origin['source_commit'] or digest(before) != a['raw_inventory_sha256']
            or len(before) != a['raw_files'] or read(raw / 'started.json') != a['closure']['started']
            or read(raw / 'terminal.json') != a['closure']['terminal'] or read(raw / 'selection.json') != a['selection']
            or end['status'] != 'closed' or end['audit_file_sha256'] != file_sha256(analysis / 'audit-1.json')
            or end['cost_file_sha256'] != file_sha256(analysis / 'costs-1.json')
            or (analysis / 'audit-1.json').read_bytes() != (analysis / 'audit-2.json').read_bytes()
            or (analysis / 'costs-1.json').read_bytes() != (analysis / 'costs-2.json').read_bytes()
            or cost['input_audit_content_sha256'] != a['content_sha256'] or cost['plan_sha256'] != p['content_sha256']
            or cost['raw_inventory_sha256'] != a['raw_inventory_sha256'] or cost['source_commit'] != p['source_commit']
            or rs['scientific_source_commit'] != p['source_commit'] or rs['plan_file_sha256'] != file_sha256(raw / 'plan.json')
            or rs['preceding_analysis'] != str(analysis) or re['status'] != 'closed'
            or re['new_model_calls'] or re['new_native_worlds']):
        raise ValueError('normally closed original study plus paired costs/readouts required')
    for name, expected in re['report_files'].items():
        if (name not in ('report.json', 'slots.csv', 'manifest.json')
                or file_sha256(reports / 'report-1' / name) != expected
                or (reports / 'report-1' / name).read_bytes() != (reports / 'report-2' / name).read_bytes()):
            raise ValueError('exact paired original readout bytes required')
    if set(re['report_files']) != {'report.json', 'slots.csv', 'manifest.json'}:
        raise ValueError('all three original report files required')
    slots, refs = collect(raw, p); projected = analyze(p, a, slots, refs)
    report = read(reports / 'report-1/report.json')
    if report['schema'] != READOUT_SCHEMA or any(report.get(k) != v for k, v in projected.items()):
        raise ValueError('literal complete original readout differs from all-slot projection')
    bank = freeze_bank(p, a, slots, refs)
    if before != _inventory(raw) or {str(f): file_sha256(f) for f in files} != origin['input_files']:
        raise ValueError('original evidence changed during frozen-policy transfer')
    return p, a, bank


def seeded_anchor(p, seed):
    anchor = clone(p['initial_system']); anchor['initial_state']['seed'] = seed
    return SystemSpec.from_dict(anchor)


def interval(p, system, events, seed):
    return verify_interval(seeded_anchor(p, seed), system, events, years=4)


def build_plan(original, audit, bank, *, source, origin, usages, observer_backend, source_proof,
               software_exclusions=None):
    checked(original); checked(audit); checked(bank)
    if (len(source) != 40 or any(c not in '0123456789abcdef' for c in source)
            or source_proof['original_source'] != original['source_commit']
            or bank['origin_plan_content_sha256'] != original['content_sha256']
            or bank['origin_audit_content_sha256'] != audit['content_sha256']
            or bank['origin_selection_content_sha256'] != audit['selection']['content_sha256']
            or not usages or len({u['root'] for u in usages}) != len(usages)):
        raise ValueError('exact source, origin policy bank and explicit unique seed roots required')
    for u in usages:
        checked(u)
        if (u['schema'] != 'scienceutopia.native-benchmark-seed-usage.v4' or not u['strict_path_coverage']
                or not u['valid'] or u['errors'] or u['prior_matching_runs'] or u['seeds'] != SEEDS
                or u['excluded_software_verification_paths']):
            raise ValueError('strict all-path unused-seed inventories for both exact conditions required')
        if software_exclusions is not None: require_inventory_policy(u, software_exclusions)
        elif 'software_fixture_policy_sha256' in u: raise ValueError('inventory exception policy is not declared')
    draft = planned_jobs(bank, clone(SEEDS))
    observer = make_contract(source_commit=source,
        provider={k: original['scientist'][k] for k in ('model', 'model_digest')},
        backend=observer_backend, maximum_posts=6000, critics=3)
    ignored = {'source_commit', 'content_sha256', 'maximum_posts'}
    if {k: v for k, v in observer.items() if k not in ignored} != {
            k: v for k, v in original['observer_contract'].items() if k not in ignored}:
        raise ValueError('fixed scientific observer changed')
    experiment = {'protocol': PROTOCOL, 'role': 'selection-fixed-mixed-method-evaluation'}
    p = {'schema': SCHEMA + '.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT / PROTOCOL), 'origin': clone(origin),
        'origin_audit_content_sha256': audit['content_sha256'], 'original_native_sources': clone(source_proof),
        'origin_selection_content_sha256': audit['selection']['content_sha256'], 'fixed_selection': clone(bank),
        **{k: clone(original[k]) for k in ('scientist', 'designer', 'data_cache', 'losses', 'objectives', 'catalog', 'initial_system')},
        'experiment': experiment, 'observer_contract': observer,
        'world': {**clone(original['world']), 'source_commit': source, 'experiment': experiment,
            'measurement_adapter_contract': observer, 'classification': 'actual-native-priority-fixed-evaluation-v1'},
        'evaluation': {'seeds': clone(SEEDS), 'maximum_physical_worlds': 30,
            'seed_usage': [u['content_sha256'] for u in usages], 'logical_policy_labels': 15,
            'missing_own_selections': clone(bank['missing_own_selections'])}, 'jobs': draft['jobs'],
        'budget': {'scientist_HTTP_attempts_per_world': 1024, 'world_wall_seconds': 7200,
            'observer_POSTs_upper_bound': 6000, 'designer_generation_POSTs': 0, 'replace_failed_slots': False},
        'claims': {'candidate_reselection': False, 'reference_fallback': False, 'new_institution_design': False,
            'independent_optimizer_replications': False, 'scientific_truth': False, 'publication_ready': False}}
    from utopia.optimization.native_scientist_transport_v1 import contract, validate, PROTOCOL as operational
    if (validate(original['scientist_transport']) != contract(read_seconds=900)
            or original['operational_protocol'] != {'path': operational, 'sha256': file_sha256(ROOT / operational)}):
        raise ValueError('literal original scientist900 transport and operational protocol required')
    p['scientist_transport'] = clone(original['scientist_transport'])
    p['operational_protocol'] = clone(original['operational_protocol'])
    if software_exclusions is not None: p['seed_software_exclusions'] = clone(software_fixture_policy(software_exclusions))
    for job in p['jobs']:
        require_candidate(seeded_anchor(p, job['seed']), SystemSpec.from_dict(job['system']))
    return p


def require_plan(root):
    p = read(root / 'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean pinned evaluation source/runtime required')
    original, audit, bank = origin_evidence(p['origin'])
    usages = [read(root / ('seed-usage-' + str(i).zfill(2) + '.json')) for i in range(len(p['evaluation']['seed_usage']))]
    expected = build_plan(original, audit, bank, source=p['source_commit'], origin=p['origin'], usages=usages,
        observer_backend=p['observer_contract']['backend'], source_proof=native_sources(original['source_commit']),
        software_exclusions=p.get('seed_software_exclusions'))
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal fixed evaluation reconstruction differs')
    return p


def strict_inventory(root, seeds, policy=None):
    return usage_inventory(root, seeds, strict_paths=True,
        **({} if policy is None else {'software_exclusions': policy}))


def prepare(args):
    from scripts.run_pre_scale_search_v1 import require_environment
    require_environment(); source = pinned_revision(ROOT); out = args.output.resolve()
    origin = {k: str(getattr(args, 'origin_' + k).resolve()) for k in ('run', 'source', 'analysis', 'readouts')}
    if (out.exists() or any(out.is_relative_to(Path(origin[k])) for k in origin)
            or not args.seed_usage_root or any(not p.is_dir() for p in args.seed_usage_root)):
        raise ValueError('fresh output, explicit original closure/readouts and existing seed roots required')
    origin['source_commit'] = read(Path(origin['run']) / 'plan.json')['source_commit']
    origin['input_files'] = {str(p): file_sha256(p) for p in evidence_files(origin)}
    policy = None if args.seed_software_exclusions is None else software_fixture_policy(read(args.seed_software_exclusions))
    with (Path(origin['run']) / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB); original, audit, bank = origin_evidence(origin)
        out.mkdir(parents=True); save(out / 'preparation-started.json', {'source_commit': source,
            'started_utc': utc(), 'origin': origin, 'new_model_calls': 0})
        try:
            usages = [strict_inventory(p, clone(SEEDS), policy) for p in args.seed_usage_root]
            for i, u in enumerate(usages): save(out / ('seed-usage-' + str(i).zfill(2) + '.json'),
                {k: v for k, v in u.items() if k != 'content_sha256'})
            plan = build_plan(original, audit, bank, source=source, origin=origin, usages=usages,
                observer_backend=backend_binding({k: original['scientist'][k] for k in ('model', 'model_digest')}),
                source_proof=native_sources(original['source_commit']), software_exclusions=policy)
            save(out / 'plan.json', plan); require_plan(out)
        except BaseException as error:
            save(out / 'preparation-ended.json', {'status': 'stopped', 'error_type': type(error).__name__,
                'error': str(error), 'new_model_calls': 0}); raise
        save(out / 'preparation-ended.json', {'status': 'prepared', 'new_model_calls': 0})


def observe(root, p, job, observer):
    directory = root / 'evaluation' / job['identity']
    if (directory / 'started.json').exists(): raise ValueError('consumed evaluation job; no redispatch')
    suggestion = Suggestion(job['identity'], job['system'], 0, 'selection-fixed-evaluation')
    save(directory / 'started.json', {**clone(job), 'suggestion': suggestion.to_dict(), 'started_utc': utc()})
    measure = measure_with(observer, p['observer_contract'])
    def measured(sim, base):
        result = resource_measure(sim, measure(sim, base))
        return {**result, 'native_workflow_interval': interval(p, sim.native_system.spec, sim.native_system.events, job['seed'])}
    outcome = evaluate_native_suggestion(suggestion, seeds=[job['seed']],
        simulation_factory=scientist_factory(directory / 'worlds', p, root), loss_spec=p['losses']['throughput'],
        measurement_adapter=measured).to_dict()
    save(directory / 'observation.json', outcome)
    save(directory / 'cross-scores.json', {k: evaluate_loss(v, outcome['metadata']['measurements']) for k, v in p['losses'].items()})


def additional_from_checkpoints(measurement, directory):
    from scripts.run_native_legacy_topic_pilot_v1 import additional_from_checkpoints as rebuild
    return rebuild(measurement, directory)


def run(root):
    p = require_plan(root)
    return run_shared(root, require_plan_fn=require_plan, observe_fn=observe, schema=SCHEMA,
        inventory_fn=lambda directory, seeds: strict_inventory(directory, seeds, p.get('seed_software_exclusions')))


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('stage', choices=('prepare', 'run'))
    parser.add_argument('--output', type=Path, required=True)
    for key in ('run', 'source', 'analysis', 'readouts'): parser.add_argument('--origin-' + key, type=Path)
    parser.add_argument('--seed-usage-root', type=Path, action='append')
    parser.add_argument('--seed-software-exclusions', type=Path); args = parser.parse_args()
    if args.stage == 'prepare':
        if any(getattr(args, 'origin_' + k) is None for k in ('run', 'source', 'analysis', 'readouts')):
            parser.error('all exact normally closed original paths required')
        prepare(args)
    else: run(args.output.resolve())


if __name__ == '__main__': main()
