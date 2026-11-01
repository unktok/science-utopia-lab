#!/usr/bin/env python3
"""Empirical v8 figure: loss paths, cross-scoring, and exact graph changes."""
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

from scripts.analyze_native_objective_structure_v8 import (
    ACTUAL, ARM_IDS, FIGURE_DATA_SCHEMA, FIXTURE, SCHEMA,
)
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic


LABELS = {ARM_IDS[0]: 'Throughput  $-A$', ARM_IDS[1]: 'Reviewed utility  $3.25A-Q+0.05R$'}
COLORS = {ARM_IDS[0]: '#2878B5', ARM_IDS[1]: '#D56A36'}


def figure_data(report):
    if (report.get('schema') != SCHEMA or report.get('classification') not in {ACTUAL, FIXTURE}
            or report.get('new_model_calls') != 0 or report.get('generated_source_executions') != 0
            or report.get('held_out_metrics') != {'status': 'not-defined-or-measured'}
            or report.get('promotion_policy') != {'status': 'not-defined-or-applied'}
            or report.get('content_sha256') != digest({k: v for k, v in report.items()
                                                        if k != 'content_sha256'})):
        raise ValueError('hash-bound independently audited v8 report required')
    if set(report.get('arms', {})) != set(ARM_IDS):
        raise ValueError('both objective arms are required')
    arms = {}
    for identity in ARM_IDS:
        arm = report['arms'][identity]
        rows = []
        for index, row in enumerate(arm['rows']):
            value = row['cross_objective_losses'][identity]
            if row['status'] == 'complete':
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError('complete row lacks a finite independently remeasured loss')
                if value != row['observation']['loss']:
                    raise ValueError('plotted bound loss differs from immutable optimization observation')
                if set(row['independent_metrics']) != {
                    'native.accepted_decisions', 'native.rejected_decisions', 'native.review_records',
                    'native.final_active_authors', 'native.final_author_resources',
                    'native.institutional_context_deliveries', 'native.accepted_unreviewed_decisions',
                    'native.accepted_peer_score_sum'}:
                    raise ValueError('all eight independently measured diagnostics are required')
            elif value is not None or row['observation'] is not None and row['observation'].get('loss') is not None:
                raise ValueError('technical failure cannot be plotted as a numerical loss')
            rows.append({'label': f"G{row['generation']+1}{chr(97+row['draw_index'])}",
                'status': row['status'], 'loss': value,
                'cross_objective_losses': row['cross_objective_losses'],
                'graph_changes': row['graph_changes'],
                'system_fingerprint': (row['physical_proof']['measurement']['system_fingerprint']
                                       if row['status'] == 'complete' else None)})
        if arm['loss_path'] != [row['loss'] for row in rows]:
            raise ValueError('plotted loss trajectory differs from audit')
        complete = [row for row in rows if row['loss'] is not None]
        best = min((row['loss'] for row in complete), default=None)
        tied = [row for row in complete if row['loss'] == best] if best is not None else []
        selection = arm['selection']
        if (selection.get('best_loss') != best or selection.get('tie_count') != len(tied)
                or selection.get('tied_system_fingerprints') != [row['system_fingerprint'] for row in tied]
                or selection.get('representative_system_fingerprint') !=
                    (tied[0]['system_fingerprint'] if tied else None)):
            raise ValueError('selected development minimum/ties differ from audited rows')
        arms[identity] = {'rows': rows, 'selection': arm['selection']}
    matrix = report['selected_cross_objective_matrix']
    if set(matrix) != set(ARM_IDS) or any(value is not None and set(value) != set(ARM_IDS)
                                          for value in matrix.values()):
        raise ValueError('selected cross-objective matrix differs')
    for identity in ARM_IDS:
        representative = next((row for row in arms[identity]['rows']
            if row['system_fingerprint'] == arms[identity]['selection']['representative_system_fingerprint']), None)
        expected = representative['cross_objective_losses'] if representative else None
        if matrix[identity] != expected:
            raise ValueError('selected cross-objective matrix differs from representative draw')
    return {'schema': FIGURE_DATA_SCHEMA, 'classification': report['classification'],
        'report_content_sha256': report['content_sha256'], 'source_commit': report['source_commit'],
        'arms': arms, 'selected_cross_objective_matrix': matrix,
        'scope': 'development engineering; same draws cross-scored; no held-out or improvement claim'}


def create(report, output):
    output = Path(output)
    data = figure_data(report)
    if data['classification'] == FIXTURE and 'paper' in output.parts and 'figures' in output.parts:
        raise ValueError('scripted fixture cannot be published as an empirical paper result')
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.4,
        'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42, 'ps.fonttype': 42})
    fig, axes = plt.subplots(1, 3, figsize=(10.3, 4.8), gridspec_kw={'width_ratios': [1.45, 1, 1.35]})

    # A: real independently reconstructed bound losses; gaps remain gaps.
    offset = {ARM_IDS[0]: -.08, ARM_IDS[1]: .08}
    for identity in ARM_IDS:
        rows = data['arms'][identity]['rows']
        for i, row in enumerate(rows):
            if row['loss'] is not None:
                axes[0].scatter(i+offset[identity], row['loss'], s=54, color=COLORS[identity],
                    edgecolor='white', linewidth=.6, label=LABELS[identity] if i == 0 else None, zorder=3)
            else:
                axes[0].scatter(i+offset[identity], 0, marker='x', s=45, color=COLORS[identity],
                    transform=axes[0].get_xaxis_transform())
    axes[0].set_xticks(range(4), ['G1a', 'G1b', 'G2a', 'G2b'])
    axes[0].set_ylabel('Bound development loss (lower is selected)')
    axes[0].set_title('A  Objective-conditioned paths', loc='left', fontsize=9.5)
    axes[0].legend(frameon=False, fontsize=7.6, loc='best')
    axes[0].grid(axis='y', alpha=.18)

    # B: raw values, not normalized scores; objectives have different units.
    matrix = data['selected_cross_objective_matrix']
    array = np.array([[matrix[row][column] if matrix[row] is not None else np.nan
                       for column in ARM_IDS] for row in ARM_IDS], dtype=float)
    shown = np.zeros_like(array)
    for column in range(2):
        values = array[:, column]
        finite = values[np.isfinite(values)]
        if len(finite):
            span = finite.max()-finite.min()
            shown[:, column] = (values-finite.min())/(span if span else 1.)
        else:
            shown[:, column] = np.nan
    image = axes[1].imshow(shown, cmap='Blues', vmin=0, vmax=1, aspect='auto')
    for i in range(2):
        for j in range(2):
            axes[1].text(j, i, 'NA' if not np.isfinite(array[i, j]) else f'{array[i,j]:.3g}',
                         ha='center', va='center', color='#172633', weight='bold')
    axes[1].set_xticks(range(2), ['score: -A', 'score: utility'], rotation=18, ha='right')
    axes[1].set_yticks(range(2), ['selected by -A', 'selected by utility'])
    axes[1].set_title('B  Selected cross-score', loc='left', fontsize=9.5)
    for spine in axes[1].spines.values(): spine.set_visible(False)
    image.set_alpha(.78)

    # C: exact set/source differences for every completed draw, versus its parent.
    categories = ('nodes_added', 'nodes_removed', 'edges_added', 'edges_removed',
                  'rewired_endpoint_pairs', 'protocol_changes', 'source_bodies_added', 'source_bodies_removed')
    totals = {identity: {key: 0 for key in categories} for identity in ARM_IDS}
    for identity in ARM_IDS:
        for row in data['arms'][identity]['rows']:
            if row['status'] == 'complete' and row['graph_changes'] is not None:
                counts = row['graph_changes']['vs_parent']['counts']
                for key in categories: totals[identity][key] += counts[key]
    x = np.arange(len(categories)); width = .36
    for index, identity in enumerate(ARM_IDS):
        axes[2].bar(x+(index-.5)*width, [totals[identity][key] for key in categories], width,
                    color=COLORS[identity], alpha=.9, label=LABELS[identity])
    axes[2].set_xticks(x, ['node +', 'node -', 'edge +', 'edge -', 'rewire', 'protocol', 'source +', 'source -'],
                       rotation=30, ha='right')
    axes[2].set_ylabel('Exact changes summed over completed draws')
    axes[2].set_title('C  Actual graph diffs vs parent', loc='left', fontsize=9.5)
    axes[2].grid(axis='y', alpha=.18)

    title = 'Original-native structural exploration under two explicit objectives'
    if data['classification'] == FIXTURE:
        title = 'SCRIPTED FIXTURE — NOT NATIVE QWEN FINDINGS'
    fig.suptitle(title, x=.06, y=.96, ha='left', fontsize=11.5)
    fig.text(.06, .025, 'Development engineering only. Same completed worlds are cross-scored under both losses; '
        'matrix shading is within-column display scaling.\n'
        'Graph bars are literal set/source differences, not effects. No held-out, causal, scientific-value, '
        'optimizer-convergence, or improvement claim.', color='#53616D', fontsize=8)
    fig.subplots_adjust(left=.07, right=.985, top=.84, bottom=.29, wspace=.45)
    paths = {kind: output.with_suffix('.'+kind) for kind in ('pdf', 'png', 'svg')}
    for kind, path in paths.items():
        fig.savefig(path, dpi=210 if kind == 'png' else None, facecolor='white')
    plt.close(fig)
    manifest = {'schema': 'scienceutopia.native-objective-structure-figure.v8', **data,
        'outputs': {key: {'path': str(path), 'sha256': file_sha256(path)} for key, path in paths.items()},
        'new_model_calls': 0, 'new_container_executions': 0}
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
