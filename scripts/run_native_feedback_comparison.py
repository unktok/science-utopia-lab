#!/usr/bin/env python3
"""Finite same-source feedback/no-feedback development comparison, no refill."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_native_warmstart_v45 import campaign_from_binding, _save_equal
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_authoring_recovery_v44 import MAX_STEPS
from utopia.optimization.native_designer_decoding_v24 import decoding_contracts
from utopia.optimization.native_designer_preflight import EXECUTION_SCOPE, require_certificate, run_calibration
from utopia.optimization.native_designer_roles_v38 import make_local_role_bound_generator, validate_designer_binding
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-feedback-comparison.v1'
PROTOCOL = 'research/protocols/campaigns/native-feedback-comparison-v1-a1.md'
CLASSIFICATION = 'actual-native-feedback-comparison-development-v1'
LOSSES = {'throughput': 'native-joint-v5-throughput',
    'efficiency': 'native-reviewed-production-efficiency-v13'}
# Fixed chronology. G0 has no outcome feedback; G1 is the first comparison of
# adaptive versus technical-only proposals. This is not statistical replication.
ARM_ORDER = ('throughput-loss', 'throughput-technical-only',
    'efficiency-technical-only', 'efficiency-loss')
GENERATIONS = 2


def build_plan(*, source_commit, provider_binding, designer_provider_binding,
               runtime_seed_binding, initial_system):
    validate_designer_binding(designer_provider_binding, scientist_binding=provider_binding)
    experiment = {'protocol': PROTOCOL, 'role': 'development-feasibility'}
    world = {**clone(provider_binding), 'source_commit': source_commit, 'years': 2,
        'population': 'five-independent-balanced-researchers',
        'experiment': experiment, 'classification': CLASSIFICATION,
        'runtime_seed_binding': clone(runtime_seed_binding)}
    losses = {name: json.loads((ROOT/'research/objectives/losses'/f'{identity}.json').read_text())
        for name, identity in LOSSES.items()}
    strategy = {'local-bounded-author': {'kind': 'literal-local-LLM-system-proposal',
        'model': designer_provider_binding['model'], 'conversation_profile': BOUNDED_AUTHORING,
        'source_commit': source_commit, 'protocol': PROTOCOL}}
    bindings, assignments = {}, {}
    for arm in ARM_ORDER:
        objective = arm.split('-', 1)[0]
        feedback = 'matched-loss' if arm.endswith('-loss') else 'technical-only'
        assignments[arm] = {'objective': objective, 'proposal_feedback': feedback}
        bindings[arm] = {'initial_system': clone(initial_system), 'loss_spec': clone(losses[objective]),
            'world': clone(world), 'seeds': [42], 'strategies': clone(strategy), 'mode': 'blackbox',
            'seed': 42, 'learning_rate': .1, 'strategy_learning_rate': .1,
            'strategy_baseline': 0., 'exploration': .1}
        bindings[arm]['proposal_feedback'] = feedback
    plan = {'schema': SCHEMA, 'classification': CLASSIFICATION, 'source_commit': source_commit,
        'provider_binding': clone(provider_binding), 'designer_provider_binding': clone(designer_provider_binding),
        'runtime_seed_binding': clone(runtime_seed_binding), 'initial_system': clone(initial_system),
        'experiment': experiment, 'world_binding': world, 'losses': losses,
        'arm_order': list(ARM_ORDER), 'assignments': assignments, 'campaign_bindings': bindings,
        'protocol': PROTOCOL, 'protocol_source_sha256': file_sha256(ROOT/PROTOCOL),
        'readiness_scope': EXECUTION_SCOPE, 'conversation_profile': BOUNDED_AUTHORING,
        'designer': {'max_steps': MAX_STEPS, 'max_tokens': 8192,
            'conversation_profile': BOUNDED_AUTHORING,
            'decoding': decoding_contracts('staged-v15', conversation_profile=BOUNDED_AUTHORING)},
        'budget': {'generations_per_arm': GENERATIONS, 'maximum_candidate_slots': 8,
            'maximum_baseline_worlds': 1, 'maximum_native_worlds': 9,
            'maximum_authoring_POSTs': 8*MAX_STEPS, 'maximum_calibration_POSTs': 40,
            'maximum_initial_designer_calibration_load_POSTs': 1,
            'maximum_designer_proposal_load_POSTs': 8, 'maximum_per_world_scientist_load_POSTs': 1,
            'replacement_policy': 'none', 'historical_cache_reuse': False},
        'comparison_scope': 'Adaptive loss-selected-parent/history feedback versus fixed-initial-parent technical-only proposals; not a scores-only ablation.',
        'claims': {'held_out': False, 'independent_replications': 1,
            'optimizer_superiority_established': False, 'scientific_value_established': False,
            'objective_specific_different_winners_required': False,
            'arm_label_is_selection_veto': False}}
    plan['content_sha256'] = digest(plan)
    return plan


def make_campaigns(root, plan):
    result = {arm: campaign_from_binding(Path(root)/'arms'/arm/'campaign', binding)
        for arm, binding in plan['campaign_bindings'].items()}
    if any(c.binding != plan['campaign_bindings'][arm] for arm, c in result.items()):
        raise ValueError('constructor differs from frozen comparison binding')
    return result


def progress(root, plan, campaigns):
    arms = {}
    for arm, c in campaigns.items():
        records = c.state['records']
        if len(records) > plan['budget']['generations_per_arm']:
            raise ValueError('finite comparison budget exceeded')
        rows = []
        for generation, r in enumerate(records):
            o = r['observations'][0] if r['observations'] else None
            status = 'generation-failure' if r['generation_error'] else (
                'complete' if o and o['status'] == 'complete' else 'technical-failure')
            rows.append({'generation': generation, 'status': status,
                'loss': o['loss'] if status == 'complete' else None})
        arms[arm] = {'slots': rows, 'pending': c.state['pending'] is not None}
    terminal = all(len(a['slots']) == GENERATIONS and not a['pending'] for a in arms.values())
    rows = [r for a in arms.values() for r in a['slots']]
    result = {'schema': SCHEMA+'.progress', 'source_commit': plan['source_commit'],
        'plan_sha256': plan['content_sha256'], 'arms': arms,
        'consumed_candidate_slots': len(rows), 'terminal': terminal,
        'status': ('complete' if all(r['status']=='complete' for r in rows)
            else 'budget-complete-with-failures') if terminal else 'in-progress'}
    result['content_sha256'] = digest(result)
    write_json_atomic(Path(root)/'progress.json', result, sort_keys=True, allow_nan=False)
    return result


def prepare(args):
    from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_open_examples import open_native_system
    source = pinned_revision(ROOT)
    config = json.loads(args.designer_provider_config.read_text())
    if set(config) != {'provider_binding'}:
        raise ValueError('exact operator designer binding required')
    designer = config['provider_binding']
    factory = LocalRoleBoundNativeFactory(args.output/'binding-only-no-worlds', args.data_cache,
        years=2, corpus_years=4, designer_provider=designer)
    executor = DockerCodeExecutor()
    scientist = {k: clone(getattr(factory, k)) for k in
        ('model', 'model_digest', 'corpus_sha256', 'corpus_years', 'dataset_identity')}
    scientist['image_id'] = executor.image_id
    plan = build_plan(source_commit=source, provider_binding=scientist, designer_provider_binding=designer,
        runtime_seed_binding=factory.runtime_seed_binding, initial_system=open_native_system(executor.image_id).to_dict())
    _save_equal(args.output/'plan.json', plan)
    _save_equal(args.output/'operator-config.json', config)
    return plan, make_campaigns(args.output, plan)


def execute(args):
    from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory, record_loaded_context
    from utopia.optimization.native_scientist_load_v38 import load_local_role
    plan, campaigns = prepare(args)
    if args.action == 'prepare':
        return 0
    designer = plan['designer_provider_binding']
    certificate = args.output/'preflight/certificate.json'
    if args.action == 'calibrate':
        from utopia.optimization.native_designer_preflight import planned_cases
        c = campaigns[ARM_ORDER[0]]
        request = c._request([], c._strategy_initial(), 1)
        if len(planned_cases(request, 'staged-v15', BOUNDED_AUTHORING)) > plan['budget']['maximum_calibration_POSTs']:
            raise ValueError('calibration would exceed its finite budget')
        load_local_role(args.output/'load-designer-calibration.json', provider=designer,
            purpose='before-feedback-comparison-calibration', role='designer')
        record_loaded_context(args.output/'loaded-designer-calibration.json', expected={'designer': designer},
            purpose='before-feedback-comparison-calibration')
        receipt = run_calibration(args.output/'preflight', request=request, provider=designer,
            source_commit=plan['source_commit'], scope=EXECUTION_SCOPE, conversation_profile=BOUNDED_AUTHORING)
        return 0 if receipt['all_controls_passed'] else 1
    require_certificate(certificate, designer, protocol='staged-v15', scope=EXECUTION_SCOPE,
        conversation_profile=BOUNDED_AUTHORING)

    def factory(root):
        return LocalRoleBoundNativeFactory(root, args.data_cache, years=2, corpus_years=4,
            designer_provider=designer, record_wire=True, record_code=True,
            experiment_binding=plan['experiment'], inference_lock=args.output/'inference.lock')

    # Baseline measured once, then its same forward vector is scored under both
    # losses. Neither objective nor arm is an input to this shared world.
    baseline = evaluate_native_suggestion(Suggestion('feedback-comparison-baseline',
        plan['initial_system'], 0, 'shared-fixed-baseline'), seeds=[42],
        simulation_factory=factory(args.output/'baseline/worlds'), loss_spec=plan['losses']['throughput'])
    campaigns[ARM_ORDER[0]]._check_observation(baseline.to_dict(), {
        'suggestion': Suggestion('feedback-comparison-baseline', plan['initial_system'], 0, 'shared-fixed-baseline').to_dict()})
    write_json_atomic(args.output/'baseline/observation.json', baseline.to_dict(), sort_keys=True, allow_nan=False)
    write_json_atomic(args.output/'baseline/cross-scores.json', {
        name: evaluate_loss(loss, baseline.metadata['measurements']) for name, loss in plan['losses'].items()},
        sort_keys=True, allow_nan=False)
    progress(args.output, plan, campaigns)
    for generation in range(GENERATIONS):
        for arm in plan['arm_order']:
            c = campaigns[arm]
            if len(c.state['records']) != generation or c.state['pending'] is not None:
                raise ValueError('comparison does not silently resume/refill already-dispatched slots')
            purpose = f'before-feedback-comparison:{arm}:g{generation}'
            directory = args.output/'arms'/arm
            load_local_role(directory/f'designer-load-{generation}.json', provider=designer,
                purpose=purpose, role='designer')
            record_loaded_context(directory/f'designer-context-{generation}.json',
                expected={'designer': designer}, purpose=purpose)
            author = make_local_role_bound_generator(args.output/'arms'/arm/'authoring',
                image_id=plan['provider_binding']['image_id'], provider_binding=designer,
                max_steps=MAX_STEPS, max_tokens=8192, inference_lock=args.output/'inference.lock',
                preflight_certificate=certificate, readiness_scope=EXECUTION_SCOPE,
                conversation_profile=BOUNDED_AUTHORING)
            c.advance(simulation_factory=factory(args.output/'arms'/arm/'worlds'),
                generators={'local-bounded-author': author}, count=1)
            result = progress(args.output, plan, campaigns)
            print(json.dumps({'arm': arm, 'generation': generation, **result['arms'][arm]}), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'calibrate', 'run'))
    parser.add_argument('--execute-authorized', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--designer-provider-config', type=Path, required=True)
    args = parser.parse_args(argv)
    args.output = args.output.resolve(); args.output.mkdir(parents=True, exist_ok=True)
    source = pinned_revision(ROOT)
    with (args.output/'comparison-writer.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX|fcntl.LOCK_NB)
        prefix = 'writer' if args.action == 'run' else args.action
        started, ended = args.output/f'{prefix}.started.json', args.output/f'{prefix}.ended.json'
        if started.exists():
            raise ValueError('action already dispatched; no hidden retry/resume or refreshed budget')
        record = {'schema': SCHEMA+'.writer', 'source_commit': source, 'action': args.action,
            'pid': os.getpid(), 'argv': sys.argv if argv is None else argv,
            'started_utc': datetime.now(timezone.utc).isoformat(), 'status': 'started',
            'environment': {k: os.environ.get(k) for k in
                ('CUDA_VISIBLE_DEVICES','PYTHONHASHSEED','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE')}}
        write_json_atomic(started, record, sort_keys=True, allow_nan=False)
        try:
            code = execute(args)
        except BaseException as error:
            record.update(status='aborted', error=type(error).__name__+': '+str(error))
            raise
        else:
            record.update(status='exited', exit_code=code)
            return code
        finally:
            record['ended_utc'] = datetime.now(timezone.utc).isoformat()
            write_json_atomic(ended, record, sort_keys=True, allow_nan=False)


if __name__ == '__main__':
    raise SystemExit(main())
