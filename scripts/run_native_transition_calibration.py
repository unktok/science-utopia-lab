#!/usr/bin/env python3
"""Actual native annual interventions -> composed differentiable representation.

Original research/LLM execution is opaque and unchanged. Gradients are of a
calibrated local representation, independently checked on unused native designs.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import torch
    from utopia.optimization.loss import load_loss_spec
    from utopia.optimization.native_design import NativeDesignCampaign
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.optimization.native_transition_autograd import NativeTransitionSurrogate, heldout_directional_check
    from utopia.optimization.native_transition_data import extract_trajectory, compile_terminal_loss, FEATURE_SCHEMA
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_kernel import legacy_world_system
    from utopia.system.native_selection_slot import selection_source_slot
    from utopia.utils.data_utils import write_json_atomic
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--loss', type=Path, required=True)
    parser.add_argument('--evaluate-proposal', action='store_true', help='fresh native evaluation of one support-preserving gradient proposal')
    parser.add_argument('--through-cell', type=int, default=6, help='bounded execution batch; resume the same frozen plan through this calibration cell')
    parser.add_argument('--inference-lock', type=Path, help='shared lab inference mutex; actual native pipelines can overlap')
    args = parser.parse_args()
    if not 1 <= args.through_cell <= 6:
        parser.error('--through-cell must be 1..6')
    args.output.mkdir(parents=True, exist_ok=True)
    loss_spec = load_loss_spec(args.loss)
    tensor_loss = compile_terminal_loss(loss_spec)
    factory = LocalQwenNativeFactory(args.output / 'runs', args.data_cache, years=3, corpus_years=4,
        experiment_binding={'protocol': 'native-transition-autograd-v3', 'loss_spec': loss_spec}, record_wire=True, record_code=True,
        inference_lock=args.inference_lock)
    if factory.runtime_seed_binding['python_hash_seed_environment'] != '42':
        parser.error('launch the native calibration process with PYTHONHASHSEED=42; a simulation RNG seed alone does not pin Python set ordering')
    executor = DockerCodeExecutor()
    cells = [('baseline', [.2, .2, .2]), ('pulse-1', [.8, .2, .2]),
        ('pulse-2', [.2, .8, .2]), ('pulse-3', [.2, .2, .8]),
        ('validation-minus', [.275] * 3), ('validation-plus', [.375] * 3)]
    world = {'source_commit': factory.source_commit, 'model': factory.model, 'model_digest': factory.model_digest,
        'corpus_sha256': factory.corpus_sha256, 'dataset_identity': factory.dataset_identity,
        'years': 3, 'corpus_years': 4, 'population': 'five-independent-balanced-researchers',
        'feature_schema': FEATURE_SCHEMA, 'protocol': 'native-transition-autograd-v3'}
    world['runtime_seed_binding'] = factory.runtime_seed_binding
    world['lab_inference_serialized'] = bool(args.inference_lock)
    plan = {'schema': 'scienceutopia.native-transition-plan.v1', 'world': world, 'seed': 1301,
        'cells': cells, 'evaluate_proposal': args.evaluate_proposal, 'loss_spec': loss_spec,
        'gradient_query': [[.325]] * 3, 'proposal_convex_step': .5,
        'scope': 'native-calibrated annual feature-transition representation; not exact native-world autograd'}
    plan_path = args.output / 'plan.json'
    if plan_path.exists() and json.loads(plan_path.read_text()) != json.loads(json.dumps(plan)):
        raise ValueError('frozen native transition plan changed')
    write_json_atomic(plan_path, plan, sort_keys=True, allow_nan=False)
    trajectories, evidence = [], []
    started = time.monotonic()

    def execute(name, controls):
        system = selection_source_slot(legacy_world_system(seed=1301), image_id=executor.image_id, annual_rates=controls)
        campaign = NativeDesignCampaign(args.output / 'cells' / name / 'campaign', initial_system=system,
            loss_spec=loss_spec, seeds=[1301], world_binding={**world, 'cell': name})
        if not campaign.state['records']:
            campaign.advance(simulation_factory=factory)
        record = campaign.state['records'][0]
        trajectory, receipt = extract_trajectory(record, run_directory=args.output / 'runs',
            source_commit=factory.source_commit, model_digest=factory.model_digest, corpus_sha256=factory.corpus_sha256,
            controls=controls, loss_spec=loss_spec)
        write_json_atomic(args.output / 'cells' / name / 'trajectory.json', {'trajectory': asdict(trajectory), 'evidence': receipt}, sort_keys=True, allow_nan=False)
        print(json.dumps({'cell': name, 'status': 'actual-native-complete', 'loss': trajectory.declared_terminal_loss,
            'controls': controls, 'elapsed_seconds_this_process': time.monotonic() - started}), flush=True)
        return trajectory, receipt

    for name, controls in cells:
        trajectory, receipt = execute(name, controls)
        trajectories.append(trajectory)
        evidence.append(receipt)
        write_json_atomic(args.output / 'progress.json', {'complete_cells': len(trajectories), 'planned_cells': 6 + int(args.evaluate_proposal),
            'last_cell': name, 'status': 'running', 'actual_losses': [r.declared_terminal_loss for r in trajectories]}, allow_nan=False)
        if len(trajectories) == args.through_cell and args.through_cell < 6:
            print(json.dumps({'status': 'execution-batch-complete-analysis-pending', 'completed_cells': len(trajectories)}), flush=True)
            return
    model = NativeTransitionSurrogate.fit(trajectories[:4], tensor_loss)
    controls = torch.full((3, 1), .325, dtype=torch.float64, requires_grad=True)
    value, predicted_states, support = model.evaluate(torch.tensor(trajectories[0].states[0], dtype=torch.float64), controls)
    value.backward()
    if controls.grad is None or not torch.isfinite(controls.grad).all():
        raise ValueError('composed native representation did not produce a finite institutional gradient')
    report = {'schema': 'scienceutopia.native-transition-autograd-result.v3', 'world': world, 'plan': plan,
        'training': [asdict(r) for r in trajectories[:4]], 'validation_trajectories': [asdict(r) for r in trajectories[4:]],
        'native_evidence': evidence, 'model': model.provenance,
        'fitted_year_models': [{key: value.detach().tolist() if isinstance(value, torch.Tensor) else value
            for key, value in vars(year).items()} for year in model.years],
        'backward': {'query': controls.detach().tolist(), 'approximate_loss': float(value.detach()),
            'gradient': controls.grad.tolist(), 'predicted_states': predicted_states.detach().tolist(), 'support': support},
        'validation': [model.validate_heldout(r) for r in trajectories[4:]],
        'directional_fidelity': heldout_directional_check(model, trajectories[4], trajectories[5]),
        'full_native_world_autograd': False, 'researcher_model_weights_trained': False,
        'interpretation': 'autograd through calibrated annual native feature transitions, including empirical opaque-response effects; not exact token/native Python derivatives'}
    write_json_atomic(args.output / 'representation-result.json', report, sort_keys=True, allow_nan=False)
    if args.evaluate_proposal:
        schedules = torch.tensor([r.controls for r in trajectories[:4]], dtype=torch.float64)
        vertex = int((schedules * controls.grad.detach()).sum(dim=(1, 2)).argmin())
        proposal = (.5 * controls.detach() + .5 * schedules[vertex]).flatten().tolist()
        # The proposal remains inside the measured schedule convex hull.
        proposal_value, _, proposal_support = model.evaluate(torch.tensor(trajectories[0].states[0], dtype=torch.float64), torch.tensor(proposal, dtype=torch.float64).reshape(3, 1))
        candidate, receipt = execute('gradient-proposal', proposal)
        report['gradient_proposal'] = {'controls': proposal, 'selected_vertex': vertex,
            'predicted_loss': float(proposal_value.detach()), 'actual_native_loss': candidate.declared_terminal_loss,
            'support': proposal_support, 'trajectory': asdict(candidate), 'native_evidence': receipt,
            'comparison_scope': 'different schedule under the same engineering loss; no scientific-quality claim'}
        write_json_atomic(args.output / 'representation-result.json', report, sort_keys=True, allow_nan=False)
    write_json_atomic(args.output / 'completion.json', {'status': 'complete', 'source_commit': factory.source_commit,
        'wall_seconds_this_process': time.monotonic() - started, 'native_cells': 6 + int(args.evaluate_proposal),
        'actual_gradient': controls.grad.tolist(), 'exact_full_native_autograd': False}, sort_keys=True, allow_nan=False)
    write_json_atomic(args.output / 'progress.json', {'status': 'complete', 'complete_cells': 6 + int(args.evaluate_proposal),
        'planned_cells': 6 + int(args.evaluate_proposal)}, allow_nan=False)


if __name__ == '__main__':
    main()
