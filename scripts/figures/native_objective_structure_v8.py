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
            elif (row['status'] not in {'technical-failure', 'generation-failure'} or value is not None
                    or row['observation'] is not None and row['observation'].get('loss') is not None):
                raise ValueError('technical failure cannot be plotted as a numerical loss')
            if row['status'] == 'generation-failure' and (row.get('draw') is not None
                    or row.get('generation_error') is None or row.get('planned_draws') != 2):
                raise ValueError('generation failure plotting receipt differs')
            label = (f"G{row['generation']+1} vocabulary failure" if row['status'] == 'generation-failure'
                     else f"G{row['generation']+1}{chr(97+row['draw_index'])}")
            x_position = (row['generation']*2+.5 if row['status'] == 'generation-failure'
                          else row['generation']*2+row['draw_index'])
            rows.append({'label': label, 'x_position': x_position,
                'status': row['status'], 'loss': value,
                'observation_id': (row['observation']['observation_id'] if row['status'] == 'complete' else None),
                'suggestion_id': (row['observation']['suggestion_id'] if row['status'] == 'complete' else None),
                'cross_objective_losses': row['cross_objective_losses'],
                'graph_changes': row['graph_changes'],
                'system_fingerprint': (row['physical_proof']['measurement']['system_fingerprint']
                                       if row['status'] == 'complete' else None)})
        if arm['loss_path'] != [row['loss'] for row in rows]:
            raise ValueError('plotted loss trajectory differs from audit')
        if arm.get('generation_failures', []) != [row for row in arm['rows']
                                                   if row['status'] == 'generation-failure']:
            raise ValueError('generation failure budget accounting differs')
        complete = [row for row in rows if row['loss'] is not None]
        best = min((row['loss'] for row in complete), default=None)
        tied = [row for row in complete if row['loss'] == best] if best is not None else []
        selection = arm['selection']
        observation_ids = [row['observation_id'] for row in complete]
        suggestion_ids = [row['suggestion_id'] for row in complete]
        if (any(not isinstance(value, str) or not value for value in observation_ids+suggestion_ids)
                or len(set(observation_ids)) != len(observation_ids)
                or len(set(suggestion_ids)) != len(suggestion_ids)):
            raise ValueError('completed draw observation/suggestion identities must be unique')
        if (selection.get('best_loss') != best or selection.get('tie_count') != len(tied)
                or selection.get('tied_system_fingerprints') != [row['system_fingerprint'] for row in tied]
                or selection.get('tied_observation_ids') != [row['observation_id'] for row in tied]
                or selection.get('tied_suggestion_ids') != [row['suggestion_id'] for row in tied]
                or selection.get('representative_observation_id') != (tied[0]['observation_id'] if tied else None)
                or selection.get('representative_suggestion_id') != (tied[0]['suggestion_id'] if tied else None)
                or selection.get('representative_system_fingerprint') !=
                    (tied[0]['system_fingerprint'] if tied else None)):
            raise ValueError('selected development minimum/ties differ from audited rows')
        arms[identity] = {'rows': rows, 'selection': arm['selection']}
    matrix = report['selected_cross_objective_matrix']
    if set(matrix) != set(ARM_IDS) or any(value is not None and set(value) != set(ARM_IDS)
                                          for value in matrix.values()):
        raise ValueError('selected cross-objective matrix differs')
    for identity in ARM_IDS:
        observation_id = arms[identity]['selection']['representative_observation_id']
        representative = (next((row for row in arms[identity]['rows']
            if row['observation_id'] == observation_id), None) if observation_id is not None else None)
        expected = representative['cross_objective_losses'] if representative else None
        if matrix[identity] != expected:
            raise ValueError('selected cross-objective matrix differs from representative draw')
    return {'schema': FIGURE_DATA_SCHEMA, 'classification': report['classification'],
        'report_content_sha256': report['content_sha256'], 'source_commit': report['source_commit'],
        'arms': arms, 'selected_cross_objective_matrix': matrix,
        'scope': 'development engineering; same draws cross-scored; no held-out or generalized benefit claim'}


def create(report, output):
    output = Path(output)
    data = figure_data(report)
    if data['classification'] == FIXTURE and 'paper' in output.parts and 'figures' in output.parts:
        raise ValueError('scripted fixture cannot be published as an empirical paper result')
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.4,
        'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42, 'ps.fonttype': 42})
    fig = plt.figure(figsize=(5.5, 6.8))
    grid = fig.add_gridspec(2, 2, height_ratios=[1.25, .92])
    path_grid = grid[0, 0].subgridspec(2, 1, hspace=.82)
    path_axes = [fig.add_subplot(path_grid[index, 0]) for index in range(2)]
    axes = [path_axes[0], fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[1, :])]

    # A: real independently reconstructed bound losses; gaps remain gaps.
    # The losses have different units: never put their raw values on one axis.
    for identity, path_ax in zip(ARM_IDS, path_axes):
        rows = data['arms'][identity]['rows']
        labelled = False
        for i, row in enumerate(rows):
            if row['loss'] is not None:
                path_ax.scatter(row['x_position'], row['loss'], s=42, color=COLORS[identity],
                    edgecolor='white', linewidth=.6, label=LABELS[identity] if not labelled else None, zorder=3)
            else:
                path_ax.scatter(row['x_position'], 0, marker='x', s=45,
                    color=COLORS[identity], label=LABELS[identity] if not labelled else None,
                    transform=path_ax.get_xaxis_transform())
                if row['status'] == 'generation-failure':
                    path_ax.annotate('vocabulary\nfailure', (row['x_position'], .03),
                        xycoords=path_ax.get_xaxis_transform(), xytext=(0, 5), textcoords='offset points',
                        ha='center', va='bottom', color=COLORS[identity], fontsize=6.8)
            labelled = True
        path_ax.set_xticks(range(4), ['G1a', 'G1b', 'G2a', 'G2b'])
        path_ax.set_xlim(-.35, 3.35)
        path_ax.set_ylabel('Own loss')
        path_ax.set_title('A1  Throughput' if identity == ARM_IDS[0] else 'A2  Reviewed utility',
                          loc='left', fontsize=9.2, color=COLORS[identity], pad=7)
        path_ax.grid(axis='y', alpha=.18)

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
                         ha='center', va='center',
                         color='white' if np.isfinite(shown[i, j]) and shown[i, j] > .55 else '#172633',
                         weight='bold')
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
    axes[2].set_xticks(x, ['node +', 'node -', 'edge +', 'edge -', 'port rewire', 'protocol', 'source +', 'source -'],
                       rotation=30, ha='right')
    axes[2].set_ylabel('Exact changes vs parent\n(sum over completed draws)')
    axes[2].set_title('C  Actual graph diffs vs parent', loc='left', fontsize=9.5, pad=26)
    axes[2].grid(axis='y', alpha=.18)
    axes[2].legend(labels=['Throughput', 'Reviewed utility'], frameon=False,
                   fontsize=7.5, loc='lower left', bbox_to_anchor=(0, 1.00), ncol=2)

    title = 'Two-objective native structural exploration'
    if data['classification'] == FIXTURE:
        title = 'SCRIPTED FIXTURE - NOT NATIVE RESULTS'
    fig.suptitle(title, x=.08, y=.97, ha='left', fontsize=11.5)
    fig.text(.08, .022, 'Development engineering only. Same worlds cross-scored; colors scaled within columns.\n'
        'Graph bars are literal differences, not effects.\n'
        'No held-out, causal, scientific-value, convergence,\nor comparative optimizer claim.',
        color='#53616D', fontsize=7.8)
    fig.subplots_adjust(left=.14, right=.985, top=.87, bottom=.21, wspace=.80, hspace=.67)
    paths = {kind: output.with_suffix('.'+kind) for kind in ('pdf', 'png', 'svg')}
    for kind, path in paths.items():
        fig.savefig(path, dpi=210 if kind == 'png' else None, facecolor='white')
        if kind == 'svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    plt.close(fig)
    manifest = {**data, 'schema': 'scienceutopia.native-objective-structure-figure.v8',
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
