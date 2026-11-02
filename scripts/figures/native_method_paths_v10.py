#!/usr/bin/env python3
"""Render audited v10 method paths; never execute a model, operator or world."""
import argparse
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
plt.rcParams['svg.hashsalt'] = 'scienceutopia-native-method-paths-v10'

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-method-paths-audit.v10'
ACTUAL = 'actual-native-qwen-method-paths-development-v10'


def read_report(path, expected_source=None):
    report = json.loads(Path(path).read_text())
    if report.get('content_sha256') != digest({k: v for k, v in report.items() if k != 'content_sha256'}):
        raise ValueError('audit is not content-hash bound')
    if (report.get('schema') != SCHEMA or report.get('classification') != ACTUAL
            or report.get('status') != 'complete'
            or report.get('technical_validity', {}).get('completed_worlds') != 6
            or report.get('technical_validity', {}).get('failures')
            or expected_source is not None and report.get('source_commit') != expected_source):
        raise ValueError('figure requires one complete source-bound actual v10 audit')
    if (report.get('comparison', {}).get('equal_fresh_native_attempt_budget') != 3
            or report['comparison'].get('optimizer_superiority_claim') is not False
            or report.get('held_out_metrics', {}).get('status') != 'not-measured'):
        raise ValueError('method comparison scope/budget differs')
    for arm in ('gradient', 'blackbox'):
        value = report.get('arms', {}).get(arm, {})
        if len(value.get('current_path', [])) != 3 or len(value.get('incumbent_path', [])) != 3:
            raise ValueError('all path points including no-op/worse outcomes are required')
    return report


def create(source, output, expected_source=None):
    report = read_report(source, expected_source)
    colors = {'gradient': '#00a7a5', 'blackbox': '#d97706'}
    fig, axes = plt.subplots(2, 1, figsize=(6.7, 5.2), sharex=True,
                             gridspec_kw={'height_ratios': [1, 1.15]})
    for arm in ('gradient', 'blackbox'):
        path = report['arms'][arm]['current_path']
        x = [row['step']+1 if 'step' in row else i+1 for i, row in enumerate(path)]
        theta = [row['theta'] for row in path]
        losses = [row['loss'] for row in path]
        incumbent = [row['loss'] for row in report['arms'][arm]['incumbent_path']]
        axes[0].plot(x, theta, marker='o', linewidth=2, label=arm, color=colors[arm])
        axes[1].plot(x, losses, marker='o', linewidth=1.7, label=f'{arm} observed', color=colors[arm])
        axes[1].plot(x, incumbent, linestyle='--', linewidth=1.4,
                     label=f'{arm} incumbent', color=colors[arm], alpha=.8)
    historical = report['shared_historical']['rows']
    axes[0].axhline(.5, color='#64748b', linestyle=':', linewidth=1, label='initial current 0.5')
    axes[1].axhline(historical[1]['native_loss'], color='#64748b', linestyle=':', linewidth=1,
                    label='shared center loss')
    axes[1].axhline(min(row['native_loss'] for row in historical), color='#334155', linestyle='-.', linewidth=1,
                    label='shared historical best')
    axes[0].set_ylabel('institution coordinate θ')
    axes[1].set_ylabel('fixed native loss (lower better)')
    axes[1].set_xlabel('fresh native evaluation per arm')
    axes[0].set_ylim(.17, .83)
    axes[0].set_xticks([1, 2, 3])
    for axis in axes:
        axis.grid(alpha=.2)
        axis.legend(fontsize=7.5, ncol=2)
    fig.suptitle('Equal-budget native method paths\nactual common-prefix-coupled development; not held-out or optimality', fontsize=10)
    fig.tight_layout()
    output = Path(output)
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
        'optimizer_superiority_claim': False, 'held_out_claim': False}
    result['content_sha256'] = digest(result)
    write_json_atomic(output.with_suffix('.manifest.json'), result, sort_keys=True, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-source')
    args = parser.parse_args()
    print(json.dumps(create(args.audit, args.output, args.expected_source), sort_keys=True))


if __name__ == '__main__':
    main()
