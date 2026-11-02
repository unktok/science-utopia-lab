#!/usr/bin/env python3
"""Audit-bound nested institutional paths, not synthetic scientific outcomes."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import tempfile

import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.text import Annotation, Text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.analyze_native_nested_search_v13 import (
    ACTUAL, ARM_IDS, FIXTURE, SCHEMA, design_change, executable_contracts, objective_specs)
from scripts.analyze_native_open_estimators_v11 import incumbent_path
from scripts.native_nested_estimator_audit_v13 import conditional_update_proof
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.optimization.native_nested_search import NativeNestedDesignCampaign, STAGES, COUNTS
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

COLORS = ('#087e9c', '#b3497d')
SHORT = ('T', 'E')
SLOTS = ('G0a', 'G0b', 'Updated', 'G1')


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


class _CompactReplay(NativeNestedDesignCampaign):
    """Logical source/likelihood replay; physical verification belongs to audit.

    Do not open workstation-specific checkpoint paths while publishing a compact
    verified audit. The independent native receipts remain explicitly required.
    """
    def _save(self):
        return None

    def _check_observation(self, value, draw):
        if draw['suggestion'] is None:
            if value is not None:
                raise ValueError('invalid draw acquired an observation')
            return
        evaluated = evaluate_loss(self.loss, value['metadata']['measurements'])
        if (value['suggestion_id'] != draw['suggestion']['suggestion_id']
                or value['candidate'] != draw['suggestion']['candidate']
                or value['metadata'].get('world_backend') != 'native-research-world'
                or value['metadata']['loss_spec_sha256'] != loss_spec_sha256(self.loss)
                or value['metadata']['loss_evaluation'] != evaluated
                or value['loss'] != (evaluated['loss'] if evaluated['status'] == 'complete' else None)
                or (value['status'] == 'complete') != (evaluated['status'] == 'complete')):
            raise ValueError('compact native observation/loss/design differs')


def _incumbents(rows):
    result = incumbent_path(rows)
    stages = {row['observation_id']: row['stage'] for row in rows if row['observation_id']}
    for point, row in zip(result['path'], rows):
        point['stage'] = row['stage']
        for tie in point['best_observation_ties']:
            tie['stage'] = stages[tie['observation_id']]
    for tie in result['best_observation_ties']:
        tie['stage'] = stages[tie['observation_id']]
    return result


def _replay(arm, loss):
    records = arm['records']
    first = records[0]['request']
    with tempfile.TemporaryDirectory(prefix='nested-figure-logical-replay-') as directory:
        controller = _CompactReplay(directory, initial_system=SystemSpec.from_dict(first['parent_system']),
            loss_spec=loss, seeds=[42], world_binding=first['world_binding'], seed=42, learning_rate=.1)
        controller.state['records'] = deepcopy(records)
        controller._validate()
    if arm.get('conditional_update_proof') != conditional_update_proof(records):
        raise ValueError('independent analytical conditional update proof differs')


def _physical(row, observation):
    proof = row.get('physical_proof') or {}
    if (proof.get('checkpoint_sha256') != row['checkpoint_sha256']
            or proof.get('native_loss') != row['own_loss']
            or proof.get('measurement') != observation['metadata']['measurements'][0]
            or proof.get('measurement', {}).get('metrics') != row['metrics']
            or proof.get('native_counts', {}).get('kernel_restored_without_execution') is not True
            or proof.get('native_counts', {}).get('migration_receipts') != 0):
        raise ValueError('native counts/checkpoint/measurement physical proof differs')
    for value in (proof.get('code_proof', {}).get('recorded_executions'),
            proof.get('response_proof', {}).get('wire_requests'),
            proof.get('response_proof', {}).get('researcher_responses')):
        if type(value) is not int or value < 0:
            raise ValueError('native execution/response counts must be nonnegative exact integers')
    capability = proof.get('capability_effect_proof', {})
    annual = capability.get('annual')
    if not isinstance(annual, list):
        raise ValueError('complete-plan/routing native proof missing')
    plans = sum(len(year['complete_plan_effects']) for year in annual)
    routes = [route for year in annual for route in year['review_routings']]
    count = sum(route['actual_review_count'] for route in routes)
    if (capability.get('complete_plan_effect_count') != plans
            or capability.get('routing_event_count') != len(routes)
            or capability.get('routed_actual_review_count') != count
            or any(route['actual_review_count'] != len(route['native_tasks']) for route in routes)):
        raise ValueError('native plan/routing task counts differ')
    return count if routes else None


def figure_data(report, expected_source=None, *, allow_synthetic=False):
    if (report.get('schema') != SCHEMA
            or report.get('content_sha256') != digest({k:v for k,v in report.items() if k != 'content_sha256'})
            or report.get('status') not in ('complete', 'budget-complete-with-failures')
            or report.get('objective_order') != list(ARM_IDS) or set(report.get('arms', {})) != set(ARM_IDS)
            or report.get('loss_specs') != objective_specs()):
        raise ValueError('exact terminal independent v13 loss/hash audit required')
    classification = report.get('classification')
    if classification not in (ACTUAL, FIXTURE) or (classification == FIXTURE) != allow_synthetic:
        raise ValueError('synthetic fixtures require explicit test-only flag; actual data cannot use it')
    source = report.get('source_commit')
    if (expected_source is not None and expected_source != source
            or classification == ACTUAL and (expected_source is None or len(source) != 40
                or any(c not in '0123456789abcdef' for c in source))):
        raise ValueError('exact actual source pin required')
    audit = report.get('audit', {})
    required = ('checkpoint_loss_reextracted', 'campaign_and_lineage_replayed', 'own_history_only_verified',
        'all_observations_and_exact_ties_retained', 'sole_conditional_LR_update_analytically_rederived')
    if (not _hash(audit.get('raw_inventory_sha256')) or any(audit.get(k) is not True for k in required)
            or audit.get('new_model_calls') != 0 or audit.get('new_container_executions') != 0):
        raise ValueError('independent source/native/own-history/update audit proofs required')
    if classification == ACTUAL:
        proof = audit.get('replay_source_proofs', {})
        files = proof.get('files', {})
        required_sources = {'utopia/optimization/native_nested_search.py', 'utopia/optimization/native_adaptive_search.py',
            'utopia/system/native_review_routing.py', 'utopia/system/native_activity_contracts.py',
            'utopia/system/native_kernel.py', 'utopia/simulation.py', 'scripts/run_native_nested_search_v13.py'}
        if (proof.get('status') != 'verified-exact-replay-source-blobs' or not required_sources <= set(files)
                or any(not _hash(p.get('actual_source_sha256'))
                    or p['actual_source_sha256'] != p.get('analysis_source_sha256') for p in files.values())):
            raise ValueError('exact complete runtime source replay proof required')
    claims = report.get('claims', {})
    if any(claims.get(k) is not False for k in ('held_out', 'causal_institutional_benefit', 'scientific_value',
            'designer_improvement_established', 'full_native_world_pathwise_autograd',
            'external_authorship_authenticated', 'variance_reduction_established')):
        raise ValueError('claims exceed conditional-development evidence')
    replies = report.get('physical_researcher_responses')
    if type(replies) is not int or replies < 0:
        raise ValueError('nonnegative physical response count required')
    if (claims.get('live_fixed_Qwen_researchers') is not (classification == ACTUAL and replies > 0)
            or claims.get('scripted_researcher_HTTP') is not (classification == FIXTURE)):
        raise ValueError('actual/fixture researcher attribution differs')
    rows, edits, policy, seen = {}, {}, {}, set()
    complete = consumed = code = wire = logical = 0
    for identity in ARM_IDS:
        arm = report['arms'][identity]
        records, observations = arm.get('records', []), arm.get('observations', [])
        if (len(records) != 3 or arm.get('pending') is not None or arm.get('objective_id') != identity
                or arm.get('loss_spec') != report['loss_specs'][identity]):
            raise ValueError('three exact terminal nested stages per arm required')
        _replay(arm, report['loss_specs'][identity])
        if arm.get('incumbents') != _incumbents(observations):
            raise ValueError('current/incumbent/all-tie path differs')
        selected, cursor, slot, authored = [], 0, 0, []
        for stage_index, record in enumerate(records):
            stage = STAGES[stage_index]
            count = COUNTS[stage_index]
            if (record['stage'] != stage or record['request']['count'] != count
                    or record['request']['world_binding']['source_commit'] != source):
                raise ValueError('stage/budget/world source differs')
            consumed += count
            attempted = [(None, None)] if record['generation_error'] else list(zip(record['draws'], record['observations']))
            for draw_index, (draw, observation) in enumerate(attempted):
                if cursor >= len(observations):
                    raise ValueError('missing retained native attempt row')
                row = observations[cursor]
                if (row.get('arm') != identity or row.get('stage') != stage
                        or row.get('generation') != record['generation']
                        or row.get('draw_index') != (None if draw is None else draw_index)
                        or row.get('draw') != draw or row.get('observation') != observation
                        or row.get('loss') != row.get('own_loss')
                        or row.get('generation_error') != record['generation_error']
                        or row.get('scheduled_native_slots') != (count if draw is None else 1)):
                    raise ValueError('exact retained draw/stage/observation identity differs')
                cross = row.get('cross_scores')
                if not isinstance(cross, dict) or set(cross) != set(ARM_IDS):
                    raise ValueError('both exact loss cross-scores required')
                routed = None
                if row['status'] == 'complete':
                    if (not observation or observation['status'] != 'complete'
                            or not _finite(row['own_loss']) or row.get('observation_id') in seen
                            or row.get('observation_id') != observation['observation_id']
                            or not _hash(row.get('checkpoint_sha256'))):
                        raise ValueError('unique actual observation/checkpoint identity required')
                    seen.add(row['observation_id'])
                    for loss_id in ARM_IDS:
                        result = evaluate_loss(report['loss_specs'][loss_id], [{'run_id': row['observation_id'], 'metrics': row['metrics']}])
                        if result['status'] != 'complete' or cross[loss_id] != result['loss']:
                            raise ValueError('cross-score differs from native metrics')
                    if cross[identity] != row['own_loss']:
                        raise ValueError('own loss differs from matching cross-score')
                    routed = _physical(row, observation)
                    proof = row['physical_proof']
                    code += proof['code_proof']['recorded_executions']
                    wire += proof['response_proof']['wire_requests']
                    logical += proof['response_proof']['researcher_responses']
                    complete += 1
                elif (row['status'] not in ('technical-failure', 'generation-failure')
                        or row['own_loss'] is not None or any(v is not None for v in cross.values())):
                    raise ValueError('failed attempts must remain explicit nulls')
                system = row.get('system')
                if system is not None:
                    if (draw is None or not draw['suggestion'] or system != draw['suggestion']['candidate']
                            or SystemSpec.from_dict(system).fingerprint != row['system_fingerprint']
                            or executable_contracts(system) != row['contracts']):
                        raise ValueError('actual source/graph/contracts differ')
                    parent = record['request']['parent_system']
                    if (SystemSpec.from_dict(parent).fingerprint != row['parent_system_fingerprint']
                            or design_change(parent, system) != row['lineage']['vs_parent']):
                        raise ValueError('literal parent/source/graph lineage differs')
                selected.append({**row, 'slot': slot, 'slot_span': count if draw is None else 1,
                    'incumbent_loss': arm['incumbents']['path'][cursor]['best_loss_so_far'],
                    'routed_tasks': routed})
                cursor += 1
                slot += count if draw is None else 1
            if stage != 'updated-proposal':
                # Authored vocabulary/base graph, not a stochastic factor draw.
                if record['generation_error']:
                    authored.append({'generation': record['generation'], 'change': None})
                else:
                    from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
                    base = GeneratedMixedDesign(SystemSpec.from_dict(record['request']['parent_system']), record['definition'],
                        loss_spec=report['loss_specs'][identity], seed=record['request']['rng_seed'],
                        single_draw_blackbox=count == 1).base
                    authored.append({'generation': record['generation'],
                        'change': design_change(record['request']['parent_system'], base.to_dict())})
        if cursor != len(observations) or slot != 4:
            raise ValueError('extra/missing retained rows or consumed slots')
        first = records[0]['report']
        before, after = first['weights_before'], first['weights_after']
        policy[identity] = {'status': first['status'], 'weights_before': before, 'weights_after': after,
            'mean_step_l2': None if before is None else math.sqrt(math.fsum((x-y)**2 for x,y in zip(
                before['continuous_mean'], after['continuous_mean']))),
            'logit_step_l2': None if before is None else math.sqrt(math.fsum((x-y)**2
                for key in before['logits'] for x,y in zip(before['logits'][key], after['logits'][key])))}
        rows[identity], edits[identity] = selected, authored
    if (report.get('planned_native_world_budget') != 8 or report.get('consumed_native_slots') != consumed
            or consumed != 8 or report.get('physical_native_worlds') != complete
            or report.get('logical_completed_draws') != complete
            or report.get('completed_code_executions') != code or report.get('completed_wire_requests') != wire
            or report.get('logical_completed_researcher_responses') != logical
            or report.get('reused_responses_in_completed_worlds') != 0
            or complete == 8 and replies != logical):
        raise ValueError('actual native slot/world/code/wire/reply counts differ')
    if report['status'] != ('complete' if complete == 8 else 'budget-complete-with-failures'):
        raise ValueError('terminal complete/failure status differs')
    return {'classification': classification, 'source_commit': source,
        'audit_content_sha256': report['content_sha256'], 'rows': rows, 'authored_edits': edits, 'policy': policy,
        'physical_researcher_responses': replies,
        'scope': 'Conditional finite development paths; no held-out, causal benefit, successful invention or optimizer-superiority claim.'}


def _value(value):
    return 'n/a' if value is None else f'{value:.3g}'


def _table(axis, headers, labels, values, *, widths=None, bbox=None):
    axis.axis('off')
    # Row-label auto-sizing varies between Agg/SVG renderers. An ordinary,
    # explicitly sized first column keeps the actual PNG and vector identical
    # in layout, rather than letting labels escape the native paper margin.
    label_share = .28 if any(len(label) > 5 for label in labels) else .18
    columns = [label_share, *([(1-label_share)/len(headers)]*len(headers))]
    table = axis.table(cellText=[[label, *row] for label, row in zip(labels, values)],
        colLabels=['', *headers], loc='center', cellLoc='center', colWidths=columns, bbox=bbox)
    table.auto_set_font_size(False)
    table.set_fontsize(7.2)
    table.scale(1, 1.26)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#d7e1e8')
        cell.set_linewidth(.45)
        cell.set_facecolor('#eaf0f4' if row == 0 else '#f7f9fb' if row % 2 else 'white')
        if row == 0:
            cell.set_height(cell.get_height()*1.7)
    return table


def _separate_crossscore_labels(axis, renderer):
    """Deterministic annotation-only separation in physical point units."""
    placed = []
    bounds = axis.get_window_extent(renderer)
    for text in axis.texts:
        if not isinstance(text, Annotation):
            continue
        x, y = text.get_position()
        for delta in (0, 7, -7, 14, -14, 21, -21):
            text.set_position((x, y+delta))
            text.update_positions(renderer)
            # Leader segments may cross; only the visible label rectangles
            # must remain separate. Each leader still ends at its exact datum.
            box = Text.get_window_extent(text, renderer).expanded(1.05, 1.1)
            if (box.y0 >= bounds.y0 and box.y1 <= bounds.y1
                    and box.x0 >= 0 and box.x1 <= axis.figure.bbox.x1
                    and not any(box.overlaps(other) for other in placed)):
                placed.append(box)
                break
        else:
            raise ValueError('cross-score labels cannot fit native paper bounds without collision')


def render(report, output, *, audit_path, expected_source=None, allow_synthetic=False):
    output, audit_path = Path(output), Path(audit_path)
    if allow_synthetic and not output.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise ValueError('synthetic output must stay in temporary test storage')
    if json.loads(audit_path.read_text()) != report:
        raise ValueError('rendered audit differs from exact supplied audit file')
    data = figure_data(report, expected_source, allow_synthetic=allow_synthetic)
    defaults = dict(matplotlib.rcParamsDefault)
    defaults.pop('backend', None)
    defaults.update({'font.family': 'DejaVu Sans', 'font.size': 8., 'axes.labelsize': 7.5,
        'axes.titlesize': 8.5, 'xtick.labelsize': 7.2, 'ytick.labelsize': 7.2,
        'legend.fontsize': 7.2, 'svg.fonttype': 'none', 'svg.hashsalt': 'native-nested-search-v13'})
    with matplotlib.rc_context(defaults):
        fig = Figure(figsize=(5.5, 7.8))
        FigureCanvasAgg(fig)
        axes = fig.subplots(3, 2)
        for index, identity in enumerate(ARM_IDS):
            ax, rows = axes[0, index], data['rows'][identity]
            good = [row for row in rows if row['own_loss'] is not None]
            if good:
                ax.plot([r['slot'] for r in rows], [r['own_loss'] if r['own_loss'] is not None else math.nan for r in rows],
                    'o-', color=COLORS[index], linewidth=1.4, markersize=4, label='Current draw')
                ax.step([r['slot'] for r in rows], [r['incumbent_loss'] if r['incumbent_loss'] is not None else math.nan for r in rows],
                    where='post', color='#354654', linestyle='--', label='Best so far')
                ax.legend(loc='best', handlelength=1.5)
            else:
                ax.text(.5, .45, 'No completed native loss', transform=ax.transAxes, ha='center', fontsize=7.5)
                ax.set_yticks([])
            for row in rows:
                if row['own_loss'] is None:
                    ax.text(row['slot'], .94, 'Null\nslot' if row['slot_span'] == 1 else 'Null\n2 slots',
                        transform=ax.get_xaxis_transform(), va='top', ha='center', fontsize=7.2, color='#a23b43')
            ax.axvline(1.5, color='#8e9aa5', linewidth=.8, linestyle=':')
            ax.axvline(2.5, color='#8e9aa5', linewidth=.8, linestyle=':')
            ax.set_xticks(range(4), SLOTS)
            ax.set_xlim(-.25, 3.25)
            ax.set_title('A  Throughput: $L=-A$' if index == 0 else 'B  Efficiency: $L=-Q+0.5R$')
            ax.set_ylabel('Own loss (lower is better)')
            ax.grid(axis='y', alpha=.2)
        labels, values = [], []
        for index, identity in enumerate(ARM_IDS):
            for row in data['rows'][identity]:
                labels.append(SHORT[index]+' '+SLOTS[row['slot']])
                metrics = row['metrics'] or {}
                values.append([_value(metrics.get(key, {}).get('value')) for key in (
                    'native.accepted_decisions', 'native.accepted_peer_score_sum', 'native.review_records')]
                    + [_value(row['routed_tasks'])])
        axes[1, 0].set_title('C  Actual native outcomes', y=1.05, pad=0)
        _table(axes[1, 0], ['A', 'Q', 'R', 'Routed\ntasks'], labels, values, bbox=(0,0,1,.93))
        labels, values = [], []
        for index, identity in enumerate(ARM_IDS):
            for authored in data['authored_edits'][identity]:
                labels.append(SHORT[index]+f" G{authored['generation']}")
                c = authored['change']['counts'] if authored['change'] else None
                values.append(['n/a']*3 if c is None else [str(c['source_bodies_added']),
                    f"{c['nodes_added']}/{c['nodes_removed']}", f"{c['edges_added']}/{c['edges_removed']}"])
        axes[1, 1].set_title('D  Authored base vs parent', y=1.05, pad=0)
        _table(axes[1, 1], ['New\nbodies', 'Nodes\n+/−', 'Wires\n+/−'], labels, values,
            bbox=(0,.3,1,.6))
        axes[1, 1].text(.5, .04, 'Literal edits, not proven invention.\nFactor-draw changes are separate.',
            transform=axes[1, 1].transAxes, ha='center', va='bottom', fontsize=7.2, color='#435568')
        values = [[_value(data['policy'][identity][key]) for key in ('mean_step_l2', 'logit_step_l2')] for identity in ARM_IDS]
        axes[2, 0].set_title('E  One G0 conditional step / arm', y=1.05, pad=0)
        _table(axes[2, 0], ['Latent mean\nL2 change', 'Logits\nL2 change'], ['T', 'E'], values,
            bbox=(0,.42,1,.32))
        axes[2, 0].text(.5, .06, 'One LOO step → one fresh forward.\nG1 resets to its authored definition.\nZero change is not a success claim.',
            transform=axes[2, 0].transAxes, ha='center', va='bottom', fontsize=7.2, color='#435568')
        ax = axes[2, 1]
        cross_x = [row['cross_scores'][ARM_IDS[0]] for rows in data['rows'].values()
            for row in rows if row['own_loss'] is not None]
        midpoint = (min(cross_x)+max(cross_x))/2 if cross_x else 0
        for index, identity in enumerate(ARM_IDS):
            grouped = {}
            for row in data['rows'][identity]:
                if row['own_loss'] is not None:
                    grouped.setdefault(tuple(row['cross_scores'][k] for k in ARM_IDS), []).append(
                        ('0a', '0b', 'U', '1')[row['slot']])
            points = sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0]))
            for point_index, ((x, y), tags) in enumerate(points):
                ax.scatter(x, y, color=COLORS[index], marker=('o', 's')[index], s=24,
                    label=('Throughput', 'Efficiency')[index] if point_index == 0 else None)
                # Close vertical profiles otherwise stack short labels directly
                # on top of one another. Alternate sides in the second arm;
                # this affects annotation only, never coordinates or scores.
                leftward = (point_index % 2 == 1) if index else x >= midpoint
                ax.annotate('/'.join(tags), (x,y), xytext=(-6 if leftward else 6, 0),
                    textcoords='offset points', ha='right' if leftward else 'left', va='center',
                    fontsize=7.2, color=COLORS[index],
                    arrowprops={'arrowstyle': '-', 'color': COLORS[index], 'linewidth': .6,
                        'shrinkA': 1., 'shrinkB': 2., 'alpha': .75})
        ax.set(title='F  Same-world cross-scores', xlabel='Throughput loss', ylabel='Efficiency loss')
        ax.grid(alpha=.2)
        ax.margins(x=.5, y=.55)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(loc='best', handlelength=1)
        else:
            ax.text(.5, .5, 'No completed cross-scores', transform=ax.transAxes, ha='center', fontsize=7.2)
            ax.set_xticks([])
            ax.set_yticks([])
        fig.suptitle('SYNTHETIC CONTRACT FIXTURE — NOT EVIDENCE' if allow_synthetic else
            'Free institutions → conditional update → free redesign', fontsize=10.5, fontweight='bold', y=.985)
        fig.text(.5, .018, 'G0a/G0b: IID design draws. Updated: fresh G0-weight forward. G1: free re-authoring.\n'
            'T: throughput arm; E: efficiency arm. All attempts/ties retained; no extra merit veto.\n'
            'A: accepted; Q: original-peer mean sum; R: review records. n/a is not zero.\n'
            'Cross-score labels: 0a/0b/U/1. Development worlds, not held-out or causal benefit.',
            ha='center', fontsize=7.2, color='#435568')
        fig.tight_layout(rect=(.025,.11,.99,.96), h_pad=2.5, w_pad=2.0)
        fig.canvas.draw()
        _separate_crossscore_labels(axes[2,1], fig.canvas.get_renderer())
        fig.canvas.draw()
        output.parent.mkdir(parents=True, exist_ok=True)
        files = []
        for suffix in ('.png', '.svg'):
            path = output.with_suffix(suffix)
            fig.savefig(path, dpi=200, metadata={'Date': None} if suffix == '.svg' else None)
            files.append({'path': str(path), 'sha256': file_sha256(path)})
    manifest = {'schema': 'scienceutopia.native-nested-search-figure.v13', 'classification': data['classification'],
        'source_commit': data['source_commit'], 'audit_file_sha256': file_sha256(audit_path),
        'audit_content_sha256': report['content_sha256'], 'generator_sha256': file_sha256(Path(__file__)),
        'files': files, 'data': data}
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
    result = render(json.loads(args.audit.read_text()), args.output, audit_path=args.audit,
        expected_source=args.expected_source, allow_synthetic=args.allow_synthetic)
    print(json.dumps({'content_sha256': result['content_sha256'], 'files': result['files']}, sort_keys=True))


if __name__ == '__main__':
    main()
