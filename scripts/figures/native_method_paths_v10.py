#!/usr/bin/env python3
"""Render audited v10 method paths; never execute a model, operator or world."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

import matplotlib.pyplot as plt
plt.rcParams['svg.hashsalt'] = 'scienceutopia-native-method-paths-v10'

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-method-paths-audit.v10'
ACTUAL = 'actual-native-qwen-method-paths-development-v10'
FIXTURE = 'scripted-fixture-not-native-results'


def read_report(path, expected_source=None, *, allow_synthetic=False):
    report = json.loads(Path(path).read_text())
    if report.get('content_sha256') != digest({k: v for k, v in report.items() if k != 'content_sha256'}):
        raise ValueError('audit is not content-hash bound')
    classification = report.get('classification')
    if (report.get('schema') != SCHEMA or classification not in (ACTUAL, FIXTURE)
            or report.get('status') != 'complete'
            or report.get('technical_validity', {}).get('completed_worlds') != 6
            or report.get('technical_validity', {}).get('failures')
            or expected_source is not None and report.get('source_commit') != expected_source):
        raise ValueError('figure requires one complete source-bound actual v10 audit')
    if classification == FIXTURE:
        if not allow_synthetic or Path(path).resolve().parent != Path(tempfile.gettempdir()).resolve() and not Path(path).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()):
            raise ValueError('synthetic figure fixtures require an explicit temporary-only flag')
    elif (allow_synthetic or expected_source is None
            or report.get('source_proof', {}).get(
                'current_method_and_scientific_sources_match_experiment_commit') is not True
            or report.get('claims', {}).get('actual_fixed_weight_Qwen') is not True
            or report['claims'].get('optimizer_superiority') is not False
            or report.get('objective', {}).get('loss_spec', {}).get('id') !=
                'native-joint-v5-net-reviewed-utility'):
        raise ValueError('actual figure requires exact audit source/objective/claim proof')
    if (report.get('comparison', {}).get('equal_fresh_native_attempt_budget') != 3
            or report['comparison'].get('optimizer_superiority_claim') is not False
            or report['comparison'].get('oracle_capabilities_equal') is not False
            or report.get('held_out_metrics', {}).get('status') != 'not-measured'):
        raise ValueError('method comparison scope/budget differs')
    for arm in ('gradient', 'blackbox'):
        value = report.get('arms', {}).get(arm, {})
        if len(value.get('current_path', [])) != 3 or len(value.get('incumbent_path', [])) != 3:
            raise ValueError('all path points including no-op/worse outcomes are required')
    return report


def create(source, output, expected_source=None, *, allow_synthetic=False):
    report = read_report(source, expected_source, allow_synthetic=allow_synthetic)
    output = Path(output)
    raw_root = Path(report.get('raw_output_root', '/nonexistent-v10-raw-root')).resolve()
    targets = (output.with_suffix('.png'), output.with_suffix('.svg'), output.with_suffix('.manifest.json'))
    if (any(path.resolve().is_relative_to(raw_root) for path in targets)
            or any(path.resolve() == Path(source).resolve() for path in targets)):
        raise ValueError('figure outputs must not overwrite audit or immutable raw evidence')
    if allow_synthetic and not Path(output).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise ValueError('synthetic figure output must remain in the system temporary directory')
    colors = {'gradient': '#00a7a5', 'blackbox': '#d97706'}
    offsets = {'gradient': -.025, 'blackbox': .025}
    markers = {'gradient': 'o', 'blackbox': 's'}
    fig, axes = plt.subplots(2, 1, figsize=(5.5, 4.8), sharex=True,
                             gridspec_kw={'height_ratios': [1, 1.15]})
    for arm in ('gradient', 'blackbox'):
        path = report['arms'][arm]['current_path']
        x = [(row['step']+1 if 'step' in row else i+1)+offsets[arm]
             for i, row in enumerate(path)]
        theta = [row['theta'] for row in path]
        losses = [row['loss'] for row in path]
        incumbent = [row['loss'] for row in report['arms'][arm]['incumbent_path']]
        axes[0].plot(x, theta, marker=markers[arm], linewidth=2, label=arm, color=colors[arm])
        axes[1].plot(x, losses, marker=markers[arm], linewidth=1.7,
                     label=f'{arm} observed', color=colors[arm])
        axes[1].plot(x, incumbent, linestyle='--', linewidth=1.4,
                     label=f'{arm} incumbent', color=colors[arm], alpha=.8)
    historical = report['shared_historical']['rows']
    axes[0].axhline(.5, color='#64748b', linestyle=':', linewidth=1, label='initial current 0.5')
    axes[1].axhline(historical[1]['native_loss'], color='#64748b', linestyle=':', linewidth=1,
                    label='shared center loss')
    axes[1].axhline(min(row['native_loss'] for row in historical), color='#334155', linestyle='-.', linewidth=1,
                    label='shared historical best')
    axes[0].set_ylabel('Institution θ')
    axes[1].set_ylabel('Native loss L')
    axes[1].set_xlabel('fresh native evaluation per arm')
    axes[0].set_ylim(.17, .83)
    axes[1].set_xlim(.88, 3.12)
    axes[1].set_xticks([1, 2, 3], labels=['1', '2', '3'])
    for axis in axes:
        axis.grid(alpha=.2)
        axis.legend(fontsize=6.5, ncol=2)
    fig.suptitle('Equal-budget native method paths\nactual common-prefix-coupled development; not held-out or optimality', fontsize=10)
    fig.text(.5, .008, 'Equal native attempts; gradient uses raw review traces, blackbox uses scalar loss only.',
             ha='center', fontsize=6.7, color='#334155')
    if report['classification'] == FIXTURE:
        fig.text(.5, .5, 'SYNTHETIC FIXTURE — NOT ACTUAL QWEN', ha='center', va='center',
                 rotation=25, fontsize=14, color='#dc2626', alpha=.22, weight='bold')
    fig.tight_layout(rect=(0, .035, 1, .96))
    output.parent.mkdir(parents=True, exist_ok=True)
    png, svg = output.with_suffix('.png'), output.with_suffix('.svg')
    fig.savefig(png, dpi=180, bbox_inches='tight', metadata={'Software': 'Science Utopia Lab'})
    fig.savefig(svg, bbox_inches='tight', metadata={'Date': None})
    plt.close(fig)
    result = {'schema': SCHEMA+'.figure', 'audit_file_sha256': file_sha256(source),
        'audit_content_sha256': report['content_sha256'], 'source_commit': report['source_commit'],
        'outputs': {'png': {'path': str(png), 'sha256': file_sha256(png)},
                    'svg': {'path': str(svg), 'sha256': file_sha256(svg)}},
        'new_model_calls': 0, 'new_native_worlds': 0,
        'classification': report['classification'],
        'optimizer_superiority_claim': False, 'held_out_claim': False}
    result['content_sha256'] = digest(result)
    write_json_atomic(output.with_suffix('.manifest.json'), result, sort_keys=True, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    args = parser.parse_args()
    print(json.dumps(create(args.audit, args.output, args.expected_source), sort_keys=True))


if __name__ == '__main__':
    main()
