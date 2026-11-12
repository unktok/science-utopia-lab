"""Finite developer agenda controls in the original capacity world; no design."""
import argparse
import fcntl
import json
import os
from pathlib import Path

from scripts.run_native_capacity_fixed_evaluation_v1 import origin_evidence, read, INSTRUMENT
from scripts.run_native_capacity_objective_loop_v1 import measured, SEED, OBJECTIVES
from scripts.run_native_objective_instrument_loop_v1 import factory_for, progress, utc
from scripts.run_pre_scale_search_v1 import require_environment, ENVIRONMENT
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_benchmark_controls import selection_control
from utopia.optimization.native_design_space import require_candidate_in_space
from utopia.optimization.native_designer_preflight import runtime_binding
from utopia.optimization.native_fixed_production_domain import allow_catalog_planning, allow_review_routing
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import save
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone
from utopia.system.native_capacity_controls import capacity_allocation_control
from utopia.system.native_catalog_planning import catalog_agenda_control, catalog_contract
from utopia.system.native_information_institution import information_system, information_design_space
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-catalog-actuation.v1'
PROTOCOL = 'research/protocols/campaigns/native-catalog-actuation-v1.md'
MODES = ('cut', 'information', 'project')
ROLE = 'developer-catalog-actuation-control'


def build_plan(original, audit, *, source, origin):
    if (original['schema'] != 'scienceutopia.native-capacity-objective-loop.v1.plan'
            or original['objectives'] != list(OBJECTIVES)
            or len(source) != 40 or any(c not in '0123456789abcdef' for c in source)
            or original['world']['world_conditions'] != {
                'schema': 'scienceutopia.native-world-conditions.v2', 'initial_funding': 30,
                'population_resource_profile': 'balanced_two_band', 'log_resource_ledger': True,
                'papers_per_project': 2, 'funding_budget_mode': 'fixed', 'funding_budget_slots_frac': .2}):
        raise ValueError('exact closed capacity T/P world and full source required')
    contract = clone(original['measurement_contract'])
    if (contract['source_commit'] != original['source_commit']
            or contract['instrument_sha256'] != file_sha256(ROOT / INSTRUMENT)
            or contract['new_model_calls'] or contract['adoption_constraint']):
        raise ValueError('unchanged P instrument without adoption constraint required')
    contract['source_commit'] = source
    image = original['scientist']['image_id']
    anchor = capacity_allocation_control(selection_control(information_system(image, seed=SEED),
        rule='accept-all'), image, rule='reserve-proximity')
    if anchor.to_dict() != original['reference_systems']['reviewed-all-reserve-proximity']:
        raise ValueError('literal common reserve-proximity anchor required')
    domain = allow_catalog_planning(anchor, allow_review_routing(anchor,
        information_design_space(anchor, 'code-and-graph', fixed_production=True)))
    jobs = []
    for mode in MODES:
        spec = catalog_agenda_control(anchor, image, actuation=mode)
        require_candidate_in_space(anchor, spec, domain)
        jobs.append({'identity': 'catalog-' + mode, 'condition': mode, 'seed': SEED, 'system': spec.to_dict()})
    experiment = {'protocol': PROTOCOL, 'role': ROLE}
    return {'schema': SCHEMA + '.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT / PROTOCOL),
        'origin': clone(origin), 'origin_audit_content_sha256': audit['content_sha256'],
        'launch_environment': clone(ENVIRONMENT),
        **{k: clone(original[k]) for k in ('scientist', 'designer', 'data_cache', 'losses', 'objectives')},
        'world': {**clone(original['world']), 'source_commit': source, 'experiment': experiment,
            'classification': 'actual-native-catalog-actuation-v1', 'measurement_adapter_contract': contract},
        'experiment': experiment, 'measurement_contract': contract,
        'catalog': catalog_contract(), 'anchor': anchor.to_dict(), 'design_space': domain, 'jobs': jobs,
        'budget': {'native_worlds_upper_bound': 3, 'scientist_HTTP_attempts_per_world': 1024,
            'world_wall_seconds': 7200, 'designer_generation_POSTs': 0, 'critic_POSTs': 0,
            'replace_failed_slots': False},
        'development_seed_reused': True, 'held_out_evaluation': False, 'policy_selection': False,
        'automatic_invention': False, 'publication_ready': False}


def require_plan(root):
    p = read(root / 'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean catalog-actuation source/runtime required')
    original, audit = origin_evidence(p['origin'])
    expected = build_plan(original, audit, source=p['source_commit'], origin=p['origin'])
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal catalog/agenda/authority/budget reconstruction differs')
    return p


def prepare(args):
    require_environment(); source = pinned_revision(ROOT)
    if args.output.exists() or args.output.is_relative_to(args.origin_run.resolve()):
        raise ValueError('fresh separate controls directory required')
    audit = read(args.audit_one)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
        'source_commit': audit['source_commit'],
        'audit_files': {str(path.resolve()): file_sha256(path) for path in (args.audit_one, args.audit_two)}}
    with (args.origin_run / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original, audit = origin_evidence(origin)
        if not Path(original['data_cache']).is_dir(): raise ValueError('existing offline corpus required')
        p = build_plan(original, audit, source=source, origin=origin)
        args.output.mkdir(parents=True); save(args.output / 'plan.json', p); require_plan(args.output)
    print(json.dumps({'prepared_source': source, 'worlds_upper_bound': 3, 'designer_POSTs': 0}), flush=True)


def observe(root, p, job):
    directory = root / 'controls' / job['identity']
    if (directory / 'started.json').exists(): raise ValueError('consumed control; no redispatch')
    suggestion = Suggestion(job['identity'], job['system'], 0, ROLE)
    save(directory / 'started.json', {'job': clone(job), 'suggestion': suggestion.to_dict(), 'started_utc': utc()})
    observation = evaluate_native_suggestion(suggestion, seeds=[job['seed']],
        simulation_factory=factory_for(directory / 'worlds', p, root), loss_spec=p['losses']['throughput'],
        measurement_adapter=measured(p)).to_dict()
    save(directory / 'observation.json', observation)
    save(directory / 'cross-scores.json',
        {k: evaluate_loss(v, observation['metadata']['measurements']) for k, v in p['losses'].items()})


def run(root):
    require_environment(); p = require_plan(root)
    with (root / 'writer.lock').open('a') as owner, (Path(p['origin']['run']) / 'writer.lock').open('r') as previous:
        for handle in (owner, previous): fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / 'started.json').exists(): raise ValueError('consumed study; no redispatch')
        save(root / 'started.json', {'schema': SCHEMA + '.start', 'pid': os.getpid(),
            'plan_sha256': p['content_sha256'], 'started_utc': utc()})
        status, complete, failure = 'stopped', 0, {}
        try:
            for job in p['jobs']:
                progress(root, 'controls', job['identity']); observe(root, p, job)
                complete += 1; require_plan(root)
            status = 'closed'; progress(root, 'closed')
        except BaseException as error:
            failure = {'error_type': type(error).__name__, 'error': str(error)}; raise
        finally:
            save(root / 'terminal.json', {'schema': SCHEMA + '.terminal', 'status': status,
                'completed_jobs': complete, 'ended_utc': utc(), 'held_out_world_seeds': False,
                'policy_selection': False, 'publication_ready': False, **failure})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'run'))
    parser.add_argument('--output', type=Path, required=True)
    for name in ('origin-run', 'origin-source', 'audit-one', 'audit-two'): parser.add_argument('--' + name, type=Path)
    args = parser.parse_args(); args.output = args.output.resolve()
    if args.stage == 'prepare':
        if any(getattr(args, k) is None for k in ('origin_run', 'origin_source', 'audit_one', 'audit_two')):
            parser.error('closed original capacity source and matching audits required')
        prepare(args)
    else: run(args.output)


if __name__ == '__main__': main()
