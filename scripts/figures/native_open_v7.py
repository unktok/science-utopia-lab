"""Two-panel scientific figure from independently audited v7 native facts only."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from scripts.analyze_native_open_v7 import SCHEMA, ACTUAL, FIXTURE
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic


def figure_data(report):
    if (report.get('schema') != SCHEMA or report.get('classification') not in {ACTUAL, FIXTURE}
            or 'audit' not in report or report['audit'].get('new_model_calls') != 0
            or report['content_sha256'] != digest({k: v for k, v in report.items() if k != 'content_sha256'})):
        raise ValueError('hash-bound independently audited native v7 report required')
    data = []
    for index, row in enumerate(report['observations']):
        obs, draw = row['observation'], row['draw']
        complete = obs is not None and obs['status'] == 'complete'
        if complete:
            if not (type(obs['loss']) in (int, float) and math.isfinite(obs['loss'])):
                raise ValueError('complete native loss must be finite')
            metrics = row['independent_metrics']
            a = metrics['native.accepted_decisions']['value']
            c = metrics['native.institutional_context_deliveries']['value']
            if not math.isclose(obs['loss'], -a-.1*c, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError('plotted loss differs from independently reconstructed native counts')
            spec = SystemSpec.from_dict(draw['suggestion']['candidate'])
            if spec.fingerprint != obs['metadata']['system_fingerprint']:
                raise ValueError('plotted actual structure differs from native design identity')
        else:
            if obs is not None and obs['loss'] is not None:
                raise ValueError('failed world cannot be assigned a numerical plotting penalty')
            a = c = None
            spec = SystemSpec.from_dict(draw['suggestion']['candidate']) if draw['suggestion'] else None
        number = sum(r['generation'] == row['generation'] for r in report['observations'][:index])
        data.append({'label': f"G{row['generation']+1}{chr(97+number)}", 'generation': row['generation'],
            'status': 'complete' if complete else 'technical-failure', 'loss': obs['loss'] if obs else None,
            'accepted_decisions': a, 'contexts_delivered': c,
            'custom_artifacts': row['native_counts']['custom_artifacts'] if complete else None,
            'process_invocations': row['native_counts']['process_invocations'] if complete else None,
            'custom_actors': row['native_counts']['custom_actors'] if complete else None,
            'continuous': {operation['path']: operation['value'] for operation in draw['continuous_operations']},
            'structural_assignment': draw['assignment'], 'latent': draw['latent'],
            'nodes': len(spec.mechanisms) if spec else None, 'edges': len(spec.connections) if spec else None,
            'system_fingerprint': spec.fingerprint if spec else None})
    if report['audit']['loss_path'] != [r['loss'] for r in data]:
        raise ValueError('plotting path differs from independent audit')
    return data


def create(report, output):
    output = Path(output)
    if report['classification'] == FIXTURE and 'paper' in output.parts and 'figures' in output.parts:
        raise ValueError('scripted QA cannot be published as a paper native result')
    data = figure_data(report)
    if not data:
        raise ValueError('no observed native draw to plot; pending authoring is not a result')
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
        'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42, 'ps.fonttype': 42})
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.65), gridspec_kw={'width_ratios': [1, 1.2]})
    colors = ['#27679D', '#BC6539']
    x = np.arange(len(data))
    for i, row in enumerate(data):
        color = colors[row['generation'] % len(colors)]
        if row['status'] == 'complete':
            axes[0].scatter(i, row['loss'], s=83, c=color, edgecolor='white', linewidth=.7, zorder=4)
            axes[0].annotate(f"{row['loss']:g}", (i, row['loss']), xytext=(0, 10),
                textcoords='offset points', ha='center', color=color, weight='bold')
        else:
            axes[0].text(i, .05, 'technical\nfailure\n(loss null)', transform=axes[0].get_xaxis_transform(),
                ha='center', va='bottom', color='#8A3548', fontsize=8)
    for generation in sorted({d['generation'] for d in data}):
        ids = [i for i, d in enumerate(data) if d['generation'] == generation and d['status'] == 'complete']
        if len(ids) == 2:
            mean = sum(data[i]['loss'] for i in ids)/2
            axes[0].hlines(mean, min(ids)-.22, max(ids)+.22, color=colors[generation % 2], alpha=.5, linewidth=1.1)
    labels = []
    for row in data:
        coordinates = list(row['continuous'].items())
        continuous = (f"{coordinates[0][0].rsplit('/',1)[-1]} {coordinates[0][1]:+.2f}"
            if len(coordinates) == 1 else f"{len(coordinates)} coordinates")
        factor = ', '.join(f'{k}={v}' for k, v in row['structural_assignment'].items())
        # Full unabridged paths/choices are preserved in the figure manifest.
        if len(factor) > 22:
            factor = factor[:19] + '...'
        labels.append(f"{row['label']}\n{continuous}\n{factor}")
    axes[0].set_xticks(x, labels, fontsize=7.4)
    axes[0].set_xlim(-.6, len(data)-.4)
    axes[0].set_ylabel('Actual native loss  L = -A - 0.1C  (lower is better)')
    axes[0].set_title('A  Objective-conditioned native draws', loc='left', fontsize=11, pad=16)
    axes[0].grid(axis='y', alpha=.18)
    axes[0].margins(y=.23)
    width = .19
    categories = [('accepted_decisions', 'Accepted decisions A', '#27679D'),
        ('contexts_delivered', 'Delivered contexts C', '#319083'),
        ('custom_artifacts', 'Custom artifacts', '#BA743A'),
        ('process_invocations', 'Process invocations', '#8794A6')]
    for j, (key, name, color) in enumerate(categories):
        for i, row in enumerate(data):
            if row[key] is not None:
                axes[1].bar(i+(j-1.5)*width, row[key], width=width, color=color,
                    label=name if i == next((n for n, d in enumerate(data) if d[key] is not None), -1) else None)
    axes[1].set_xticks(x, [d['label'] for d in data])
    axes[1].set_ylim(bottom=0)
    axes[1].set_ylabel('Counts from completed native checkpoints')
    axes[1].set_title('B  Committed institutional activity', loc='left', fontsize=11, pad=16)
    axes[1].grid(axis='y', alpha=.18)
    axes[1].set_axisbelow(True)
    axes[1].legend(loc='upper left', bbox_to_anchor=(0, 1.01), ncol=2, fontsize=7.6,
        frameon=False, handlelength=1.2, columnspacing=1.2)
    axes[1].margins(y=.26)
    title = 'Open institutional design in the original researcher world'
    if report['classification'] == FIXTURE:
        title = 'SCRIPTED SOFTWARE QA - NOT NATIVE QWEN FINDINGS'
    fig.suptitle(title, fontsize=13, x=.06, ha='left', y=.97)
    fig.text(.06, .035, 'Two IID designs per generation; blue G1, orange G2. Thin lines: observed batch means, not improvement estimates.\n'
        'One development seed. Engineering count proxy; no held-out, causal, scientific-quality, or full-world autograd claim.', fontsize=8, color='#525E6A')
    fig.subplots_adjust(left=.075, right=.985, bottom=.25, top=.79, wspace=.32)
    paths = {kind: output.with_suffix('.'+kind) for kind in ('pdf', 'png', 'svg')}
    for kind, path in paths.items():
        fig.savefig(path, dpi=210 if kind == 'png' else None, facecolor='white')
    plt.close(fig)
    manifest = {'schema': 'scienceutopia.native-open-figure.v7', 'classification': report['classification'],
        'report_content_sha256': report['content_sha256'], 'source_commit': report['source_commit'],
        'raw_inventory_sha256': report['audit']['raw_inventory_sha256'], 'plotted_native_facts': data,
        'outputs': {k: {'path': str(p), 'sha256': file_sha256(p)} for k, p in paths.items()},
        'claims': report['claims'], 'new_model_calls': 0, 'new_container_executions': 0}
    write_json_atomic(output.with_suffix('.manifest.json'), manifest, sort_keys=True, allow_nan=False)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    create(json.loads(args.report.read_text()), args.output)


if __name__ == '__main__':
    main()
