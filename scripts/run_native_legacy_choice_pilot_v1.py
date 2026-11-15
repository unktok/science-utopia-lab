"""Finite original-choice control pilot, not optimization or unused evaluation.

Reuse the original world, common-content observer, role/transport factory and
losses. No designer generation, host topic coercion, refill or source repair.
"""
import argparse
from contextlib import ExitStack
import fcntl
import json
import os
from pathlib import Path

from scripts import run_native_longitudinal_fixed_evaluation_v1 as previous
from scripts import run_native_workflow_objective_loop_v1 as workflow
from scripts.analyze_native_open_v7 import _inventory
from scripts.run_native_objective_instrument_loop_v1 import measure_with, progress
from scripts.run_pre_scale_search_v1 import require_environment, ENVIRONMENT
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend, make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_designer_preflight import runtime_binding, backend_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_scientist_transport_v1 import contract, validate, PROTOCOL as TRANSPORT_PROTOCOL
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.optimization.native_workflow_domain_v4 import require_workflow_candidate, verify_workflow_interval
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.system.native_legacy_choice_controls import controls
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-legacy-choice-pilot.v1'
PROTOCOL = 'research/protocols/campaigns/native-legacy-choice-feasibility-v1.md'
FIXED_RECEIPT = 'research/results/native-longitudinal-fixed-closed-v1.json'
ROLE = 'developer-legacy-choice-control'
SEED = 61001
LABELS = ('core-assignment', 'native-choice', 'native-choice-advice')
read, save, utc = workflow.read, workflow.save, workflow.utc
scientist_factory = workflow.scientist_factory


def preceding_evidence(origin):
    original, audit = previous.origin_evidence(origin)
    fixed = read(ROOT / FIXED_RECEIPT)
    raw = Path(fixed['scientific_run'])
    if (fixed['terminal']['status'] != 'closed' or fixed['physical_worlds'] != 5
            or fixed['terminal']['completed_jobs'] != 5
            or fixed['origin_selection_content_sha256'] != audit['selection']['content_sha256']
            or fixed['scientific_source_commit'] != original['source_commit']
            or read(raw / 'terminal.json') != fixed['terminal']
            or digest(_inventory(raw)) != fixed['raw_inventory_sha256']
            or len(_inventory(raw)) != fixed['raw_files']
            or not fixed['two_original_audits_identical'] or not fixed['two_original_costs_identical']):
        raise ValueError('unchanged closed preceding development and frozen evaluation required')
    return original, audit, fixed


def build_plan(original, audit, fixed, *, source, origin, observer_backend, original_sources):
    if (original['schema'] != previous.development.SCHEMA + '.plan'
            or original['objectives'] != ['throughput', 'content-utility']
            or original['world']['years'] != 4 or audit['closure']['terminal']['status'] != 'closed'
            or audit['closure']['terminal']['consumed_slots'] != 12
            or original['initial_system']['initial_state']['seed'] != SEED
            or original_sources['original_source'] != original['source_commit']
            or validate(original['scientist_transport']) != contract(read_seconds=900)
            or original['operational_protocol'] != {
                'path': TRANSPORT_PROTOCOL, 'sha256': file_sha256(ROOT / TRANSPORT_PROTOCOL)}):
        raise ValueError('literal four-year original world, T/U and scientist900 binding required')
    observer = make_contract(source_commit=source,
        provider={k: original['scientist'][k] for k in ('model', 'model_digest')},
        backend=observer_backend, maximum_posts=3000, critics=3)
    ignore = {'source_commit', 'content_sha256', 'maximum_posts'}
    if ({k: v for k, v in observer.items() if k not in ignore}
            != {k: v for k, v in original['observer_contract'].items() if k not in ignore}):
        raise ValueError('same original common-content observer required')
    anchor = SystemSpec.from_dict(original['reference_systems']['post-funding-cost'])
    systems = controls(anchor)
    for system in systems.values():
        require_workflow_candidate(SystemSpec.from_dict(original['initial_system']), system)
    experiment = {'protocol': PROTOCOL, 'role': ROLE}
    return {'schema': SCHEMA + '.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT / PROTOCOL),
        'launch_environment': clone(ENVIRONMENT), 'origin': clone(origin),
        'origin_audit_content_sha256': audit['content_sha256'],
        'preceding_fixed_receipt': {'path': FIXED_RECEIPT, 'file_sha256': file_sha256(ROOT / FIXED_RECEIPT),
            'content_sha256': fixed['content_sha256'], 'run': fixed['scientific_run']},
        'original_native_sources': clone(original_sources),
        **{k: clone(original[k]) for k in ('scientist', 'designer', 'data_cache', 'losses',
            'objectives', 'catalog', 'initial_system', 'scientist_transport', 'operational_protocol')},
        'experiment': experiment, 'observer_contract': observer,
        'world': {**clone(original['world']), 'source_commit': source, 'experiment': experiment,
            'measurement_adapter_contract': observer, 'classification': 'actual-native-legacy-choice-pilot-v1'},
        'jobs': [{'identity': 'legacy-choice-' + label, 'condition': label, 'seed': SEED,
                  'system': systems[label].to_dict()} for label in LABELS],
        'budget': {'native_worlds_upper_bound': 3, 'scientist_HTTP_attempts_per_world': 1024,
            'world_wall_seconds': 7200, 'observer_POSTs_upper_bound': 3000,
            'designer_generation_POSTs': 0, 'replace_failed_slots': False,
            'stop_after_technical_failure': True},
        'development_seed_reused': True, 'held_out_evaluation': False,
        'policy_selection': False, 'automatic_invention': False, 'publication_ready': False}


def require_plan(root):
    p = read(root / 'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean pilot source/runtime required')
    original, audit, fixed = preceding_evidence(p['origin'])
    expected = build_plan(original, audit, fixed, source=p['source_commit'], origin=p['origin'],
        observer_backend=p['observer_contract']['backend'],
        original_sources=workflow.native_sources(original['source_commit']))
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal control/world/loss/transport/budget reconstruction differs')
    return p


def interval(plan, system, events, seed):
    if seed != SEED:
        raise ValueError('explicit reused development condition required')
    return verify_workflow_interval(SystemSpec.from_dict(plan['initial_system']), system, events, years=4)


def observe(root, p, job, observer, *, role=None, interval_reader=None, metric_adapter=None):
    directory = root / 'controls' / job['identity']
    if (directory / 'started.json').exists():
        raise ValueError('consumed control; no redispatch')
    suggestion = Suggestion(job['identity'], job['system'], 0, ROLE if role is None else role)
    save(directory / 'started.json', {'job': clone(job), 'suggestion': suggestion.to_dict(), 'started_utc': utc()})
    measure = measure_with(observer, p['observer_contract'])
    def measured(sim, base):
        value = measure(sim, base)
        if metric_adapter is not None:
            value = metric_adapter(sim, value)
        check_interval = interval if interval_reader is None else interval_reader
        return {**value, 'native_workflow_interval': check_interval(
            p, sim.native_system.spec, sim.native_system.events, job['seed'])}
    observation = evaluate_native_suggestion(suggestion, seeds=[job['seed']],
        simulation_factory=scientist_factory(directory / 'worlds', p, root),
        loss_spec=p['losses']['throughput'], measurement_adapter=measured).to_dict()
    save(directory / 'observation.json', observation)
    scores = {k: evaluate_loss(v, observation['metadata']['measurements']) for k, v in p['losses'].items()}
    save(directory / 'cross-scores.json', scores)
    if observation['status'] != 'complete' or any(v['status'] != 'complete' for v in scores.values()):
        raise ValueError('technical-null control retained; no refill or further inference')


def run(root, *, plan_reader=None, observe_function=None, schema=None):
    plan_reader = require_plan if plan_reader is None else plan_reader
    observe_function = observe if observe_function is None else observe_function
    schema = SCHEMA if schema is None else schema
    require_environment(); p = plan_reader(root)
    with ExitStack() as stack:
        paths = {root / 'writer.lock', Path(p['origin']['run']) / 'writer.lock',
                 Path(p['preceding_fixed_receipt']['run']) / 'writer.lock'}
        for path in sorted(paths):
            handle = stack.enter_context(path.open('a' if path == root / 'writer.lock' else 'r'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / 'started.json').exists():
            raise ValueError('consumed pilot; no redispatch')
        plan_reader(root)
        save(root / 'started.json', {'schema': schema + '.start', 'pid': os.getpid(),
            'plan_sha256': p['content_sha256'], 'started_utc': utc()})
        status, completed, failure = 'stopped', 0, {}
        try:
            observer = CommonContentObserver(root / 'observer', p['observer_contract'],
                backend=LocalObserverBackend(inference_lock=root / 'inference.lock'))
            for job in p['jobs']:
                progress(root, 'controls', job['identity'])
                observe_function(root, p, job, observer); completed += 1; plan_reader(root)
            workflow.retain_observer_audit(root, observer)
            status = 'closed'; progress(root, 'closed')
        except BaseException as error:
            failure = {'error_type': type(error).__name__, 'error': str(error)}
            raise
        finally:
            save(root / 'terminal.json', {'schema': schema + '.terminal', 'status': status,
                'completed_jobs': completed, 'ended_utc': utc(), 'held_out_world_seeds': False,
                'policy_selection': False, 'automatic_invention': False, 'publication_ready': False, **failure})


def prepare(args, *, plan_builder=None, plan_reader=None, source_reader=None):
    plan_builder = build_plan if plan_builder is None else plan_builder
    plan_reader = require_plan if plan_reader is None else plan_reader
    source_reader = workflow.native_sources if source_reader is None else source_reader
    require_environment(); source = pinned_revision(ROOT)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
        'source_commit': read(args.audit_one)['source_commit'], 'audit_files': {
            str(path.resolve()): file_sha256(path) for path in (args.audit_one, args.audit_two)}}
    fixed = read(ROOT / FIXED_RECEIPT)
    output = args.output.resolve()
    if (output.exists() or output.is_relative_to(args.origin_run.resolve())
            or output.is_relative_to(Path(fixed['scientific_run']))):
        raise ValueError('fresh separate pilot directory required')
    with ExitStack() as stack:
        for path in sorted({args.origin_run / 'writer.lock', Path(fixed['scientific_run']) / 'writer.lock'}):
            handle = stack.enter_context(path.open('r')); fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original, audit, fixed = preceding_evidence(origin)
        if not Path(original['data_cache']).is_dir():
            raise ValueError('existing offline corpus required')
        p = plan_builder(original, audit, fixed, source=source, origin=origin,
            observer_backend=backend_binding(original['scientist']),
            original_sources=source_reader(original['source_commit']))
        output.mkdir(parents=True); save(output / 'plan.json', p); plan_reader(output)
    print(json.dumps({'prepared_source': source, 'worlds_upper_bound': len(p['jobs']), 'designer_generation_POSTs': 0}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'run')); parser.add_argument('--output', type=Path, required=True)
    for name in ('origin-run', 'origin-source', 'audit-one', 'audit-two'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args(); args.output = args.output.resolve()
    if args.stage == 'prepare':
        if any(getattr(args, name) is None for name in ('origin_run', 'origin_source', 'audit_one', 'audit_two')):
            parser.error('closed original source/run and two matching audits required')
        prepare(args)
    else:
        run(args.output)


if __name__ == '__main__':
    main()
