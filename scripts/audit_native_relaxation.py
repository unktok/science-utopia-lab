#!/usr/bin/env python3
"""Read-only native hard/soft probe audit, including actual-trace grad checks."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--loss', type=Path, required=True)
    args = parser.parse_args()
    import torch
    from scripts.audit_native_design_loop import audit
    from utopia.optimization.loss import load_loss_spec
    from utopia.optimization.native_relaxation import native_tensor_trace, replay_tensor_trace, trace_objective, fit_native_tensor_trace
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system.design_patch import digest
    from utopia.system.tensor_program import IMPLEMENTATION
    from utopia.utils.data_utils import file_sha256
    run = args.run.resolve()
    saved = json.loads((run / 'campaign/native-design-state.json').read_text())
    report = audit(run, load_loss_spec(args.loss), saved['binding']['world']['years'])
    record = saved['records'][0]
    first = record['observation']['metadata']['runs'][0]
    checkpoint = read_portable_checkpoint(first['checkpoint_path'])
    trace = native_tensor_trace(checkpoint['native_system']['events'])
    fit = json.loads((run / 'relaxation.json').read_text())
    if digest(trace) != fit['trace_sha256'] or file_sha256(first['checkpoint_path']) != fit['checkpoint_sha256']:
        raise ValueError('native training trace/checkpoint hash differs')
    programs = {n['mechanism_id']: n['parameters']['program'] for n in record['suggestion']['candidate']['mechanisms'] if n['implementation'] == IMPLEMENTATION}
    replay_tensor_trace(trace, programs, hard=True, verify_recorded=True)
    parameters = {name: {k: torch.tensor(v, dtype=torch.float64, requires_grad=k in ('keys', 'thresholds', 'bias')) for k, v in p['parameters'].items()} for name, p in programs.items()}
    def evaluate(): return trace_objective(replay_tensor_trace(trace, programs, parameters=parameters, temperature=fit['temperature']), fit['terms'])
    leaves = [(name, key, tensor) for name, group in parameters.items() for key, tensor in group.items() if tensor.requires_grad]
    analytic = torch.autograd.grad(evaluate(), [t for _, _, t in leaves])
    checks = []
    eps = 1e-5
    for (name, key, tensor), gradient in zip(leaves, analytic):
        for coordinate in range(tensor.numel()):
            with torch.no_grad(): tensor.reshape(-1)[coordinate] += eps
            plus = float(evaluate().detach())
            with torch.no_grad(): tensor.reshape(-1)[coordinate] -= 2 * eps
            minus = float(evaluate().detach())
            with torch.no_grad(): tensor.reshape(-1)[coordinate] += eps
            estimate = (plus - minus) / (2 * eps)
            error = abs(estimate - float(gradient.reshape(-1)[coordinate]))
            if error > 1e-5: raise ValueError('actual-native-trace finite difference mismatch')
            checks.append({'mechanism': name, 'parameter': key, 'coordinate': coordinate,
                'autograd': float(gradient.reshape(-1)[coordinate]), 'central_difference': estimate, 'absolute_error': error})
    started = time.monotonic()
    reproduced = fit_native_tensor_trace(trace, programs, trainable={'addressed-selection': ['keys', 'thresholds', 'bias']},
        terms=fit['terms'], steps=30, learning_rate=0.1, temperature=fit['temperature'])
    fit_seconds = time.monotonic() - started
    if reproduced['programs'] != fit['programs'] or reproduced['history'] != fit['history']:
        raise ValueError('recorded tensor fitting path does not reproduce')
    actual_candidate = saved['records'][1]['suggestion']['candidate']
    for node in actual_candidate['mechanisms']:
        if node['mechanism_id'] in fit['programs'] and node['parameters']['program'] != fit['programs'][node['mechanism_id']]:
            raise ValueError('native counterfactual did not install the fitted program')
    report['relaxation'] = {k: fit[k] for k in ('trace_sha256', 'temperature', 'scope', 'full_native_world_autograd', 'terms', 'conditional_hard_loss_after')}
    report['relaxation'].update(first_conditional_soft_loss=fit['history'][0]['conditional_soft_loss'],
        last_conditional_soft_loss=fit['history'][-1]['conditional_soft_loss'], actual_trace_gradient_checks=checks,
        reproduced_fit_seconds=fit_seconds, fitted_programs_sha256=digest(fit['programs']),
        full_fit_path_reproduced=True, fitted_program_installed_in_native_candidate=True)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
