#!/usr/bin/env python3
"""Actual objective-conditioned redesign graphics, derived only from an audit."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import tempfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.analyze_native_objective_redesign_v12 import (
    ACTUAL, ARM_IDS, FIXTURE, SCHEMA, design_change, executable_contracts, objective_specs,
)
from scripts.analyze_native_open_estimators_v11 import incumbent_path
from utopia.optimization.loss import evaluate_loss
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

plt.rcParams['svg.hashsalt'] = 'scienceutopia-native-objective-redesign-v12'
COLORS = ('#087e9c', '#b3497d')
LABELS = ('Throughput objective', 'Net reviewed utility objective')


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def figure_data(report, expected_source=None, *, allow_synthetic=False):
    if (report.get('content_sha256') != digest({k:v for k,v in report.items() if k != 'content_sha256'})
            or report.get('schema') != SCHEMA or report.get('status') not in ('complete', 'budget-complete-with-failures')
            or report.get('objective_order') != list(ARM_IDS) or set(report.get('arms', {})) != set(ARM_IDS)
            or report.get('loss_specs') != objective_specs()):
        raise ValueError('source/hash/full-objective-bound terminal v12 audit required')
    classification = report.get('classification')
    if classification not in (ACTUAL, FIXTURE) or (classification == FIXTURE) != allow_synthetic:
        raise ValueError('synthetic fixtures require an explicit test-only flag; actual evidence cannot use it')
    source = report.get('source_commit')
    if (expected_source is not None and expected_source != source
            or classification == ACTUAL and (expected_source is None or len(source) != 40
                or any(c not in '0123456789abcdef' for c in source))):
        raise ValueError('exact actual source pin required')
    audit = report.get('audit', {})
    if (not _hash(audit.get('raw_inventory_sha256')) or audit.get('new_model_calls') != 0
            or audit.get('new_container_executions') != 0 or audit.get('checkpoint_loss_reextracted') is not True
            or audit.get('campaign_and_lineage_replayed') is not True
            or audit.get('all_observations_and_exact_ties_retained') is not True
            or audit.get('own_history_only_verified') is not True):
        raise ValueError('independent native/lineage/own-history audit proofs missing')
    if classification == ACTUAL and audit.get('replay_source_proofs', {}).get('status') != 'verified-exact-replay-source-blobs':
        raise ValueError('source replay proof missing')
    claims = report.get('claims', {})
    if any(claims.get(key) is not False for key in ('held_out', 'causal_institutional_benefit',
            'scientific_value', 'designer_improvement_established', 'full_native_world_pathwise_autograd',
            'external_authorship_authenticated')):
        raise ValueError('claims exceed development evidence')
    if (claims.get('live_fixed_Qwen_researchers') is not (classification == ACTUAL)
            or claims.get('scripted_researcher_HTTP') is not (classification == FIXTURE)):
        raise ValueError('actual/fixture attribution differs')
    rows, complete, seen = {}, 0, set()
    for identity in ARM_IDS:
        arm = report['arms'][identity]
        observations, records = arm.get('observations', []), arm.get('records', [])
        if (len(observations) != 3 or len(records) != 3 or arm.get('loss_spec') != report['loss_specs'][identity]
                or arm.get('pending') is not None or arm.get('objective_id') != identity):
            raise ValueError('all three terminal generations per objective required')
        if arm.get('incumbents') != incumbent_path(observations):
            raise ValueError('incumbent/tie path differs')
        selected = []
        for generation, (row, record) in enumerate(zip(observations, records)):
            if (row.get('arm') != identity or (row.get('generation'), row.get('draw_index')) != (generation, 0)
                    or row.get('loss') != row.get('own_loss')):
                raise ValueError('objective/generation/loss identity differs')
            cross = row.get('cross_scores')
            if not isinstance(cross, dict) or set(cross) != set(ARM_IDS):
                raise ValueError('both objective cross-scores required for every attempt')
            if row['status'] == 'complete':
                complete += 1
                if (not _finite(row['own_loss']) or row.get('observation_id') in seen
                        or not isinstance(row.get('observation_id'), str)
                        or not _hash(row.get('checkpoint_sha256'))):
                    raise ValueError('actual unique observation/checkpoint identity required')
                seen.add(row['observation_id'])
                for loss_id in ARM_IDS:
                    evaluated = evaluate_loss(report['loss_specs'][loss_id], [{'run_id': row['observation_id'], 'metrics': row['metrics']}])
                    expected = evaluated['loss'] if evaluated['status'] == 'complete' else None
                    if cross[loss_id] != expected:
                        raise ValueError('cross-score differs from independently audited checkpoint metrics')
                if cross[identity] != row['own_loss']:
                    raise ValueError('own loss is not the matching cross-score')
            elif (row['status'] not in ('technical-failure', 'generation-failure') or row['own_loss'] is not None
                    or any(value is not None for value in cross.values())):
                raise ValueError('failures must remain explicit null observations')
            system = row.get('system')
            if system is not None:
                if SystemSpec.from_dict(system).fingerprint != row.get('system_fingerprint'):
                    raise ValueError('plotted source/graph fingerprint differs')
                if executable_contracts(system) != row.get('contracts'):
                    raise ValueError('declared source/protocol/process contracts differ')
                parent = record['request']['parent_system']
                if (SystemSpec.from_dict(parent).fingerprint != row['parent_system_fingerprint']
                        or row['lineage']['vs_parent'] != design_change(parent, system)):
                    raise ValueError('parent/source/wiring/process lineage differs')
            selected.append({**row, 'incumbent_loss': arm['incumbents']['path'][generation]['best_loss_so_far']})
        rows[identity] = selected
    if (report.get('physical_native_worlds') != complete or report.get('logical_completed_draws') != complete
            or report.get('reused_responses_in_completed_worlds') != 0):
        raise ValueError('native world counts or response reuse differs')
    return {'classification': classification, 'source_commit': source,
        'audit_content_sha256': report['content_sha256'], 'rows': rows,
        'physical_researcher_responses': report.get('physical_researcher_responses'),
        'scope': 'Development-world paths and same-checkpoint cross-scores; not held-out, causal benefit or optimizer superiority.'}


def render(report, output, *, audit_path, expected_source=None, allow_synthetic=False):
    output = Path(output)
    if allow_synthetic and not output.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise ValueError('synthetic figure output must stay in temporary test storage')
    data = figure_data(report, expected_source, allow_synthetic=allow_synthetic)
    fig, axes = plt.subplots(2, 2, figsize=(11.8, 7.9), gridspec_kw={'height_ratios': [1, 1.2]})
    for index, identity in enumerate(ARM_IDS):
        ax = axes[0, index]
        rows = data['rows'][identity]
        values = [row['own_loss'] if row['own_loss'] is not None else float('nan') for row in rows]
        incumbents = [row['incumbent_loss'] if row['incumbent_loss'] is not None else float('nan') for row in rows]
        ax.plot(range(3), values, 'o-', color=COLORS[index], linewidth=1.8, label='Current observed system')
        ax.step(range(3), incumbents, where='post', color='#303c49', linestyle='--', label='Best observed so far')
        for generation, row in enumerate(rows):
            if row['own_loss'] is None:
                ax.text(generation, .95, 'Technical\nfailure', transform=ax.get_xaxis_transform(),
                    ha='center', va='top', fontsize=8, color='#a23b43')
        ax.set(title=f'{chr(65+index)}  {LABELS[index]}', xlabel='Authored generation', ylabel='Own optimization loss (lower is better)')
        ax.set_xticks(range(3), ['G0', 'G1', 'G2'])
        ax.grid(alpha=.2)
        ax.legend(fontsize=8, loc='best')
    cross_ax = axes[1, 0]
    for index, identity in enumerate(ARM_IDS):
        rows = data['rows'][identity]
        good = [row for row in rows if all(_finite(v) for v in row['cross_scores'].values())]
        grouped = {}
        for row in good:
            coordinates = tuple(row['cross_scores'][key] for key in ARM_IDS)
            grouped.setdefault(coordinates, []).append(f"G{row['generation']}")
        for point_index, ((x, y), generations) in enumerate(grouped.items()):
            cross_ax.scatter(x, y, color=COLORS[index], marker=('o','s')[index], s=58, alpha=.78,
                label=LABELS[index] if point_index == 0 else None)
            cross_ax.annotate('/'.join(generations), (x,y), xytext=(5, 7+index*10), textcoords='offset points', fontsize=8, color=COLORS[index])
    cross_ax.set(title='C  Same-checkpoint objective profiles', xlabel='Throughput loss (lower is better)', ylabel='Net reviewed utility loss (lower is better)')
    cross_ax.grid(alpha=.2)
    cross_ax.margins(x=.24, y=.30)
    handles, _ = cross_ax.get_legend_handles_labels()
    if handles:
        cross_ax.legend(fontsize=8)
    matrix, labels = [], []
    fields = ('source_bodies_added', 'nodes_added', 'edges_added', 'process_contract_changes')
    for index, identity in enumerate(ARM_IDS):
        for row in data['rows'][identity]:
            labels.append(f"{'Throughput' if index == 0 else 'Utility'} G{row['generation']}")
            matrix.append([row['lineage']['vs_parent']['counts'][key] if row['lineage'] else np.nan for key in fields])
    ax = axes[1, 1]
    ax.imshow(np.asarray(matrix, dtype=float), aspect='auto', cmap='Blues', interpolation='nearest', vmin=0)
    for y, values in enumerate(matrix):
        for x, value in enumerate(values):
            ax.text(x, y, 'n/a' if math.isnan(value) else str(value), ha='center', va='center', fontsize=9,
                color='white' if not math.isnan(value) and value > np.nanmax(matrix)*.55 else '#213447')
    ax.set_title('D  Literal changes against own incumbent parent')
    ax.set_xticks(range(4), ['Source bodies\nadded', 'Nodes\nadded', 'Wires\nadded', 'Process\ncontracts changed'], fontsize=8)
    ax.set_yticks(range(6), labels, fontsize=8)
    ax.tick_params(length=0)
    title = 'Objective-conditioned open institutional redesign'
    if allow_synthetic:
        title = 'SYNTHETIC CONTRACT FIXTURE — NOT RESEARCH EVIDENCE'
    fig.suptitle(title, fontsize=15, fontweight='bold', y=.98)
    fig.text(.5, .025, 'All attempts and exact best ties retained. Cross-scores are development reuse, not held-out tests.\n'
        'Text/graph changes do not establish useful invention. Fixed Qwen weights; original native researcher world.',
        ha='center', va='bottom', fontsize=8, color='#394957')
    fig.tight_layout(rect=(0,.085,1,.95), h_pad=2.0, w_pad=2.7)
    output.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for suffix in ('.png', '.svg'):
        path = output.with_suffix(suffix)
        fig.savefig(path, dpi=190, metadata={'Date': None} if suffix == '.svg' else None)
        files.append({'path': str(path), 'sha256': file_sha256(path)})
    plt.close(fig)
    manifest = {'schema': 'scienceutopia.native-objective-redesign-figure.v12',
        'source_commit': data['source_commit'], 'classification': data['classification'],
        'audit_file_sha256': file_sha256(audit_path), 'audit_content_sha256': report['content_sha256'],
        'generator_sha256': file_sha256(Path(__file__)), 'files': files, 'data': data}
    manifest['content_sha256'] = digest(manifest)
    write_json_atomic(output.with_suffix('.manifest.json'), manifest, sort_keys=True, allow_nan=False)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--allow-synthetic', action='store_true')
    args = parser.parse_args()
    report = json.loads(args.audit.read_text())
    result = render(report, args.output, audit_path=args.audit,
        expected_source=args.expected_source, allow_synthetic=args.allow_synthetic)
    print(json.dumps({'content_sha256': result['content_sha256'], 'files': result['files']}, sort_keys=True))


if __name__ == '__main__':
    main()
