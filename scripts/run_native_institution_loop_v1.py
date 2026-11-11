"""Prospective native T/E optimization with explicit routing authority.

Finite pilot toward the publication goal, not a publication-readiness verdict.
Reuse native ask/tell, exact editor transport, per-proposal fresh readiness and
original scientist worlds. No historical losses become fresh measurements.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path

from scripts.run_pre_scale_search_v1 import (require_environment, ENVIRONMENT,
    campaign, observe, selection_payload, evaluation_jobs)
from scripts.run_pre_scale_pilot_v1 import numeric_calibration
from scripts.native_benchmark_seed_usage import usage_inventory
from utopia.optimization.native_benchmark_controls import objective_specs, selection_control, without_review
from utopia.optimization.native_bounded_staged_designer import BoundedStagedDesigner, execute
from utopia.optimization.native_causal_design import OPTION, PRESENTATION
from utopia.optimization.native_designer_preflight import runtime_binding, backend_binding, planned_cases
from utopia.optimization.native_designer_roles_v38 import validate_designer_binding
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_fixed_production_domain import allow_review_routing
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory
from utopia.optimization.native_numeric_designer import NumericDesigner, checked, save
from utopia.optimization.native_review_routing_controls import routed_control
from utopia.optimization.native_scientist_load_v38 import load_local_role
from utopia.system import SystemSpec
from utopia.system.design_patch import clone
from utopia.system.native_information_institution import information_system, information_design_space
from utopia.system.native_kernel import legacy_world_system
from utopia.utils.data_utils import file_sha256, write_json_atomic

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-institution-loop.v1'
PROTOCOL = 'research/protocols/campaigns/native-institution-loop-v1.md'
SEED = 61001
EVALUATION_SEEDS = (62001, 62011, 62017)
OBJECTIVES = ('throughput', 'efficiency')
METHODS = ('parameters', 'code-fixed-graph', 'code-and-graph')


def read(path):
    return checked(json.loads(Path(path).read_text()))


def build_plan(*, source, operator, backend, seed_usage):
    validate_designer_binding(operator['designer'], scientist_binding=operator['scientist'])
    if len(source) != 40 or any(c not in '0123456789abcdef' for c in source):
        raise ValueError('full clean source required')
    if not seed_usage or any(not u['valid'] or u['errors'] or u['prior_matching_runs'] for u in seed_usage):
        raise ValueError('development/evaluation seed usage must be explicitly checked and empty')
    image = operator['scientist']['image_id']; anchor = information_system(image, seed=SEED)
    routed = {n: routed_control(anchor, reviewers_per_paper=n, snapshot_phase=85, producer_phase=87)
              for n in (1, 2)}
    references = {'open-seed': anchor.to_dict(), 'legacy': legacy_world_system(seed=SEED).to_dict(),
        'reviewed-accept-all': selection_control(anchor, rule='accept-all').to_dict(),
        'no-review-accept-all': without_review(selection_control(anchor, rule='accept-all')).to_dict(),
        'no-review-reject-all': without_review(selection_control(anchor, rule='reject-all')).to_dict(),
        'routed-one-accept-all': selection_control(routed[1], rule='accept-all').to_dict(),
        'routed-two-accept-all': selection_control(routed[2], rule='accept-all').to_dict(),
        'routed-one-reject-all': selection_control(routed[1], rule='reject-all').to_dict()}
    experiment = {'protocol': PROTOCOL, 'role': 'purpose-conditioned-native-routing-pilot'}
    world = {**clone(operator['scientist']), 'source_commit': source, 'years': 4,
        'experiment': experiment, 'classification': 'actual-native-institution-loop-v1',
        'runtime_seed_binding': {'python_hash_seed_environment': os.environ.get('PYTHONHASHSEED'),
            'python_hash_probe': hash('scienceutopia.native-world.v1')}}
    losses = objective_specs(); assignments = {}; bindings = {}
    for method in METHODS:
        for objective in OBJECTIVES:
            arm = objective+':'+method
            assignments[arm] = {'method': method, 'objective': objective, 'strategy': 'local-designer', 'domain': method}
            domain = allow_review_routing(anchor, information_design_space(anchor, method, fixed_production=True))
            bindings[arm] = {'initial_system': anchor.to_dict(), 'loss_spec': losses[objective],
                'seeds': [SEED], 'world': world, 'strategies': {'local-designer': {
                    'kind': method, 'protocol': PROTOCOL, OPTION: True, PRESENTATION: 'inline'}},
                'seed': 63001, 'design_space': domain}
    order = list(bindings)
    schedule = [{'arm': arm, 'generation': g} for g in range(2) for arm in order[g:]+order[:g]]
    return {'schema': SCHEMA+'.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT/PROTOCOL),
        'scientist': clone(operator['scientist']), 'designer': clone(operator['designer']),
        'backend': clone(backend), 'data_cache': operator['data_cache'], 'world': world,
        'experiment': experiment, 'launch_environment': clone(ENVIRONMENT),
        'losses': losses, 'objectives': list(OBJECTIVES), 'methods': list(METHODS),
        'assignments': assignments, 'campaign_bindings': {'run-00': bindings},
        'arm_order': order, 'schedule': schedule, 'generations': 2,
        'reference_systems': references, 'reference_order': list(references),
        'evaluation': {'seeds': list(EVALUATION_SEEDS), 'years': 4, 'maximum_physical_worlds': 33,
            'reference_labels': ['legacy', 'reviewed-accept-all', 'no-review-accept-all',
                                 'routed-one-accept-all', 'routed-two-accept-all'],
            'seed_usage': [u['content_sha256'] for u in seed_usage]},
        'budget': {'reference_worlds': 8, 'candidate_slots': 12, 'candidate_worlds_upper_bound': 12,
            'evaluation_worlds_upper_bound': 33, 'native_worlds_upper_bound': 53,
            'initial_editor_readiness_sessions': 1, 'per_code_proposal_editor_readiness_sessions': 8,
            'editor_readiness_posts_upper_bound': 360, 'editor_proposal_posts_upper_bound': 128,
            'initial_numeric_readiness_sessions': 1, 'per_numeric_proposal_readiness_sessions': 4,
            'numeric_readiness_posts_upper_bound': 20, 'numeric_proposal_posts_upper_bound': 8,
            'seconds_per_designer_session': 1200, 'scientist_http_attempts_per_world': 1024,
            'designer_http_timeout_seconds': [10, 900], 'replace_failed_slots': False},
        'claims': {'scientific_truth': False, 'whole_world_autograd': False,
            'graph_syntax_necessary': False, 'pure_design_space_effect_identified': False,
            'method_superiority': False, 'new_conference_ready_result': False}}


def prepare(args):
    require_environment()
    if args.output.exists():
        raise ValueError('fresh experiment output required')
    source = pinned_revision(ROOT); operator = read(args.operator_binding_plan)
    if not Path(operator['data_cache']).is_dir():
        raise ValueError('existing offline corpus cache required')
    usages = [usage_inventory(p, [SEED, *EVALUATION_SEEDS]) for p in args.seed_usage_root]
    plan = build_plan(source=source, operator=operator, backend=backend_binding(operator['designer']), seed_usage=usages)
    args.output.mkdir(parents=True)
    for i, receipt in enumerate(usages):
        save(args.output/f'seed-usage-{i}.json', {k:v for k,v in receipt.items() if k != 'content_sha256'})
    save(args.output/'plan.json', plan)
    print(json.dumps({'prepared_source': source, 'native_worlds_upper_bound': 53, 'generation_calls': 0}), flush=True)


def require_plan(root):
    plan = read(root/'plan.json')
    if (plan['source_commit'] != pinned_revision(ROOT) or plan['runtime'] != runtime_binding()
            or plan['protocol_sha256'] != file_sha256(ROOT/PROTOCOL)):
        raise ValueError('native loop source/runtime/protocol changed')
    return plan


def readiness(root, plan, *, request, numeric, target):
    target.mkdir(parents=True, exist_ok=True)
    if numeric:
        parameters = {**clone(plan), 'numeric_calibration_cases': list(OBJECTIVES),
            'systems': {'M1': plan['reference_systems']['open-seed']},
            'numeric_settings': {'max_calls': 2, 'wall_seconds': 1200, 'num_ctx': 40960,
                'num_predict': 8192, 'temperature': .6, 'think': False, 'http_timeout_seconds': [10,900]}}
        def request_for(objective):
            # Both explicit objective cases at this exact source/domain.
            c = campaign(root, plan, 'run-00', objective+':parameters')
            return c._request(c.state['records'], c._validate(), 1)
        # The reused calibrator has its own inner per-session lock. Also hold
        # this campaign's shared lock across loading AND every calibration call
        # so it cannot overlap a scientist/editor using the outer lock.
        with (root/'inference.lock').open('a') as inference:
            fcntl.flock(inference, fcntl.LOCK_EX | fcntl.LOCK_NB)
            numeric_calibration(target, parameters, request_factory=request_for)
        cert = target/'numeric-readiness/certificate.json'
        if not read(cert)['passed']:
            raise ValueError('fresh numeric readiness failed; stop without replacement')
    else:
        count = len(planned_cases(request, 'staged-v15', BOUNDED_AUTHORING))
        if count > 40:
            raise ValueError('editor readiness exceeds40 POSTs')
        result = execute(target/'editor-readiness', kind='calibration', request=request,
            provider=plan['designer'], source_commit=plan['source_commit'], maximum_posts=count,
            inference_lock=root/'inference.lock')
        cert = target/'editor-readiness/calibration/certificate.json'
        if not result['passed']:
            raise ValueError('fresh editor readiness failed; stop without replacement')
        saved = read(cert)
        if saved['plan']['backend'] != plan['backend'] or saved['plan']['request'] != request:
            raise ValueError('editor readiness backend/request differs')
    return cert


def progress(root, plan, stage, active=None):
    rows = []
    for arm in plan['arm_order']:
        c = campaign(root, plan, 'run-00', arm)
        for g, r in enumerate(c.state['records']):
            observation = r['observations'][0] if r['observations'] else None
            rows.append({'arm': arm, 'generation': g,
                'status': 'generation-failure' if r['generation_error'] else observation['status'] if observation else 'unknown',
                'loss': observation['loss'] if observation else None})
    value = {'schema': SCHEMA+'.progress', 'stage': stage, 'active': active,
        'observed_utc': datetime.now(timezone.utc).isoformat(), 'writer_pid': os.getpid(),
        'reference_observations': len(list((root/'references').glob('*/observation.json'))),
        'candidate_slots': rows, 'evaluation_observations': len(list((root/'evaluation').glob('*/observation.json')))}
    write_json_atomic(root/'progress.json', value, sort_keys=True, allow_nan=False)
    print(json.dumps({k:v for k,v in value.items() if k != 'candidate_slots'}), flush=True)


def run(root):
    require_environment(); plan = require_plan(root); plan['_output'] = str(root)
    with (root/'writer.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save(root/'started.json', {'schema': SCHEMA+'.start', 'pid': os.getpid(),
            'plan_sha256': plan['content_sha256'], 'started_utc': datetime.now(timezone.utc).isoformat()})
        terminal = {'schema': SCHEMA+'.terminal', 'status': 'closed'}
        try:
            c = campaign(root, plan, 'run-00', 'throughput:code-and-graph')
            request = c._request([], c._strategy_initial(), 1)
            progress(root, plan, 'initial-readiness')
            readiness(root, plan, request=request, numeric=False, target=root/'initial-readiness')
            readiness(root, plan, request=request, numeric=True, target=root/'initial-readiness')
            for name in plan['reference_order']:
                progress(root, plan, 'references', name)
                observation = observe(root/'references'/name, plan, 'reference-'+name,
                    plan['reference_systems'][name], SEED, 'developer-reference')
                if observation['status'] != 'complete':
                    raise ValueError('reference failed; preserve and stop this source')
            for slot in plan['schedule']:
                arm = slot['arm']; g = slot['generation']; c = campaign(root, plan, 'run-00', arm)
                if c.state['pending'] is not None or len(c.state['records']) != g:
                    raise ValueError('pending attempt or wrong generation; no redispatch')
                request = c._request(c.state['records'], c._validate(), 1)
                directory = root/'search'/'run-00'/arm.replace(':','--')
                numeric = plan['assignments'][arm]['method'] == 'parameters'
                progress(root, plan, 'proposal-readiness', arm+':g'+str(g))
                cert = readiness(root, plan, request=request, numeric=numeric,
                    target=directory/f'readiness-{g}')
                if numeric:
                    load_local_role(directory/f'designer-load-{g}.json', provider=plan['designer'],
                        role='designer', purpose='native-loop-numeric-proposal')
                    author = NumericDesigner(directory/'authoring', provider=plan['designer'],
                        backend=plan['backend'], certificate=cert, inference_lock=root/'inference.lock')
                else:
                    author = BoundedStagedDesigner(directory/'authoring', provider=plan['designer'],
                        source_commit=plan['source_commit'], certificate=cert, inference_lock=root/'inference.lock')
                factory = LocalRoleBoundNativeFactory(directory/'worlds', Path(plan['data_cache']),
                    years=4, corpus_years=4, designer_provider=plan['designer'], record_wire=True, record_code=True,
                    maximum_http_attempts=1024, experiment_binding=plan['experiment'], inference_lock=root/'inference.lock')
                progress(root, plan, 'optimization', arm+':g'+str(g))
                c.advance(simulation_factory=factory, generators={'local-designer': author}, count=1)
            selection = selection_payload(root, plan, frozen_utc=datetime.now(timezone.utc).isoformat())
            selection['schema'] = SCHEMA+'.selection'
            # Rehash rather than retaining the old runner's schema digest.
            selection = save(root/'selection.json', {k:v for k,v in selection.items() if k != 'content_sha256'})
            jobs = evaluation_jobs(plan, selection)
            save(root/'evaluation-plan.json', {'schema': SCHEMA+'.evaluation-plan',
                'selection_sha256': selection['content_sha256'], 'jobs': jobs})
            for job in jobs:
                progress(root, plan, 'selection-fixed-evaluation', job['identity'])
                observe(root/'evaluation'/job['identity'], plan, job['identity'], job['system'], job['seed'],
                        'selection-fixed-evaluation')
            progress(root, plan, 'closed')
        except BaseException as error:
            terminal.update(status='stopped', error_type=type(error).__name__, error=str(error))
            try:
                progress(root, plan, 'stopped', terminal['error_type'])
            except Exception as progress_error:
                terminal['progress_error'] = type(progress_error).__name__+': '+str(progress_error)
            raise
        finally:
            terminal['ended_utc'] = datetime.now(timezone.utc).isoformat()
            save(root/'terminal.json', terminal)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('prepare','run')); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--operator-binding-plan', type=Path); p.add_argument('--seed-usage-root', type=Path, action='append', default=[])
    a = p.parse_args(); a.output = a.output.resolve()
    if a.stage == 'prepare':
        if not a.operator_binding_plan or not a.seed_usage_root:
            p.error('prepare requires operator binding and explicit seed-usage roots')
        prepare(a)
    else:
        run(a.output)


if __name__ == '__main__':
    main()
