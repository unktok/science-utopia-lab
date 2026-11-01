#!/usr/bin/env python3
"""Continue immutable v3 native data with an explicit analysis-only identity fix.

Waits for the six already-budgeted worlds; never reruns or alters them. Removes
only the archive destination from scientific-state identity after verifying the
original extraction exactly. At most one already-planned gradient proposal is
then evaluated under identical execution-only source, not hidden extra seeds.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import torch
    from scripts.prepare_native_de_novo_design import runtime_tree
    from utopia.optimization.loss import load_loss_spec
    from utopia.optimization.native_design import NativeDesignCampaign
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.optimization.native_transition_autograd import NativeTransitionSurrogate, heldout_directional_check
    from utopia.optimization.native_transition_data import verify_saved_trajectory, compile_terminal_loss, extract_trajectory
    from utopia.system import SystemSpec
    from utopia.system.code_mechanisms import sha
    from utopia.system.design_patch import clone
    from utopia.utils.data_utils import write_json_atomic
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--loss', type=Path, required=True)
    parser.add_argument('--inference-lock', type=Path, required=True)
    parser.add_argument('--wait-seconds', type=int, default=10800)
    args = parser.parse_args()
    if args.wait_seconds < 0 or args.wait_seconds > 43200:
        parser.error('bounded wait0..43200 seconds required')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        parser.error('continuation requires clean commit-pinned source')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    upstream = args.upstream.resolve()
    plan = json.loads((upstream / 'plan.json').read_text())
    loss = load_loss_spec(args.loss)
    if plan['loss_spec'] != loss or not plan['world']['source_commit'].startswith('8a114f3'):
        raise ValueError('continuation is restricted to the recorded original v3 plan and loss')
    old_runtime, new_runtime = runtime_tree(plan['world']['source_commit']), runtime_tree(commit)
    if old_runtime != new_runtime:
        raise ValueError('analysis continuation must not change native execution source')
    args.output.mkdir(parents=True, exist_ok=True)
    binding = {'schema': 'scienceutopia.native-transition-continuation-plan.v1', 'upstream': str(upstream),
        'upstream_plan_sha256': sha(plan), 'analysis_and_proposal_source_commit': commit,
        'native_data_source_commit': plan['world']['source_commit'], 'execution_only_source_sha256': old_runtime,
        'loss_spec': loss, 'amendment': 'exclude paper_tracker.output_dir only after exact legacy re-extraction verification',
        'native_calibration_worlds_rerun': 0, 'new_native_proposal_budget': int(plan['evaluate_proposal'])}
    path = args.output / 'plan.json'
    if path.exists() and json.loads(path.read_text()) != binding:
        raise ValueError('continuation binding changed')
    write_json_atomic(path, binding, sort_keys=True, allow_nan=False)
    if (args.output / 'completion.json').exists():
        print((args.output / 'completion.json').read_text(), flush=True)
        return
    deadline = time.monotonic() + args.wait_seconds
    needed = [upstream / 'cells' / name / 'trajectory.json' for name, _ in plan['cells']]
    while not all(p.exists() for p in needed):
        count = sum(p.exists() for p in needed)
        write_json_atomic(args.output / 'progress.json', {'status': 'waiting-for-original-native-cells',
            'complete_calibration_cells': count, 'planned_calibration_cells': 6,
            'checked_at_utc': datetime.now(timezone.utc).isoformat()}, allow_nan=False)
        if time.monotonic() >= deadline:
            raise TimeoutError('bounded wait expired; original cells preserved, no extra worlds launched')
        time.sleep(10)
    trajectories, evidence, amendments, baseline_record = [], [], [], None
    world = plan['world']
    for name, controls in plan['cells']:
        saved = json.loads((upstream / 'cells' / name / 'campaign/native-design-state.json').read_text())
        if saved['pending'] is not None or len(saved['records']) != 1:
            raise ValueError('one completed original native world per control schedule required')
        record = saved['records'][0]
        if baseline_record is None:
            baseline_record = record
        trajectory, proof, amendment = verify_saved_trajectory(record,
            json.loads((upstream / 'cells' / name / 'trajectory.json').read_text()),
            run_directory=upstream / 'runs', source_commit=world['source_commit'], model_digest=world['model_digest'],
            corpus_sha256=world['corpus_sha256'], controls=controls, loss_spec=loss)
        trajectories.append(trajectory)
        evidence.append(proof)
        amendments.append(amendment)
    write_json_atomic(args.output / 'verified-native-data.json', {'binding': binding,
        'trajectories': [asdict(t) for t in trajectories], 'evidence': evidence, 'identity_amendments': amendments}, sort_keys=True, allow_nan=False)
    try:
        model = NativeTransitionSurrogate.fit(trajectories[:4], compile_terminal_loss(loss))
        query = torch.tensor(plan['gradient_query'], dtype=torch.float64, requires_grad=True)
        value, states, support = model.evaluate(torch.tensor(trajectories[0].states[0], dtype=torch.float64), query)
        value.backward()
        if query.grad is None or not torch.isfinite(query.grad).all():
            raise ValueError('represented backward has no finite institutional gradient')
        report = {'schema': 'scienceutopia.native-transition-continuation-result.v3', 'binding': binding,
            'training_run_ids': [t.run_id for t in trajectories[:4]], 'validation_run_ids': [t.run_id for t in trajectories[4:]],
            'model': model.provenance, 'identity_amendments': amendments,
            'backward': {'query': query.detach().tolist(), 'approximate_loss': float(value.detach()),
                'gradient': query.grad.tolist(), 'predicted_states': states.detach().tolist(), 'support': support},
            'validation': [model.validate_heldout(t) for t in trajectories[4:]],
            'directional_fidelity': heldout_directional_check(model, trajectories[4], trajectories[5]),
            'full_native_world_autograd': False, 'researcher_model_weights_trained': False}
        write_json_atomic(args.output / 'representation-result.json', report, sort_keys=True, allow_nan=False)
        if plan['evaluate_proposal']:
            if (upstream / 'representation-result.json').exists() or (upstream / 'completion.json').exists():
                raise ValueError('original driver reached analysis/proposal; refuse duplicate native proposal budget')
            schedules = torch.tensor([t.controls for t in trajectories[:4]], dtype=torch.float64)
            vertex = int((schedules * query.grad.detach()).sum(dim=(1, 2)).argmin())
            controls = (.5 * query.detach() + .5 * schedules[vertex]).flatten().tolist()
            prediction, _, proposal_support = model.evaluate(torch.tensor(trajectories[0].states[0], dtype=torch.float64), torch.tensor(controls, dtype=torch.float64).reshape(3, 1))
            spec = clone(baseline_record['suggestion']['candidate'])
            next(n for n in spec['mechanisms'] if n['mechanism_id'] == 'world.selection')['parameters']['annual_rates'] = controls
            system = SystemSpec.from_dict(spec)
            factory = LocalQwenNativeFactory(args.output / 'runs', args.data_cache, years=3, corpus_years=4,
                experiment_binding={'protocol': 'native-transition-autograd-v3', 'loss_spec': loss}, record_wire=True,
                record_code=True, inference_lock=args.inference_lock)
            if any(getattr(factory, key) != world[key] for key in ('model', 'model_digest', 'corpus_sha256', 'runtime_seed_binding')):
                raise ValueError('proposal source/model/corpus/startup runtime differs from declared native data')
            campaign = NativeDesignCampaign(args.output / 'proposal/campaign', initial_system=system,
                loss_spec=loss, seeds=[plan['seed']], world_binding={**world, 'source_commit': commit,
                    'origin': 'gradient-proposal-from-native-calibrated-representation', 'continuation_binding_sha256': sha(binding)})
            write_json_atomic(args.output / 'progress.json', {'status': 'fresh-native-gradient-proposal-running',
                'complete_calibration_cells': 6, 'proposal_controls': controls}, allow_nan=False)
            if not campaign.state['records']:
                campaign.advance(simulation_factory=factory)
            actual, proof = extract_trajectory(campaign.state['records'][0], run_directory=args.output / 'runs',
                source_commit=commit, model_digest=world['model_digest'], corpus_sha256=world['corpus_sha256'], controls=controls, loss_spec=loss)
            if proof['initial_physical_state_sha256'] != evidence[0]['initial_physical_state_sha256']:
                raise ValueError('gradient-proposal initial physical/RNG state differs')
            report['gradient_proposal'] = {'controls': controls, 'selected_vertex': vertex,
                'predicted_loss': float(prediction.detach()), 'actual_native_loss': actual.declared_terminal_loss,
                'support': proposal_support, 'trajectory': asdict(actual), 'native_evidence': proof,
                'comparison_scope': 'same native execution-only source, different analysis commit; engineering objective, not scientific quality'}
            write_json_atomic(args.output / 'representation-result.json', report, sort_keys=True, allow_nan=False)
        completion = {'status': 'complete', 'native_calibration_worlds': 6,
            'new_native_proposals': int(plan['evaluate_proposal']), 'gradient': query.grad.tolist(),
            'exact_full_native_autograd': False, 'binding_sha256': sha(binding)}
        # Reopen actual checkpoints and independently refit/check the represented
        # derivative, without relying on this driver's serialized gradient.
        from scripts.audit_native_transition_v3 import audit_transition
        from scripts.audit_native_design_loop import audit
        from scripts.audit_native_feedback_v2 import wire_summary
        independent = {'calibration': audit_transition(upstream, loss)}
        checked_gradient = independent['calibration'].get('representation', {}).get('backward_gradient')
        if checked_gradient is None or sha(checked_gradient) != sha(report['backward']['gradient']):
            raise ValueError('independent represented backward verification failed')
        if plan['evaluate_proposal']:
            checked = audit(args.output / 'proposal', loss, 3, require_completion=False, native_run_directory=args.output / 'runs')
            for row in checked['rows']:
                for run in row['runs']:
                    run['wire'] = wire_summary(args.output / 'runs' / run['run_id'], needle='not-a-context-probe', required=True)
            if checked['rows'][0]['loss'] != report['gradient_proposal']['actual_native_loss']:
                raise ValueError('independent fresh native proposal loss differs')
            independent['fresh_native_proposal'] = checked
        write_json_atomic(args.output / 'independent-audit.json', independent, sort_keys=True, allow_nan=False)
        write_json_atomic(args.output / 'completion.json', completion, sort_keys=True, allow_nan=False)
        write_json_atomic(args.output / 'progress.json', completion, sort_keys=True, allow_nan=False)
        print(json.dumps(completion), flush=True)
    except Exception as error:
        write_json_atomic(args.output / 'analysis-failure.json', {'type': type(error).__name__, 'error': str(error),
            'native_data_preserved': True, 'loss_fabricated': False, 'binding_sha256': sha(binding)}, sort_keys=True, allow_nan=False)
        write_json_atomic(args.output / 'progress.json', {'status': 'analysis-or-proposal-failed', 'error_type': type(error).__name__,
            'native_calibration_worlds': 6, 'see': 'analysis-failure.json'}, allow_nan=False)
        raise


if __name__ == '__main__':
    main()
