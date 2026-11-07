#!/usr/bin/env python3
"""Two declared forward attempts from shared historical evidence, no slot refill."""
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

from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_authoring_recovery_v44 import MAX_STEPS
from utopia.optimization.native_designer_decoding_v24 import decoding_contracts
from utopia.optimization.native_designer_preflight import EXECUTION_SCOPE, require_certificate, run_calibration
from utopia.optimization.native_designer_roles_v38 import make_local_role_bound_generator, validate_designer_binding
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_initial_evidence import build_initial_evidence, validate_initial_evidence
from utopia.optimization.native_jobs import pinned_revision
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-warmstart-pilot.v45'
CLASSIFICATION = 'actual-native-historical-warm-start-development-v45'
PROTOCOL = 'research/protocols/campaigns/native-warmstart-v45-a1.md'
HISTORICAL_SOURCE = '60ef56ca2e32634c72817676b8bcc55bc9fcaa45'
HISTORICAL_AUDIT = '18ba247752ad258b6661091c254ef7f4383ea176eee0146fdd8a82fab9ca3366'
INITIAL_BANK = '7f3fbefaeae22b3f8e47f2cd2209968a2621f2826ce7217a488a46c0c6b2b0e5'
ARMS = ('efficiency', 'throughput')
LOSSES = {'efficiency': 'native-reviewed-production-efficiency-v13', 'throughput': 'native-joint-v5-throughput'}


def build_plan(*, source_commit, provider_binding, designer_provider_binding,
               runtime_seed_binding, initial_system, bank, historical_audit_manifest=None):
    validate_designer_binding(designer_provider_binding, scientist_binding=provider_binding)
    validate_initial_evidence(bank)
    if (bank['source_audit']['content_sha256'] != HISTORICAL_AUDIT
            or bank['content_sha256'] != INITIAL_BANK):
        raise ValueError('this finite protocol uses only its exact historical audit')
    experiment = {'protocol': PROTOCOL, 'role': 'development-engineering',
        'initial_evidence_sha256': bank['content_sha256']}
    world = {**clone(provider_binding), 'source_commit': source_commit, 'years': 2,
        'population': 'five-independent-balanced-researchers',
        'origin': 'explicit-local-compute-consent', 'experiment': experiment,
        'classification': CLASSIFICATION, 'runtime_seed_binding': clone(runtime_seed_binding)}
    validate_initial_evidence(bank, target_world=world, target_seeds=[42])
    losses = {arm: json.loads((ROOT/'research/objectives/losses'/f'{LOSSES[arm]}.json').read_text())
        for arm in ARMS}
    strategies = {'local-bounded-author': {'kind': 'literal-local-LLM-system-proposal',
        'model': designer_provider_binding['model'], 'conversation_profile': BOUNDED_AUTHORING,
        'protocol': PROTOCOL, 'source_commit': source_commit}}
    bindings = {arm: {'initial_system': clone(initial_system), 'loss_spec': clone(losses[arm]),
        'world': clone(world), 'seeds': [42], 'strategies': clone(strategies), 'mode': 'blackbox',
        'seed': 42, 'learning_rate': .1, 'strategy_learning_rate': .1,
        'strategy_baseline': 0., 'exploration': .1, 'initial_evidence': clone(bank)} for arm in ARMS}
    result = {'schema': SCHEMA, 'classification': CLASSIFICATION, 'source_commit': source_commit,
        'provider_binding': clone(provider_binding), 'designer_provider_binding': clone(designer_provider_binding),
        'runtime_seed_binding': clone(runtime_seed_binding), 'initial_system': clone(initial_system),
        'world_binding': world, 'experiment': experiment, 'losses': losses,
        'campaign_bindings': bindings, 'arm_order': list(ARMS),
        'conversation_profile': BOUNDED_AUTHORING, 'readiness_scope': EXECUTION_SCOPE,
        'initial_evidence_sha256': bank['content_sha256'], 'historical_source_commit': HISTORICAL_SOURCE,
        'historical_audit_content_sha256': HISTORICAL_AUDIT,
        'historical_audit_manifest': clone(historical_audit_manifest),
        'protocol': PROTOCOL, 'protocol_source_sha256': file_sha256(ROOT/PROTOCOL),
        'designer': {'max_steps': MAX_STEPS, 'max_tokens': 8192, 'conversation_profile': BOUNDED_AUTHORING,
            'decoding': decoding_contracts('staged-v15', conversation_profile=BOUNDED_AUTHORING)},
        'budget': {'maximum_new_native_slots': 2, 'new_slots_per_arm': 1,
            'maximum_authoring_POSTs': 2*MAX_STEPS, 'replacement_policy': 'none',
            'maximum_calibration_POSTs': 40,
            'historical_slots_charged_as_new': 0, 'maximum_initial_designer_load_POSTs': 1,
            'maximum_initial_scientist_load_POSTs': 1, 'maximum_per_world_scientist_load_POSTs': 1},
        'claims': {'historical_warm_start': True, 'historical_physical_cache_reuse': False,
            'source_equivalence_established': False, 'new_improvement_established': False,
            'held_out': False, 'scientific_value': False, 'designer_improvement': False,
            'hidden_novelty_or_fairness_veto': False}}
    result['content_sha256'] = digest(result)
    return result


def campaign_from_binding(directory, binding):
    kwargs = {k: clone(v) for k, v in binding.items() if k not in ('initial_system', 'world')}
    return NativeAdaptiveDesignCampaign(directory, initial_system=SystemSpec.from_dict(binding['initial_system']),
        world_binding=binding['world'], **kwargs)


def make_campaigns(root, plan):
    campaigns = {arm: campaign_from_binding(Path(root)/'arms'/arm/'campaign', binding)
        for arm, binding in plan['campaign_bindings'].items()}
    if any(c.binding != plan['campaign_bindings'][arm] for arm, c in campaigns.items()):
        raise ValueError('campaign constructor differs from frozen plan')
    return campaigns


def _save_equal(path, value):
    path = Path(path)
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError('immutable prepared artifact differs: '+str(path))
    else:
        write_json_atomic(path, value, sort_keys=True, allow_nan=False)


def prepare(args):
    from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_open_examples import open_native_system
    source = pinned_revision(ROOT)
    config = json.loads(args.designer_provider_config.read_text())
    if set(config) != {'provider_binding'}:
        raise ValueError('exact local operator designer binding required')
    designer = config['provider_binding']
    audit_path = args.historical_audit.resolve()
    audit_sha = file_sha256(audit_path)
    bank = build_initial_evidence(json.loads(audit_path.read_text()),
        expected_audit_content_sha256=HISTORICAL_AUDIT, expected_source_commit=HISTORICAL_SOURCE)
    if file_sha256(audit_path) != audit_sha:
        raise ValueError('historical audit changed while preparing')
    factory = LocalRoleBoundNativeFactory(args.output/'binding-only-no-worlds', args.data_cache,
        years=2, corpus_years=4, designer_provider=designer)
    executor = DockerCodeExecutor()
    scientist = {k: clone(getattr(factory, k)) for k in
        ('model', 'model_digest', 'corpus_sha256', 'corpus_years', 'dataset_identity')}
    scientist['image_id'] = executor.image_id
    plan = build_plan(source_commit=source, provider_binding=scientist,
        designer_provider_binding=designer, runtime_seed_binding=factory.runtime_seed_binding,
        initial_system=open_native_system(executor.image_id).to_dict(), bank=bank,
        historical_audit_manifest={'path': str(audit_path), 'file_sha256': audit_sha})
    _save_equal(args.output/'bank.json', bank)
    _save_equal(args.output/'plan.json', plan)
    _save_equal(args.output/'operator-config.json', config)
    return plan, make_campaigns(args.output, plan)


def progress(root, plan, campaigns):
    arms, counts = {}, {'complete': 0, 'technical-failure': 0, 'generation-failure': 0}
    for arm, campaign in campaigns.items():
        records = campaign.state['records']
        if len(records) > 1:
            raise ValueError('fixed one-new-slot-per-arm budget exceeded')
        row = {'consumed_slots': len(records), 'pending': campaign.state['pending'] is not None,
            'status': 'pending', 'loss': None}
        if records:
            record = records[0]
            row['status'] = ('generation-failure' if record['generation_error'] else
                'complete' if record['observations'] and record['observations'][0]
                and record['observations'][0]['status'] == 'complete' else 'technical-failure')
            row['loss'] = record['observations'][0]['loss'] if row['status']=='complete' else None
            counts[row['status']] += 1
        arms[arm] = row
    terminal = all(row['consumed_slots'] == 1 and not row['pending'] for row in arms.values())
    result = {'schema': SCHEMA+'.progress', 'source_commit': plan['source_commit'],
        'plan_sha256': plan['content_sha256'], 'arms': arms, 'counts': counts,
        'terminal': terminal, 'consumed_native_slots': sum(r['consumed_slots'] for r in arms.values()),
        'status': 'complete' if terminal and counts['complete']==2 else
            'budget-complete-with-failures' if terminal else 'in-progress'}
    result['content_sha256'] = digest(result)
    write_json_atomic(Path(root)/'progress.json', result, sort_keys=True, allow_nan=False)
    return result


def execute(args):
    from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory, record_loaded_context
    from utopia.optimization.native_scientist_load_v38 import load_local_role, load_scientist
    plan, campaigns = prepare(args)
    if args.action == 'prepare':
        return 0
    designer = plan['designer_provider_binding']
    certificate = args.output/'preflight/certificate.json'
    if args.action == 'calibrate':
        from utopia.optimization.native_designer_preflight import planned_cases
        campaign = campaigns['efficiency']
        request = campaign._request([], campaign._strategy_initial(), 1)
        if len(planned_cases(request, 'staged-v15', BOUNDED_AUTHORING)) > plan['budget']['maximum_calibration_POSTs']:
            raise ValueError('declared calibration budget exceeded before any model dispatch')
        load_local_role(args.output/'role-load-designer-calibration.json', provider=designer,
            purpose='before-v45-calibration', role='designer')
        record_loaded_context(args.output/'loaded-designer-calibration.json',
            expected={'designer': designer}, purpose='before-v45-calibration')
        run_calibration(args.output/'preflight', request=request, provider=designer,
            source_commit=plan['source_commit'], scope=EXECUTION_SCOPE, conversation_profile=BOUNDED_AUTHORING)
        return 0
    require_certificate(certificate, designer, protocol='staged-v15', scope=EXECUTION_SCOPE,
        conversation_profile=BOUNDED_AUTHORING)
    scientist = plan['provider_binding']
    load_scientist(args.output/'role-load-scientist-before-run.json', provider=scientist,
        purpose='before-v45-native-pilot')
    record_loaded_context(args.output/'loaded-scientist-before-run.json', expected={'scientist': scientist},
        purpose='before-v45-native-pilot')
    progress(args.output, plan, campaigns)
    for arm in plan['arm_order']:
        campaign = campaigns[arm]
        if campaign.state['records']:
            continue
        factory = LocalRoleBoundNativeFactory(args.output/'arms'/arm/'worlds', args.data_cache,
            years=2, corpus_years=4, designer_provider=designer, record_wire=True, record_code=True,
            experiment_binding=plan['experiment'], inference_lock=args.output/'inference.lock')
        generator = make_local_role_bound_generator(args.output/'arms'/arm/'authoring',
            image_id=scientist['image_id'], provider_binding=designer, max_steps=MAX_STEPS,
            max_tokens=8192, inference_lock=args.output/'inference.lock',
            preflight_certificate=certificate, readiness_scope=EXECUTION_SCOPE,
            conversation_profile=BOUNDED_AUTHORING)
        campaign.advance(simulation_factory=factory, generators={'local-bounded-author': generator}, count=1)
        result = progress(args.output, plan, campaigns)
        print(json.dumps({'arm': arm, **result['arms'][arm]}), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'calibrate', 'run'))
    parser.add_argument('--execute-authorized', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--designer-provider-config', type=Path, required=True)
    parser.add_argument('--historical-audit', type=Path, required=True)
    args = parser.parse_args(argv)
    args.output = args.output.resolve(); args.output.mkdir(parents=True, exist_ok=True)
    source = pinned_revision(ROOT)
    with (args.output/'pilot-writer.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX|fcntl.LOCK_NB)
        prefix = 'writer' if args.action == 'run' else args.action
        started = args.output/f'{prefix}.started.json'; ended = args.output/f'{prefix}.ended.json'
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
