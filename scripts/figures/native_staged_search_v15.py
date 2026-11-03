#!/usr/bin/env python3
"""Three-panel, audit-bound native paths and separately budgeted v15 costs."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.text import Text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utopia.optimization.loss import evaluate_loss
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-staged-search-audit-summary.v15'
ACTUAL = 'actual-local-qwen-staged-native-search-development-v15'
FIXTURE = 'scripted-fixture-not-native-results'
ARMS = ('throughput', 'efficiency')
LOSS_FILES = ('native-joint-v5-throughput.json', 'native-reviewed-production-efficiency-v13.json')
COUNT_KEYS = ('dispatch_intents', 'completed_step_receipts', 'recorded_POST_attempts',
    'known_HTTP_responses', 'known_designer_responses', 'interrupted_response_unknown', 'valid_finished_generations')


def _hash(value, size=64):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{' + str(size) + '}', value) is not None


def _count(value):
    return type(value) is int and value >= 0


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def objective_specs():
    return {arm: json.loads((ROOT / 'research/objectives/losses' / name).read_text())
        for arm, name in zip(ARMS, LOSS_FILES)}


def _report(report, source, revision, *, allow_scripted):
    _require(isinstance(report, dict) and report.get('schema') == SCHEMA, 'exact compact v15 independent audit required')
    _require(report.get('content_sha256') == digest({k: v for k, v in report.items() if k != 'content_sha256'}),
        'audit content hash differs')
    classification = FIXTURE if allow_scripted else ACTUAL
    _require(report.get('classification') == classification, 'actual evidence required; SCRIPTED opt-in is test-only')
    _require(_hash(source, 40) and report.get('source_commit') == source, 'exact experiment source pin required')
    _require(report.get('status') in {'complete', 'budget-complete-with-failures'}
        and report.get('budget_terminal') is True and report.get('queue_terminal') is True,
        'terminal budget and queue proofs required')
    _require(report.get('planned_native_slots') == report.get('consumed_native_slots') == 4
        and report.get('exact_full_audit_reproducible') is True
        and _hash(report.get('exact_full_audit_content_sha256')), 'four separately budgeted slots/full audit binding required')
    claims = report.get('claims', {})
    _require(all(claims.get(key) is False for key in ('held_out', 'scientific_benefit_established',
        'designer_improvement_established', 'method_superiority_established', 'model_weights_trained',
        'full_world_pathwise_autograd', 'same_society_adoption')), 'bounded development claims required')
    proof = report.get('audit', {})
    inventory = proof.get('raw_input_sha256s')
    _require(proof.get('exact_raw_tools_draft_source_definition_replayed') is True
        and proof.get('own_history_loss_and_all_ties_replayed') is True
        and proof.get('new_model_calls') == proof.get('new_container_executions') == 0,
        'read-only raw action/source/native history replay proofs required')
    _require(isinstance(inventory, dict) and inventory and all(_hash(v) for v in inventory.values())
        and len(inventory) == proof.get('raw_files_verified_unchanged')
        and digest(inventory) == proof.get('raw_inventory_sha256'), 'immutable raw inventory binding differs')
    if not allow_scripted:
        source_proofs = proof.get('source_proofs', {})
        files = source_proofs.get('files', {})
        critical = {'utopia/optimization/native_staged_author_v15.py', 'utopia/optimization/native_search_v15.py',
            'utopia/optimization/native_adaptive_search.py', 'utopia/optimization/native_factory.py',
            'utopia/system/native_kernel.py', 'scripts/run_native_staged_search_v15.py'}
        _require(source_proofs.get('status') == 'verified-exact-staged-runtime-driver-helper-source-blobs'
            and critical <= set(files) and all(_hash(p.get('actual_source_sha256'))
                and p['actual_source_sha256'] == p.get('analysis_source_sha256') for p in files.values()),
            'exact actual runtime/driver/source comparison required')
    _require(set(report.get('runs', {})) == set(ARMS), 'both distinct objective arms required')
    specs, paths, totals, seen = objective_specs(), {}, {key: 0 for key in COUNT_KEYS}, set()
    worlds = completed_scientist = 0
    for arm in ARMS:
        run = report['runs'][arm]
        _require(digest(run.get('loss_spec')) == digest(specs[arm]) and run.get('terminal') is True
            and run.get('queue_status') in {'complete', 'failed'} and run.get('consumed_native_slots') == 2
            and _hash(run.get('request_sha256')) and _hash(run.get('runtime_plan_sha256')),
            'exact objective/request/two-slot terminal arm binding differs')
        generations, observations = run.get('generations'), run.get('observations')
        _require(isinstance(generations, list) and len(generations) == 2
            and isinstance(observations, list) and len(observations) == 2, 'all two-generation attempts must remain visible')
        points, prior, incumbent = [], [], None
        for index, (generation, row) in enumerate(zip(generations, observations)):
            _require(generation.get('generation') == row.get('generation') == row.get('slot') == index
                and row.get('record_index') == index and row.get('scheduled_native_slots') == 1
                and _hash(generation.get('request_sha256'))
                and row.get('request_sha256') == generation['request_sha256']
                and generation.get('status') in {'generated', 'generation-failed'}
                and generation.get('exact_raw_tools_draft_finish_replayed') is True
                and generation.get('own_history_and_loss_prompt_replayed') is True,
                'own generation/draft/history/observation identity differs')
            counts, receipts = generation.get('counts', {}), generation.get('step_receipts')
            _require(all(_count(counts.get(key)) for key in COUNT_KEYS)
                and isinstance(receipts, list) and len(receipts) == counts['dispatch_intents']
                and counts['completed_step_receipts'] + counts['interrupted_response_unknown'] == len(receipts)
                and counts['known_designer_responses'] <= counts['completed_step_receipts']
                and counts['valid_finished_generations'] == int(generation['status'] == 'generated'),
                'known/unknown designer step accounting differs')
            if not allow_scripted:
                _require(counts['known_designer_responses'] <= counts['known_HTTP_responses']
                    <= counts['recorded_POST_attempts'] <= counts['dispatch_intents'], 'known HTTP/POST/intents accounting differs')
            finished = unknown = 0
            for step, receipt in enumerate(receipts):
                _require(receipt.get('step') == step and _hash(receipt.get('started_sha256')),
                    'ordered original step/dispatch hash required')
                if receipt.get('completed_sha256') is None:
                    _require(receipt.get('status') == 'interrupted-response-unknown', 'unknown reply was relabelled')
                    unknown += 1
                else:
                    _require(_hash(receipt['completed_sha256']), 'original completed receipt hash required')
                    finished += int(receipt.get('status') == 'finished')
            _require(finished == counts['valid_finished_generations'] and unknown == counts['interrupted_response_unknown'],
                'finish/unknown step counts differ')
            for key in COUNT_KEYS:
                totals[key] += counts[key]
            change = generation.get('authoring_change')
            if revision == 'a2':
                _require(isinstance(change, dict) and change.get('valid_explicit_finish') is (generation['status'] == 'generated')
                    and _hash(change.get('parent_document_sha256')), 'a2 explicit authoring-change proof required')
                history = generation.get('own_scalar_outcomes_received')
                expected = [{'observation_id': r['observation_id'],
                    'status': r['original_observation_status'], 'loss': r['original_observation_loss']}
                    for r in prior if r['observation_id'] is not None]
                _require(history == expected, 'own scalar feedback was omitted, altered or borrowed from another arm')
                based = generation.get('based_on_observation_id')
                _require(based is not None or not any(r['status'] == 'complete' for r in prior),
                    'measured own parent identity was omitted')
                if based is not None:
                    parent = next((r for r in prior if r['observation_id'] == based and r['status'] == 'complete'), None)
                    _require(parent is not None and parent['system_fingerprint'] == change['parent_document_sha256']
                        and parent['loss'] == min(r['loss'] for r in prior if r['status'] == 'complete'),
                        'selected parent does not join its own best measured history')
            marker = None
            if row.get('status') == 'complete':
                _require(_finite(row.get('loss')) and isinstance(row.get('observation_id'), str)
                    and row['observation_id'] not in seen and _hash(row.get('checkpoint_sha256'))
                    and _hash(row.get('system_fingerprint')), 'finite unique native observation/checkpoint required')
                if revision == 'a2':
                    _require(row.get('original_observation_status') == 'complete'
                        and row.get('original_observation_loss') == row['loss'], 'original complete observation differs')
                seen.add(row['observation_id'])
                measured = row.get('native_A_Q_R', {})
                metrics = {metric: measured.get(key) for key, metric in [('A', 'native.accepted_decisions'),
                    ('Q', 'native.accepted_peer_score_sum'), ('R', 'native.review_records')]}
                cross = row.get('cross_scores')
                _require(isinstance(cross, dict) and set(cross) == {s['id'] for s in specs.values()},
                    'both exact checkpoint cross-scores required')
                for name, spec in specs.items():
                    score = evaluate_loss(spec, [{'run_id': row['observation_id'], 'metrics': metrics}])
                    _require(cross[spec['id']] == score['loss'], 'native metric/checkpoint cross-score differs')
                    if name == arm:
                        _require(score['status'] == 'complete' and score['loss'] == row['loss'], 'own native loss differs')
                physical = row.get('native_physical_counts') or {}
                _require(_count(physical.get('scientist_responses')) and _count(physical.get('wire_requests')),
                    'completed native physical response accounting required')
                worlds += 1; completed_scientist += physical['scientist_responses']
                incumbent = row['loss'] if incumbent is None else min(incumbent, row['loss'])
                if change:
                    marker = 'same-parent' if row['system_fingerprint'] == change['parent_document_sha256'] else 'changed-system'
                    if change.get('explicit_exact_parent_retention') is True:
                        _require(marker == 'same-parent', 'explicit retention acquired a different native system')
            else:
                _require(row.get('status') in {'generation-failure', 'technical-failure'} and row.get('loss') is None,
                    'technical/null observation cannot be converted to zero or a penalty')
                _require(row.get('cross_scores') is None or isinstance(row['cross_scores'], dict)
                    and all(value is None for value in row['cross_scores'].values()),
                    'technical/null cross-scores must remain null')
            points.append({'generation': index, 'loss': row['loss'], 'best_loss_so_far': incumbent,
                'status': row['status'], 'observation_id': row['observation_id'], 'literal_relation_to_parent': marker})
            prior.append(row)
        paths[arm] = points
    designer = report.get('designer_costs', {})
    _require(designer.get('generations') == 4 and all(designer.get(key) == value for key, value in totals.items()),
        'aggregate designer cost accounting differs')
    _require(_count(report.get('physical_native_worlds')) and _count(report.get('technical_failures'))
        and report.get('physical_native_worlds') == worlds and report.get('technical_failures') == 4 - worlds
        and report.get('completed_researcher_responses') == completed_scientist
        and _count(report.get('physical_researcher_responses'))
        and report['physical_researcher_responses'] >= completed_scientist,
        'completed/partial native physical accounting differs')
    return {'revision': revision, 'source_commit': source, 'paths': paths, 'slots': 4,
        'designer_intents': totals['dispatch_intents'], 'designer_known': totals['known_designer_responses'],
        'designer_unknown': totals['interrupted_response_unknown'], 'completed_native_worlds': worlds,
        'physical_scientist_replies': report['physical_researcher_responses']}


def figure_data(a1, a2, *, expected_a1_source, expected_a2_source, allow_scripted=False):
    first = _report(a1, expected_a1_source, 'a1', allow_scripted=allow_scripted)
    second = _report(a2, expected_a2_source, 'a2', allow_scripted=allow_scripted)
    _require(first['source_commit'] != second['source_commit'], 'separate engineering revision source pins required')
    return {'classification': FIXTURE if allow_scripted else ACTUAL, 'revisions': [first, second],
        'native_paths': second['paths'], 'controlled_comparison': False, 'held_out': False}


def render(a1, a2, output, *, expected_a1_source, expected_a2_source, a1_path, a2_path, allow_scripted=False):
    if allow_scripted:
        import tempfile
        _require(Path(output).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()),
            'SCRIPTED figure files must stay in a system temporary directory')
    data = figure_data(a1, a2, expected_a1_source=expected_a1_source,
        expected_a2_source=expected_a2_source, allow_scripted=allow_scripted)
    with matplotlib.rc_context({'font.family': 'DejaVu Sans', 'font.size': 7.2, 'axes.titlesize': 8.2,
            'axes.labelsize': 7.2, 'xtick.labelsize': 7.1, 'ytick.labelsize': 7.1,
            'svg.fonttype': 'none', 'svg.hashsalt': 'native-staged-search-v15', 'pdf.fonttype': 42}):
        fig = Figure(figsize=(5.5, 4.6)); FigureCanvasAgg(fig)
        grid = fig.add_gridspec(2, 2, height_ratios=[2.1, 1.05], left=.115, right=.97,
            top=.80, bottom=.19, hspace=.70, wspace=.42)
        for index, (arm, color, title) in enumerate(zip(ARMS, ('#087e9c', '#a94779'),
                ('A  Throughput\n$L=-A$', 'B  Reviewed production\n$L=-Q+0.5R$'))):
            ax = fig.add_subplot(grid[0, index]); points = data['native_paths'][arm]
            xs = [p['generation'] for p in points]
            ys = [p['loss'] if p['loss'] is not None else math.nan for p in points]
            ax.plot(xs, ys, color=color, linewidth=1.3, zorder=2)
            best = [p['best_loss_so_far'] if p['best_loss_so_far'] is not None else math.nan for p in points]
            ax.step(xs, best, where='post', color='#43566a', linestyle='--', linewidth=.9, label='Best so far')
            for point in points:
                if point['loss'] is None:
                    ax.text(point['generation'], .90, 'Null', transform=ax.get_xaxis_transform(),
                        ha='center', va='top', color='#a23b43', fontsize=7)
                else:
                    marker = 'D' if point['literal_relation_to_parent'] == 'changed-system' else 'o'
                    ax.plot(point['generation'], point['loss'], marker=marker, markersize=5,
                        markerfacecolor=color if marker == 'D' else 'white', markeredgecolor=color, zorder=4)
                    ax.annotate(f"{point['loss']:g}", (point['generation'], point['loss']),
                        xytext=(0, 8), textcoords='offset points', ha='center', fontsize=7, color=color)
            if not any(math.isfinite(y) for y in ys):
                ax.set_yticks([]); ax.text(.5, .40, 'No completed native loss', transform=ax.transAxes, ha='center', fontsize=7)
            else:
                lo, hi = min(y for y in ys if math.isfinite(y)), max(y for y in ys if math.isfinite(y))
                margin = max((hi - lo) * .3, abs(lo) * .06, .5); ax.set_ylim(lo - margin, hi + margin)
            ax.set_xticks([0, 1], ['G0', 'G1']); ax.set_xlim(-.22, 1.22)
            ax.set_title(title, loc='left', pad=10); ax.set_ylabel('Native own loss (lower is better)')
            ax.grid(axis='y', alpha=.2); ax.spines[['top', 'right']].set_visible(False)
        table_ax = fig.add_subplot(grid[1, :]); table_ax.set_axis_off()
        table_ax.set_title('C  Physical accounting - separately budgeted engineering revisions', loc='left', pad=9)
        keys = ('slots', 'designer_intents', 'designer_known', 'designer_unknown', 'completed_native_worlds', 'physical_scientist_replies')
        table = table_ax.table(cellText=[[str(row[k]) for k in keys] for row in data['revisions']],
            rowLabels=['a1', 'a2'], colLabels=['Charged\nslots', 'Designer\nintents', 'Known\nreplies',
                'Unknown\nreplies', 'Completed\nworlds', 'Scientist\nreplies'], cellLoc='center',
            rowLoc='center', bbox=(0, .08, 1, .85))
        table.auto_set_font_size(False); table.set_fontsize(7)
        for (row, _), cell in table.get_celld().items():
            cell.set_edgecolor('#d1dbe2'); cell.set_linewidth(.6)
            cell.set_facecolor('#edf2f5' if row == 0 else 'white')
        fig.suptitle('SCRIPTED CONTRACT FIXTURE - NOT NATIVE RESULTS' if allow_scripted else
            'Staged institutional authoring: native feedback and accounting', fontsize=9.4, fontweight='bold', y=.97)
        fig.text(.5, .92, 'a2 native paths; axes use different loss scales. One development seed.', ha='center', fontsize=7.1, color='#43566a')
        relations = {p['literal_relation_to_parent'] for points in data['native_paths'].values() for p in points if p['loss'] is not None}
        symbols = 'Open circle: same parent SystemSpec.'
        if 'changed-system' in relations:
            symbols += ' Diamond: literally changed SystemSpec (not novelty).'
        fig.text(.5, .115, symbols + '\nDashed: best own loss. Null endpoints are not zero. Retention is not invented code.\n'
            'Separate source/transport revisions and four-slot budgets; not a controlled comparison.\n'
            'Scientist replies include known partial-world replies. No held-out or scientific-benefit claim.',
            ha='center', va='center', fontsize=6.8, color='#43566a', linespacing=1.5)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer(); frame = fig.bbox
        for artist in fig.findobj(match=Text):
            if artist.get_visible() and artist.get_text().strip():
                box = artist.get_window_extent(renderer)
                _require(box.x0 >= frame.x0 - 1 and box.y0 >= frame.y0 - 1
                    and box.x1 <= frame.x1 + 1 and box.y1 <= frame.y1 + 1,
                    'figure text extends beyond page: ' + artist.get_text())
        output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
        files = {}
        for suffix in ('.png', '.svg', '.pdf'):
            path = output.with_suffix(suffix)
            metadata = {'Date': None} if suffix == '.svg' else {'CreationDate': None, 'ModDate': None} if suffix == '.pdf' else None
            fig.savefig(path, dpi=220, metadata=metadata); files[path.name] = file_sha256(path)
    manifest = {'schema': 'scienceutopia.native-staged-search-figure.v15', 'classification': data['classification'],
        'audits': {revision: {'source_commit': report['source_commit'], 'content_sha256': report['content_sha256'],
            'file_sha256': file_sha256(path)} for revision, report, path in [('a1', a1, a1_path), ('a2', a2, a2_path)]},
        'generator_sha256': file_sha256(Path(__file__)), 'width_inches': 5.5, 'height_inches': 4.6,
        'files': files, 'data': data}
    manifest['content_sha256'] = digest(manifest)
    write_json_atomic(output.with_suffix('.manifest.json'), manifest, sort_keys=True, allow_nan=False)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('a1', 'a2', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--expected-a1-source', required=True); parser.add_argument('--expected-a2-source', required=True)
    parser.add_argument('--allow-scripted', action='store_true')
    args = parser.parse_args()
    if args.allow_scripted:
        import tempfile
        _require(args.output.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()),
            'SCRIPTED figure files must stay in a system temporary directory')
    result = render(json.loads(args.a1.read_text()), json.loads(args.a2.read_text()), args.output,
        expected_a1_source=args.expected_a1_source, expected_a2_source=args.expected_a2_source,
        a1_path=args.a1, a2_path=args.a2, allow_scripted=args.allow_scripted)
    print(json.dumps({'content_sha256': result['content_sha256'], 'files': result['files']}, sort_keys=True))


if __name__ == '__main__':
    main()
