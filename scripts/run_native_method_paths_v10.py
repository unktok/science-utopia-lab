#!/usr/bin/env python3
"""Three adaptive native evaluations per method; one fixed scientific objective."""
import argparse
import fcntl
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utopia.optimization.loss import load_loss_spec, loss_spec_sha256
from utopia.optimization.native_hybrid import native_endpoint, project_continuous
from utopia.optimization.native_method_paths import (ACTUAL, SCHEMA, EXPERIMENT,
    GRADIENT_RULE, SCHEDULE, read, load_shared_historical, historical_observations, fit_path_operator)
from utopia.optimization.native_path_policies import NativePathPolicy
from utopia.optimization.native_qwen_response import control_proof, require_same_control
from utopia.optimization.native_relaxation import replay_tensor_trace, trace_objective
from utopia.optimization.native_response_fidelity import make_response_completion_receipt, programs
from utopia.optimization.native_response_prefix import prepare_common_prefix, install_common_prefix
from utopia.system.design_patch import digest
from utopia.system import SystemSpec
from utopia.system.native_response_examples import DECLARATIONS, TERMS, response_gradient_system
from utopia.system.native_review_identity import enable_review_identity_recording
from utopia.utils.data_utils import file_sha256, write_json_atomic

MODEL = 'qwen3:8b'
PROTOCOL = 'research/protocols/campaigns/native-method-paths-v10.md'


def save(path, value):
    value = {k: v for k, v in value.items() if k != 'content_sha256'}
    value['content_sha256'] = digest(value)
    write_json_atomic(path, value, sort_keys=True, allow_nan=False)
    return value


def execute_world(factory, system, world, prepared, anchor, name, theta, output):
    objective = load_loss_spec(ROOT/'research/objectives/losses/native-joint-v5-net-reviewed-utility.json')
    candidate, projection = project_continuous(system, DECLARATIONS, {'evidence-weight': theta})
    root, sim, controller = output/'worlds'/name, None, None
    started = time.time()
    print(json.dumps({'event': 'world-start', 'name': name, 'theta': theta}), flush=True)
    try:
        sim = factory(candidate, 42, name)
        enable_review_identity_recording(sim)
        if prepared is not None:
            controller = install_common_prefix(sim, prepared, root/'wire-requests.jsonl')
        sim.run()
        prefix = controller.complete() if controller else None
        if prefix:
            write_json_atomic(root/'common-prefix-receipt.json', prefix, sort_keys=True, allow_nan=False)
        endpoint = native_endpoint(Path(sim.output_dir)/'portable_checkpoint_year_2.json.gz',
            candidate, DECLARATIONS, objective, world=world, code_contexts=root/'code-contexts.jsonl')
        hard = float(trace_objective(replay_tensor_trace(endpoint['trace'], programs(endpoint),
            hard=True, verify_recorded=True), TERMS))
        if abs(hard-endpoint['native_loss']) > 1e-10:
            raise ValueError('original native loss and hard tensor accounting differ')
        receipt = make_response_completion_receipt(endpoint, sim.llm.response_cache,
            root/'wire-requests.jsonl', run_manifest_sha256=file_sha256(
                root/'simulation/docs/native-design/run_manifest.json'))
        write_json_atomic(root/'completion-receipt.json', receipt, sort_keys=True, allow_nan=False)
        proof = control_proof(endpoint, root)
        if prepared:
            require_same_control([proof, control_proof(prepared['anchor_endpoint'], anchor)])
        row = {'name': name, 'theta': theta, 'endpoint': endpoint, 'projection': projection,
            'control_proof': proof, 'completion_receipt': receipt,
            'elapsed_seconds': time.time()-started, 'hard_represented_loss': hard,
            'fresh_physical_replies': prefix['fresh_physical_reply_count'] if prefix else endpoint['response_cache_count'],
            'numeric_response_evidence': {'journal': str(root/'replies/responses.sqlite'),
                'wire': str(root/'wire-requests.jsonl'), 'mechanism': 'addressed-selection',
                'input_name': 'features', 'completion_receipt': receipt}}
        if prefix:
            row.update(common_prefix_receipt=prefix, logical_response_count=endpoint['response_cache_count'],
                replayed_response_count=prefix['replayed_response_count'])
        print(json.dumps({'event': 'world-complete', 'name': name, 'theta': theta,
            'loss': endpoint['native_loss'], 'fresh_physical_replies': row['fresh_physical_replies'],
            'elapsed_seconds': row['elapsed_seconds']}), flush=True)
        return row
    except BaseException:
        if controller:
            write_json_atomic(root/'common-prefix-partial-receipt.json',
                controller.receipt(require_complete=False), sort_keys=True, allow_nan=False)
        raise
    finally:
        if sim is not None:
            sim.llm.response_cache.close()


def run(args):
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.system.code_mechanisms import DockerCodeExecutor
    # A stopped/complete campaign is immutable. Do not silently reroll a partial.
    if any(path.name != 'runner.lock' for path in args.output.iterdir()):
        raise ValueError('existing v10 output is immutable; use an explicit prospective amendment')
    shared = load_shared_historical(args.historical_audit)
    anchor = Path(shared['anchor_world_dir']).resolve()
    prepared = prepare_common_prefix(anchor, shared['anchor_endpoint'])
    executor = DockerCodeExecutor()
    system = response_gradient_system(executor.image_id)
    objective = load_loss_spec(ROOT/'research/objectives/losses/native-joint-v5-net-reviewed-utility.json')
    factory = LocalQwenNativeFactory(args.output/'worlds', args.data_cache, years=2, corpus_years=4,
        model=MODEL, experiment_binding=EXPERIMENT, record_wire=True, record_code=True,
        inference_lock=args.inference_lock)
    normalized, _ = project_continuous(SystemSpec.from_dict(
        prepared['anchor_endpoint']['system']), DECLARATIONS, {'evidence-weight': .5})
    if (prepared['anchor_model'] != MODEL or normalized.to_dict() != system.to_dict()
            or prepared['anchor_endpoint']['world']['model_digest'] != factory.model_digest
            or prepared['anchor_endpoint']['world']['corpus_sha256'] != factory.corpus_sha256):
        raise ValueError('historical prefix does not match this fixed model/corpus/native system')
    world = {'source_commit': factory.source_commit, 'model_digest': factory.model_digest,
        'corpus_sha256': factory.corpus_sha256, 'seed': 42, 'years': 2, 'corpus_years': 4,
        'runtime_seed_binding': factory.runtime_seed_binding, 'experiment': EXPERIMENT, 'classification': ACTUAL}
    plan = {'schema': SCHEMA, 'classification': ACTUAL, 'world': world,
        'population': {'authors': 5, 'institutions': 5}, 'image_id': executor.image_id,
        'loss_spec': objective, 'system': system.to_dict(), 'declarations': DECLARATIONS, 'terms': TERMS,
        'shared_historical': shared, 'method_configs': {'gradient': GRADIENT_RULE,
            'blackbox': {'rule': 'incumbent-adjacent widest-interval bisection; lower interval and earliest observation ties'}},
        'schedule': SCHEDULE, 'fresh_budget_per_arm': 3, 'initial_current_theta': .5,
        'domain': [.2, .8], 'protocol_sha256': file_sha256(ROOT/PROTOCOL),
        'response_coupling': {'mode': 'actual-common-prefix-replay',
            'unique_anchor_prefix_calls': prepared['prefix_count'], 'prepared': prepared}}
    # Verify source-equivalent historical fit BEFORE any fresh model call.
    fit_path_operator(shared['rows'], objective, GRADIENT_RULE['temperature_schedule'][0], ROOT)
    save(args.output/'plan.json', plan)
    history = historical_observations(shared)
    policies = {arm: NativePathPolicy.create(args.output/'policies'/f'{arm}.json',
        method='represented-gradient' if arm == 'gradient' else 'blackbox', historical=history,
        loss_spec_sha256=loss_spec_sha256(objective), world_binding=world, fresh_budget=3,
        gradient_rule=GRADIENT_RULE if arm == 'gradient' else None) for arm in ('gradient', 'blackbox')}
    evidence = {'schema': SCHEMA, 'classification': ACTUAL, 'source_commit': factory.source_commit,
        'plan': plan, 'status': 'in-progress', 'endpoints': [], 'failures': [], 'steps': [],
        'claims': {'actual_fixed_weight_Qwen': True, 'exact_Qwen_Jacobian': False,
            'full_native_world_autograd': False, 'held_out_seeds': False,
            'optimizer_superiority': False, 'causal_scientific_benefit': False}}
    save(args.output/'evidence.json', evidence)
    for item in SCHEDULE:
        arm, step, name = item['arm'], item['step'], item['name']
        policy, backward, operator_record = policies[arm], None, None
        try:
            if arm == 'gradient':
                eligible = shared['rows']+[r for r in evidence['endpoints'] if r['arm'] == 'gradient']
                temperature = GRADIENT_RULE['temperature_schedule'][step]
                operator = fit_path_operator(eligible, objective, temperature, ROOT)
                operator_path = args.output/'operators'/f'{name}.json'
                operator_path.parent.mkdir(parents=True, exist_ok=True)
                operator.save(operator_path)
                backward = {**operator.backward([policy.summary()['current_theta']]), 'temperature': temperature}
                operator_record = {'path': str(operator_path), 'file_sha256': file_sha256(operator_path),
                    'representation_sha256': operator._hash,
                    'eligible_endpoint_sha256s': [r['endpoint']['checkpoint_sha256'] for r in eligible]}
            proposal = policy.ask(backward=backward)
            frozen = save(args.output/'proposals'/f'{name}.json',
                {'schema': SCHEMA+'.proposal', **item, 'proposal': proposal, 'operator': operator_record})
            evidence['steps'].append(frozen)
            save(args.output/'evidence.json', evidence)
            row = execute_world(factory, system, world, prepared, anchor, name, proposal['candidate_theta'], args.output)
            row.update(arm=arm, step=step, proposal_sha256=proposal['content_sha256'])
            observation = {'theta': row['theta'], 'status': 'complete', 'loss': row['endpoint']['native_loss'],
                'loss_spec_sha256': loss_spec_sha256(objective), 'world_binding_sha256': digest(world),
                'provenance': {'endpoint_record_sha256': digest(row['endpoint']),
                    'checkpoint_sha256': row['endpoint']['checkpoint_sha256']}}
            policy.tell(proposal['content_sha256'], observation)
            row['observation'] = observation
            evidence['endpoints'].append(row)
            evidence['policies'] = {key: value.summary() for key, value in policies.items()}
            save(args.output/'evidence.json', evidence)
        except BaseException as error:
            failure = {**item, 'error_type': type(error).__name__, 'error': str(error)[:4000], 'loss': None}
            evidence['failures'].append(failure)
            if policy.state.get('pending') is not None:
                pending = policy.state['pending']
                policy.tell(pending['content_sha256'], {'theta': pending['candidate_theta'],
                    'status': 'technical-failure', 'loss': None, 'error': failure,
                    'loss_spec_sha256': loss_spec_sha256(objective), 'world_binding_sha256': digest(world),
                    'provenance': {'preserved_world_directory': str(args.output/'worlds'/name)}})
            evidence['status'] = 'stopped-with-preserved-failure'
            evidence['policies'] = {key: value.summary() for key, value in policies.items()}
            save(args.output/'evidence.json', evidence)
            raise
    evidence.update(status='complete', physical_native_worlds=len(evidence['endpoints']),
        all_control_check=require_same_control([r['control_proof'] for r in evidence['endpoints']]),
        physical_reply_count=sum(r['fresh_physical_replies'] for r in evidence['endpoints']),
        logical_response_count=sum(r['logical_response_count'] for r in evidence['endpoints']),
        replayed_response_count=sum(r['replayed_response_count'] for r in evidence['endpoints']))
    return save(args.output/'evidence.json', evidence)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--inference-lock', type=Path, required=True)
    parser.add_argument('--historical-audit', type=Path,
        default=ROOT/'research/results/native-qwen-response-v9-a3.json')
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output/'runner.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run(args)
    print(json.dumps({'status': result['status'], 'worlds': result['physical_native_worlds'],
        'replies': result['physical_reply_count']}), flush=True)


if __name__ == '__main__':
    main()
