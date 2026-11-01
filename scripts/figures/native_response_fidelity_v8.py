#!/usr/bin/env python3
"""Plot the labelled scripted original-world response-boundary QA, never Qwen data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from utopia.utils.data_utils import file_sha256, write_json_atomic
from utopia.system.design_patch import digest


def create(report_path, output):
    report_path, output = Path(report_path), Path(output)
    data = json.loads(report_path.read_text())
    if data.get('content_sha256') != digest({k: v for k, v in data.items() if k != 'content_sha256'}):
        raise ValueError('report must be hash-bound')
    if (data['classification'] != 'scripted-fixture-not-native-results'
            or data['full_native_world_autograd'] is not False
            or data['native_LLM_Jacobian_verified'] is not False
            or data['new_live_Qwen_calls'] != 0):
        raise ValueError('requires explicitly scoped scripted response-boundary evidence')
    endpoints = data['endpoints']
    if len(endpoints) != 7 or len(data['unused_endpoint_checks']) != 2:
        raise ValueError('requires complete seven-world QA and two unused checks')
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.5,
        'pdf.fonttype': 42, 'ps.fonttype': 42})
    fig, (left, right) = plt.subplots(1, 2, figsize=(5.5, 3.55),
                                    gridspec_kw={'width_ratios': [1.2, 1]})
    fig.subplots_adjust(left=.14, right=.95, top=.78, bottom=.32, wspace=.48)
    blue, orange, green = '#2878B5', '#D56A36', '#2C8B75'
    for indexes, label, color, marker in (
            ([0, 1, 2], 'Calibration', blue, 'o'),
            ([3, 4], 'Unused endpoints', orange, 's'),
            ([5], 'Projected; ties center', green, '^'),
            ([6], 'Outside support; unsupported', '#6C7882', 'x')):
        left.scatter([endpoints[i]['coordinate_values']['advice'] for i in indexes],
                     [endpoints[i]['native_loss'] for i in indexes],
                     label=label, color=color, marker=marker, s=32, zorder=3)
    left.axvspan(-.25, .25, color=blue, alpha=.065)
    left.set(xlabel='Institution control $\\theta$', ylabel='Actual native loss',
             xticks=[-.25, 0, .25, .6], yticks=[-120, -96, -72], ylim=(-125, -66))
    left.set_title('(a) Native forward; scripted replies', loc='left', fontsize=8.8, pad=11)
    left.legend(loc='lower left', bbox_to_anchor=(-.07, -.57), ncol=2,
                fontsize=7.1, frameon=False, columnspacing=.6, handletextpad=.3)
    path = data['native_finite_path']
    errors = [path['frozen_boundary_native_error'], path['response_aware_native_error']]
    right.barh([1, 0], errors, color=[orange, green], height=.42)
    right.set_xscale('log')
    right.set(xlim=(1e-6, 1e3), yticks=[1, 0],
              yticklabels=['Frozen\nresponse', 'Response-\naware'],
              xlabel='Absolute finite-change error')
    right.set_xticks([1e-6, 1e-4, 1e-2, 1, 100])
    right.set_title('(b) Unused $\\Delta L=-24$', loc='left', fontsize=8.8, pad=11)
    for y, error in zip([1, 0], errors):
        right.text(error*1.4, y, f'{error:.3g}', va='center', fontsize=8.5)
    for ax in (left, right):
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='x', alpha=.14)
        ax.set_axisbelow(True)
    fig.text(.035, .965, 'Response-aware native QA: scripted only',
             fontsize=11, weight='bold', va='top')
    fig.text(.035, .88, '7 original six-year worlds · 0 Qwen calls · no native/LLM Jacobian',
             fontsize=8.2, color='#53616D')
    fig.text(.985, .025, 'Finite-path agreement is not a point-gradient proof or institutional improvement.',
             fontsize=8.2, color='#8A4253', ha='right')
    paths = {kind: output.with_suffix('.'+kind) for kind in ('pdf', 'png', 'svg')}
    for kind, path_out in paths.items():
        fig.savefig(path_out, dpi=210 if kind == 'png' else None, facecolor='white')
        if kind == 'svg':
            path_out.write_text('\n'.join(line.rstrip() for line in path_out.read_text().splitlines())+'\n')
    plt.close(fig)
    receipt = {'schema': 'scienceutopia.native-response-fidelity-figure.v8',
        'classification': data['classification'], 'report_sha256': file_sha256(report_path),
        'native_source_commit': data['source_commit'], 'new_model_calls': 0,
        'new_native_worlds': 0, 'native_jacobian_claim': False,
        'outputs': {kind: {'path': str(path), 'sha256': file_sha256(path)}
                    for kind, path in paths.items()}}
    write_json_atomic(output.with_suffix('.manifest.json'), receipt, sort_keys=True, allow_nan=False)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    create(args.report, args.output)
