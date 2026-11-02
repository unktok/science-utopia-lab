#!/usr/bin/env python3
"""Six bounded actual-Qwen worlds, frozen local fit and native reevaluation."""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utopia.optimization.loss import load_loss_spec
from utopia.optimization.native_hybrid import native_endpoint, project_continuous
from utopia.optimization.native_qwen_response import control_proof, gradient_proposal, require_same_control
from utopia.optimization.native_relaxation import replay_tensor_trace, trace_objective
from utopia.optimization.native_response_fidelity import (
    NativeResponseOperator, boundary_layout, endpoint_decomposition, make_response_completion_receipt, programs, raw_review_projection,
)
from utopia.system.design_patch import digest
from utopia.system.native_response_examples import DECLARATIONS, TERMS, response_gradient_system
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-qwen-response-loop.v9'
ACTUAL = 'actual-native-qwen-response-gradient-development-v9'
EXPERIMENT = {'protocol': 'native-qwen-response-gradient-v9', 'role': 'development-engineering',
    'review_task_identity_recording': True, 'public_payload_only_review_context': True}
CALIBRATION = [.2, .5, .8]
UNUSED = [.35, .65]


def read(path):
    value = json.loads(path.read_text())
    if 'content_sha256' in value and value['content_sha256'] != digest({k: v for k, v in value.items() if k != 'content_sha256'}):
        raise ValueError('saved evidence content hash differs: '+str(path))
    return value


def save(path, value):
    value = {k: v for k, v in value.items() if k != 'content_sha256'}
    value['content_sha256'] = digest(value)
    write_json_atomic(path, value, sort_keys=True, allow_nan=False)
    return value


def run(args):
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_review_identity import enable_review_identity_recording
    if (args.output/'evidence.json').exists():
        existing = read(args.output/'evidence.json')
        if existing.get('status') == 'complete':
            raise ValueError('completed evidence is immutable; inspect it instead of rerunning')
    executor = DockerCodeExecutor()
    system = response_gradient_system(executor.image_id)
    objective = load_loss_spec(ROOT/'research/objectives/losses/native-joint-v5-net-reviewed-utility.json')
    factory = LocalQwenNativeFactory(args.output/'worlds', args.data_cache,
        years=2, corpus_years=4, experiment_binding=EXPERIMENT,
        record_wire=True, record_code=True, inference_lock=args.inference_lock)
    world = {'source_commit': factory.source_commit, 'model_digest': factory.model_digest,
        'corpus_sha256': factory.corpus_sha256, 'seed': 42, 'years': 2, 'corpus_years': 4,
        'runtime_seed_binding': factory.runtime_seed_binding, 'experiment': EXPERIMENT,
        'classification': ACTUAL}
    plan = {'schema': SCHEMA, 'classification': ACTUAL, 'world': world,
        'population': {'authors': 5, 'institutions': 5}, 'image_id': executor.image_id,
        'loss_spec': objective, 'system': system.to_dict(), 'declarations': DECLARATIONS, 'terms': TERMS,
        'calibration': CALIBRATION, 'unused': UNUSED, 'maximum_native_worlds': 6,
        'temperatures': [1., .2, .05, .01], 'candidate_rule': 'center point .5, lr .02, displacement clamp +/-.10, support [.2,.8]',
        'protocol_sha256': file_sha256(ROOT/'research/protocols/campaigns/native-qwen-response-gradient-v9.md')}
    if getattr(args, 'amendment', False):
        plan['amendment'] = {'id': 'native-qwen-response-gradient-v9-a2',
            'sha256': file_sha256(ROOT/'research/protocols/campaigns/native-qwen-response-gradient-v9-a2.md'),
            'prior_maximum_worlds': 3, 'maximum_combined_physical_worlds': 9,
            'changes': 'exclude only server envelope metadata from cross-world semantic response equality'}
    plan_path = args.output/'plan.json'
    if plan_path.exists() and read(plan_path) != plan:
        raise ValueError('frozen plan/source/objective/model/corpus differs')
    if not plan_path.exists():
        write_json_atomic(plan_path, plan, sort_keys=True, allow_nan=False)
    evidence_path = args.output/'evidence.json'
    evidence = read(evidence_path) if evidence_path.exists() else {
        'schema': SCHEMA, 'classification': ACTUAL, 'source_commit': factory.source_commit,
        'plan': plan, 'status': 'in-progress', 'endpoints': [], 'failures': [],
        'claims': {'actual_fixed_weight_Qwen': True, 'scripted_researcher_HTTP': False,
            'exact_Qwen_Jacobian': False, 'full_native_world_autograd': False,
            'held_out_seeds': False, 'causal_scientific_benefit': False}}
    if evidence['failures']:
        raise ValueError('failed attempt retained; explicit prospective amendment required before further execution')
    allowed = ['calibration-0', 'calibration-1', 'calibration-2', 'unused-0', 'unused-1', 'gradient-candidate']
    if (evidence.get('schema') != SCHEMA or evidence.get('classification') != ACTUAL
            or evidence.get('source_commit') != factory.source_commit or evidence.get('plan') != plan
            or [r['name'] for r in evidence['endpoints']] != allowed[:len(evidence['endpoints'])]
            or len(evidence['endpoints']) > 6):
        raise ValueError('saved evidence does not bind this plan/source or a unique legal world prefix')

    def execute(name, theta):
        prior = next((r for r in evidence['endpoints'] if r['name'] == name), None)
        candidate, projection = project_continuous(system, DECLARATIONS, {'evidence-weight': theta})
        root = args.output/'worlds'/name
        if prior:
            if prior['theta'] != theta or prior['projection'] != projection:
                raise ValueError('saved world belongs to another proposed coordinate')
            restored = native_endpoint(root/'simulation/checkpoints/native-design/portable_checkpoint_year_2.json.gz',
                candidate, DECLARATIONS, objective, world=world, code_contexts=root/'code-contexts.jsonl')
            if restored != prior['endpoint'] or control_proof(restored, root) != prior['control_proof']:
                raise ValueError('saved endpoint/control differs from independently restored actual raw')
            layout, numeric, _ = boundary_layout(restored)
            raw_review_projection(restored, layout, numeric, **prior['numeric_response_evidence'])
            return prior
        started, sim = time.time(), None
        print(json.dumps({'event': 'world-start', 'name': name, 'theta': theta}), flush=True)
        try:
            sim = factory(candidate, 42, name)
            enable_review_identity_recording(sim)
            sim.run()
            endpoint = native_endpoint(Path(sim.output_dir)/'portable_checkpoint_year_2.json.gz',
                candidate, DECLARATIONS, objective, world=world,
                code_contexts=args.output/'worlds'/name/'code-contexts.jsonl')
            hard = float(trace_objective(replay_tensor_trace(endpoint['trace'], programs(endpoint), hard=True,
                verify_recorded=True), TERMS))
            if abs(hard-endpoint['native_loss']) > 1e-10:
                raise ValueError('actual tensor accounting does not reproduce the fixed native loss')
            receipt = make_response_completion_receipt(endpoint, sim.llm.response_cache,
                root/'wire-requests.jsonl', run_manifest_sha256=file_sha256(root/'simulation/docs/native-design/run_manifest.json'))
            write_json_atomic(root/'completion-receipt.json', receipt, sort_keys=True, allow_nan=False)
            proof = control_proof(endpoint, root)
            row = {'name': name, 'theta': theta, 'endpoint': endpoint, 'projection': projection,
                'control_proof': proof, 'completion_receipt': receipt, 'elapsed_seconds': time.time()-started,
                'hard_represented_loss': hard, 'fresh_physical_replies': endpoint['response_cache_count'],
                'numeric_response_evidence': {'journal': str(root/'replies/responses.sqlite'),
                    'wire': str(root/'wire-requests.jsonl'), 'mechanism': 'addressed-selection',
                    'input_name': 'features', 'completion_receipt': receipt}}
            evidence['endpoints'].append(row)
            save(evidence_path, evidence)
            print(json.dumps({'event': 'world-complete', 'name': name, 'theta': theta,
                'loss': endpoint['native_loss'], 'replies': endpoint['response_cache_count'],
                'elapsed_seconds': row['elapsed_seconds']}), flush=True)
            return row
        except BaseException as error:
            evidence['failures'].append({'name': name, 'theta': theta, 'error_type': type(error).__name__,
                'error': str(error)[:4000], 'loss': None, 'elapsed_seconds': time.time()-started})
            evidence['status'] = 'stopped-with-preserved-failure'
            save(evidence_path, evidence)
            raise
        finally:
            if sim is not None:
                sim.llm.response_cache.close()

    try:
        calibration = [execute('calibration-'+str(i), x) for i, x in enumerate(CALIBRATION)]
        evidence['calibration_control_check'] = require_same_control([r['control_proof'] for r in calibration])
        fit_evidence = {r['endpoint']['checkpoint_sha256']: r['numeric_response_evidence'] for r in calibration}
        operator_path = args.output/'response-operator.json'
        if operator_path.exists():
            operator = NativeResponseOperator.load(operator_path)
            if (operator.state['calibration'] != [r['endpoint'] for r in calibration]
                    or operator.state['numeric_response_evidence'] != fit_evidence
                    or operator.state['loss_spec'] != objective
                    or operator.state['terms'] != TERMS or operator.state['declarations'] != DECLARATIONS):
                raise ValueError('saved operator differs from this exact calibration/plan/objective/evidence')
        else:
            operator = NativeResponseOperator.fit([r['endpoint'] for r in calibration], DECLARATIONS,
                objective, TERMS, temperatures=plan['temperatures'], numeric_response_evidence=fit_evidence)
            operator.save(operator_path)
        backward = operator.backward([.5])
        proposal = gradient_proposal(backward)
        frozen = {'schema': SCHEMA+'.frozen-proposal', 'backward': backward, 'proposal': proposal,
            'operator_file_sha256': file_sha256(operator_path), 'temperature_selection': operator.state['temperature_selection'],
            'calibration_checkpoint_sha256s': [r['endpoint']['checkpoint_sha256'] for r in calibration],
            'unused_outcomes_seen': 0}
        frozen_path = args.output/'frozen-proposal.json'
        if frozen_path.exists() and read(frozen_path) != {**frozen, 'content_sha256': digest(frozen)}:
            raise ValueError('proposal/operator changed after being frozen')
        if not frozen_path.exists():
            save(frozen_path, frozen)
        evidence['frozen_proposal'] = read(frozen_path)
        save(evidence_path, evidence)
        unused = [execute('unused-'+str(i), x) for i, x in enumerate(UNUSED)]
        candidate = execute('gradient-candidate', proposal['candidate'])
        evidence['all_control_check'] = require_same_control([r['control_proof'] for r in evidence['endpoints']])
        endpoints = [r['endpoint'] for r in unused]
        evidence.update(status='complete', physical_native_worlds=len(evidence['endpoints']),
            physical_reply_count=sum(r['fresh_physical_replies'] for r in evidence['endpoints']),
            unused_checks=[operator.validate_unused(p) for p in endpoints],
            unused_finite_path=operator.integrated_check(*endpoints, quadrature=128),
            unused_decomposition=endpoint_decomposition(*endpoints, DECLARATIONS, TERMS,
                temperature=operator.state['temperature']),
            candidate_check=operator.validate_unused(candidate['endpoint']),
            native_candidate_minus_center=candidate['endpoint']['native_loss']-calibration[1]['endpoint']['native_loss'],
            operator_sha256=file_sha256(operator_path), operator_representation_sha256=operator._hash,
            raw_fit_rmse=operator.state['raw_fit_rmse'])
        return save(evidence_path, evidence)
    except BaseException as error:
        if not evidence['failures']:
            evidence['failures'].append({'stage': 'fit-control-or-report', 'error_type': type(error).__name__,
                'error': str(error)[:4000], 'loss': None})
        evidence['status'] = 'stopped-with-preserved-failure'
        save(evidence_path, evidence)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--inference-lock', type=Path, required=True)
    parser.add_argument('--amendment', action='store_true', help='Bind the prospective a2 server-envelope comparison amendment')
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
