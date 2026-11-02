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
MODEL = 'qwen3:8b'
WORLD_NAMES = ['calibration-0', 'calibration-1', 'calibration-2', 'unused-0', 'unused-1', 'gradient-candidate']


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


def preflight_saved_artifacts(output):
    """Reject orphaned fit/proposal or illegal world prefixes before inference.

    A plan-bound interrupted native world may be resumed by its existing
    factory/checkpoint binding. This check does not delete, repair or adopt any
    stale directory, and never executes a saved operator or model.
    """
    evidence_path = output/'evidence.json'
    operator_path, proposal_path = output/'response-operator.json', output/'frozen-proposal.json'
    if not evidence_path.exists():
        if operator_path.exists() or proposal_path.exists():
            raise ValueError('orphaned saved operator/proposal has no authoritative native evidence prefix')
        return
    evidence = read(evidence_path)
    if evidence.get('status') == 'complete':
        raise ValueError('completed evidence is immutable; inspect it instead of rerunning')
    if (evidence.get('schema') != SCHEMA or evidence.get('classification') != ACTUAL
            or not isinstance(evidence.get('endpoints'), list)
            or len(evidence['endpoints']) > len(WORLD_NAMES)
            or any(not isinstance(row, dict) for row in evidence['endpoints'])
            or [row.get('name') for row in evidence['endpoints']] != WORLD_NAMES[:len(evidence['endpoints'])]):
        raise ValueError('saved evidence does not have a unique legal world prefix')
    if evidence.get('failures'):
        raise ValueError('failed attempt retained; explicit prospective amendment required before further execution')
    count = len(evidence['endpoints'])
    if (operator_path.exists() or proposal_path.exists()) and count < len(CALIBRATION):
        raise ValueError('orphaned saved operator/proposal precedes its complete native calibration prefix')
    if proposal_path.exists() and not operator_path.exists():
        raise ValueError('frozen proposal has no saved calibration operator')
    if count > len(CALIBRATION) and (not operator_path.exists() or not proposal_path.exists()):
        raise ValueError('unused/proposed native world lacks its frozen operator/proposal')
    # These formats carry content hashes. Check their bytes before any new
    # physical world; the normal later loader independently restores full native
    # calibration provenance and recomputes the exact saved representation.
    for path in (operator_path, proposal_path):
        if path.exists():
            value = read(path)
            if not isinstance(value, dict) or 'content_sha256' not in value:
                raise ValueError('saved operator/proposal has no content hash: '+str(path))


def run(args):
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_review_identity import enable_review_identity_recording
    preflight_saved_artifacts(args.output)
    common_prefix = None
    anchor = getattr(args, 'common_prefix_anchor', None)
    if anchor:
        if getattr(args, 'amendment', False):
            raise ValueError('a2 and a3 amendments are separate, not combined implicitly')
        from utopia.optimization.native_response_prefix import prepare_common_prefix
        anchor = Path(anchor).resolve()
        origin = read(anchor.parent.parent/'evidence.json')
        original = [r['endpoint'] for r in origin['endpoints'] if r['name'] == anchor.name]
        if len(original) != 1:
            raise ValueError('common prefix requires one completed actual anchor endpoint')
        common_prefix = prepare_common_prefix(anchor, original[0])
    executor = DockerCodeExecutor()
    system = response_gradient_system(executor.image_id)
    objective = load_loss_spec(ROOT/'research/objectives/losses/native-joint-v5-net-reviewed-utility.json')
    factory = LocalQwenNativeFactory(args.output/'worlds', args.data_cache,
        years=2, corpus_years=4, model=MODEL, experiment_binding=EXPERIMENT,
        record_wire=True, record_code=True, inference_lock=args.inference_lock)
    if common_prefix:
        from utopia.system import SystemSpec
        origin = common_prefix['anchor_endpoint']
        normalized, _ = project_continuous(SystemSpec.from_dict(origin['system']), DECLARATIONS,
            {'evidence-weight': .5})
        if (common_prefix['anchor_classification'] != ACTUAL or common_prefix['anchor_model'] != MODEL
                or origin['world']['model_digest'] != factory.model_digest
                or origin['world']['corpus_sha256'] != factory.corpus_sha256
                or origin['world']['seed'] != 42 or origin['world'].get('years') != 2
                or normalized.to_dict() != system.to_dict()):
            raise ValueError('prefix anchor is not this actual fixed-Qwen original world and noncoordinate institution')
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
    if common_prefix:
        plan['amendment'] = {'id': 'native-qwen-response-gradient-v9-a3',
            'sha256': file_sha256(ROOT/'research/protocols/campaigns/native-qwen-response-gradient-v9-a3.md'),
            'prior_world_attempts': 4, 'prior_completed_worlds': 2, 'prior_partial_worlds': 2,
            'prior_physical_replies': 228, 'maximum_combined_world_attempts': 10,
            'changes': 'replay an exact actual Qwen pre-intervention history; generate affected and later replies freshly'}
        plan['response_coupling'] = {'mode': 'actual-common-prefix-replay',
            'unique_anchor_prefix_calls': common_prefix['prefix_count'], 'prepared': common_prefix}
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
    allowed = WORLD_NAMES
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
        started, sim, prefix_controller = time.time(), None, None
        print(json.dumps({'event': 'world-start', 'name': name, 'theta': theta}), flush=True)
        try:
            sim = factory(candidate, 42, name)
            enable_review_identity_recording(sim)
            if common_prefix:
                from utopia.optimization.native_response_prefix import install_common_prefix
                prefix_controller = install_common_prefix(sim, common_prefix, root/'wire-requests.jsonl')
            sim.run()
            prefix_receipt = prefix_controller.complete() if prefix_controller else None
            if prefix_receipt:
                write_json_atomic(root/'common-prefix-receipt.json', prefix_receipt, sort_keys=True, allow_nan=False)
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
            if common_prefix:
                require_same_control([proof, control_proof(common_prefix['anchor_endpoint'], anchor)])
            row = {'name': name, 'theta': theta, 'endpoint': endpoint, 'projection': projection,
                'control_proof': proof, 'completion_receipt': receipt, 'elapsed_seconds': time.time()-started,
                'hard_represented_loss': hard,
                'fresh_physical_replies': prefix_receipt['fresh_physical_reply_count'] if prefix_receipt else endpoint['response_cache_count'],
                'numeric_response_evidence': {'journal': str(root/'replies/responses.sqlite'),
                    'wire': str(root/'wire-requests.jsonl'), 'mechanism': 'addressed-selection',
                    'input_name': 'features', 'completion_receipt': receipt}}
            if prefix_receipt:
                row.update(common_prefix_receipt=prefix_receipt,
                    logical_response_count=endpoint['response_cache_count'],
                    replayed_response_count=prefix_receipt['replayed_response_count'])
                if row['fresh_physical_replies']+row['replayed_response_count'] != row['logical_response_count']:
                    raise ValueError('logical and actual physical response counts differ from the replay receipt')
            evidence['endpoints'].append(row)
            save(evidence_path, evidence)
            print(json.dumps({'event': 'world-complete', 'name': name, 'theta': theta,
                'loss': endpoint['native_loss'], 'replies': endpoint['response_cache_count'],
                'elapsed_seconds': row['elapsed_seconds']}), flush=True)
            return row
        except BaseException as error:
            if prefix_controller:
                partial = prefix_controller.receipt(require_complete=False)
                write_json_atomic(root/'common-prefix-partial-receipt.json', partial, sort_keys=True, allow_nan=False)
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
        if common_prefix:
            fresh = sum(r['fresh_physical_replies'] for r in evidence['endpoints'])
            evidence.update(response_coupling=plan['response_coupling'],
                logical_response_count=sum(r['logical_response_count'] for r in evidence['endpoints']),
                fresh_physical_reply_count=fresh,
                unique_actual_calls_supporting_this_campaign=common_prefix['prefix_count']+fresh,
                all_v9_actual_physical_replies=228+fresh)
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
    parser.add_argument('--common-prefix-anchor', type=Path,
        help='Bind prospective a3 coupling to one completed actual Qwen world, never a synthetic anchor')
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
