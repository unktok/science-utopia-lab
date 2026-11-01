#!/usr/bin/env python3
"""Audit existing six calibration worlds and proposal; never call inference.

The failed original receipt is retained. A new, separate output directory
records independent recovery; a byte manifest proves archived outputs unchanged.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def recover(continuation):
    from scripts.audit_native_transition_v3 import audit_transition
    from scripts.audit_native_design_loop import audit
    from scripts.audit_native_feedback_v2 import wire_summary
    from utopia.optimization.native_transition_data import extract_trajectory
    from utopia.system.code_mechanisms import sha
    from utopia.utils.data_utils import file_sha256
    continuation = Path(continuation).resolve()
    plan = json.loads((continuation / 'plan.json').read_text())
    upstream = Path(plan['upstream']).resolve()
    def manifest():
        return {str(p): file_sha256(p) for root in (upstream, continuation)
                for p in sorted(root.rglob('*')) if p.is_file()}
    before = manifest()
    loss = plan['loss_spec']
    upstream_plan = json.loads((upstream / 'plan.json').read_text())
    if sha(upstream_plan) != plan['upstream_plan_sha256']:
        raise ValueError('upstream plan differs from continuation binding')
    report = json.loads((continuation / 'representation-result.json').read_text())
    if report['binding'] != plan:
        raise ValueError('representation continuation binding differs')
    calibration = audit_transition(upstream, loss)
    if calibration['pending_cells'] or 'analysis_error' in calibration:
        raise ValueError('calibration incomplete or independent refit failed')
    if sha(calibration['representation']['backward_gradient']) != sha(report['backward']['gradient']):
        raise ValueError('independently refitted gradient differs')
    if calibration['directional_fidelity'] != report['directional_fidelity']:
        raise ValueError('independently refitted native secant check differs')
    proposed = report['gradient_proposal']
    saved = json.loads((continuation / 'proposal/campaign/native-design-state.json').read_text())
    if saved['pending'] is not None or len(saved['records']) != 1:
        raise ValueError('exactly one terminal proposal required')
    actual, proof = extract_trajectory(saved['records'][0], run_directory=continuation / 'runs',
        source_commit=plan['analysis_and_proposal_source_commit'],
        model_digest=upstream_plan['world']['model_digest'],
        corpus_sha256=upstream_plan['world']['corpus_sha256'], controls=proposed['controls'], loss_spec=loss)
    if sha(asdict(actual)) != sha(proposed['trajectory']) or proof != proposed['native_evidence']:
        raise ValueError('proposal extraction differs from preserved checkpoint evidence')
    checked = audit(continuation / 'proposal', loss, 3, require_completion=False,
                    native_run_directory=continuation / 'runs')
    for row in checked['rows']:
        for run in row['runs']:
            run['wire'] = wire_summary(continuation / 'runs' / run['run_id'], needle='not-a-context-probe', required=True)
    if checked['rows'][0]['loss'] != proposed['actual_native_loss']:
        raise ValueError('fresh proposal native loss differs')
    if before != manifest():
        raise ValueError('read-only recovery changed archived outputs')
    best = min(c['actual_loss'] for c in calibration['cells'][:4])
    return {'schema': 'scienceutopia.native-transition-audit-recovery.v4',
        'status': 'existing-native-data-representation-and-proposal-independently-audited',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'auditor_source_sha256': {name: file_sha256(ROOT / name) for name in (
            'scripts/recover_native_transition_v3_audit.py', 'scripts/audit_native_transition_v3.py',
            'scripts/audit_native_design_loop.py', 'scripts/audit_native_feedback_v2.py',
            'utopia/optimization/native_transition_data.py', 'utopia/optimization/native_transition_autograd.py')},
        'original_failure': json.loads((continuation / 'analysis-failure.json').read_text()),
        'raw_output_manifest_sha256': sha(before), 'raw_output_files': len(before),
        'raw_outputs_unchanged': True, 'new_native_executions': 0, 'new_inference_calls': 0,
        'calibration': calibration, 'fresh_native_proposal': checked,
        'summary': {'training_losses': [c['actual_loss'] for c in calibration['cells'][:4]],
            'validation_losses': [c['actual_loss'] for c in calibration['cells'][4:]],
            'represented_gradient': report['backward']['gradient'],
            'directional_fidelity': report['directional_fidelity'],
            'proposal_controls': proposed['controls'], 'proposal_loss': proposed['actual_native_loss'],
            'training_best_loss': best, 'strictly_better_than_training_best': proposed['actual_native_loss'] < best,
            'full_native_pathwise_autograd': False, 'scientific_quality_improvement_established': False}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--continuation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    upstream = Path(json.loads((args.continuation / 'plan.json').read_text())['upstream']).resolve()
    if output.is_relative_to(args.continuation.resolve()) or output.is_relative_to(upstream):
        parser.error('recovery output must be outside both preserved evidence roots')
    if output.exists():
        parser.error('fresh recovery output required; existing receipts are not overwritten')
    result = recover(args.continuation)
    from utopia.utils.data_utils import write_json_atomic
    write_json_atomic(output, result, sort_keys=True, allow_nan=False)
    print(json.dumps(result['summary'], allow_nan=False))


if __name__ == '__main__':
    main()
