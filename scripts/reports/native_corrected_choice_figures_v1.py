"""Exact four-step loss paths/both endpoint scopes; render only on explicit request.

No model, native world, source execution, selection or imputed losses. A pure
projection is not original-source provenance: export requires the complete
normally closed original paired cold/cost/readout chain.
"""
import argparse
import csv
import fcntl
import math
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_priority_method_readout_v1 import METHODS, OBJECTIVES, CORRECTED_SCHEMA, cell_id
from scripts.run_native_priority_fixed_evaluation_v1 import origin_evidence, evidence_files, read
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-corrected-choice-figures.v1'


def finite(value): return type(value) in (int, float) and math.isfinite(value)


def derive(report):
    checked(report)
    if (report['schema'] != CORRECTED_SCHEMA or report['selection_changed'] or report['held_out_evaluation']
            or report['new_model_calls'] or report['new_code_executions'] or len(report['references']) != 3):
        raise ValueError('literal corrected closed-development readout required')
    slots = report['slots']; expected = {(m, 0, o, g) for m in METHODS for o in OBJECTIVES for g in range(4)}
    if (len(slots) != 24 or {(r['method'], r['replication'], r['objective'], r['generation']) for r in slots} != expected
            or any(type(r['replication']) is not int or type(r['generation']) is not int or r['cell_id'] != cell_id(r) for r in slots)
            or len({r['cell_id'] for r in slots}) != 24):
        raise ValueError('all24 exact four-step compound cells required, including nulls')
    complete = sum(r['status'] == 'complete' for r in slots)
    generation_null = sum(r['status'] == 'generation-null' for r in slots)
    if report['coverage'] != {'complete_own_slots': complete, 'declared_own_slots': 24,
            'execution_or_measurement_nulls': 24 - complete - generation_null, 'generation_nulls': generation_null,
            'physical_worlds': 27 - generation_null}:
        raise ValueError('literal completed/generation/execution-null coverage required')
    visible = [r for r in report['references'] if r['visible_parent']]
    if len(visible) != 2 or any(r['status'] != 'complete' for r in report['references']):
        raise ValueError('three complete references and two literal visible warm parents required')
    paths = []; counts = {'better': 0, 'tie': 0, 'worse': 0, 'unavailable': 0}
    endpoints = report['selected']; own_endpoints = report['own_only_selected']
    keys = {(m, 0, o) for m in METHODS for o in OBJECTIVES}
    for bank in (endpoints, own_endpoints):
        if len(bank) != 6 or {(r['method'], r['replication'], r['objective']) for r in bank} != keys:
            raise ValueError('both six-policy endpoint scopes required')
    for method in METHODS:
        for objective in OBJECTIVES:
            ref = min(visible, key=lambda r: r['cross_scores'][objective]); reference = ref['cross_scores'][objective]
            if not finite(reference): raise ValueError('finite actually measured warm reference required')
            rows = sorted((r for r in slots if (r['method'], r['objective']) == (method, objective)), key=lambda r: r['generation'])
            key = '/'.join((method, '0', objective)); recorded = report['paths'][key]
            best = None; chosen = None; points = []
            for row, original in zip(rows, recorded, strict=True):
                value = row['loss']
                if row['status'] == 'complete':
                    if not finite(value) or row['cross_scores'][objective] != value: raise ValueError('finite assigned observed loss required')
                    if best is None or value < best: best, chosen = value, row
                    counts['better' if value < reference else 'worse' if value > reference else 'tie'] += 1
                elif row['status'] not in ('failed', 'generation-null') or value is not None:
                    raise ValueError('technical null is unavailable, never an imputed penalty')
                else: counts['unavailable'] += 1
                known = reference if best is None else min(reference, best)
                point = {'cell_id': row['cell_id'], 'generation': row['generation'], 'status': row['status'],
                    'observed_loss': value, 'best_own_loss': best, 'reference_loss': reference,
                    'best_known_including_visible_parent': known}
                if original != point: raise ValueError('literal four-step observed/best-own/best-known path differs')
                points.append({**point, 'observed_minus_reference': None if value is None else value - reference,
                    'best_own_minus_reference': None if best is None else best - reference,
                    'best_known_minus_reference': known - reference})
            if len(points) != 4: raise ValueError('exact four points including nulls required')
            primary = next(r for r in endpoints if (r['method'], r['objective']) == (method, objective))
            own = next(r for r in own_endpoints if (r['method'], r['objective']) == (method, objective))
            winner = chosen if best is not None and best < reference else ref
            origin = 'own' if winner is chosen else 'reference'
            completed = [r for r in rows if r['status'] == 'complete']
            known = points[-1]['best_known_including_visible_parent']
            own_ties = [r['suggestion_id'] for r in completed if r['loss'] == best]
            known_ties = [r['suggestion_id'] for r in visible if r['cross_scores'][objective] == known]
            known_ties += [r['suggestion_id'] for r in completed if r['loss'] == known]
            if (own['loss'] != best or own['cell_id'] != (chosen['cell_id'] if chosen else None)
                    or own['suggestion_id'] != (chosen['suggestion_id'] if chosen else None)
                    or own['reference_loss'] != reference or primary['reference_loss'] != reference
                    or own['literal_system_sha256'] != (chosen['literal_system_sha256'] if chosen else None)
                    or primary['literal_system_sha256'] != winner['literal_system_sha256']
                    or own['all_tied_ids'] != own_ties or primary['all_tied_ids'] != known_ties
                    or own['completed_submissions'] != len(completed) or primary['completed_submissions'] != len(completed)
                    or primary['loss'] != known
                    or primary['selected_origin'] != origin or primary['suggestion_id'] != winner['suggestion_id']
                    or primary['cell_id'] != (chosen['cell_id'] if origin == 'own' else None)):
                raise ValueError('frozen endpoint loss/origin/tie rule differs; no reference relabeling')
            paths.append({'method': method, 'objective': objective, 'history': 0,
                'points': points, 'primary_endpoint': clone(primary), 'own_only_endpoint': clone(own)})
    return {'schema': SCHEMA, 'scientific_source_commit': report['scientific_source_commit'],
        'original_readout_content_sha256': report['content_sha256'],
        'frozen_selection_content_sha256': report['frozen_selection_content_sha256'],
        'paths': paths, 'coverage': clone(report['coverage']), 'own_vs_reference_counts': counts,
        'new_model_calls': 0, 'new_native_worlds': 0, 'selection_changed': False, 'publication_ready': False,
        'scope': 'All24 attempts/six four-step histories; observed-own, best-own and best-known stay separate. '
            'Nulls have no observed loss; returned references are not own inventions. One reused development '
            'world and one history per cell, no independent-population uncertainty or isolated method effect.'}


def render(data, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    names = ['Uniform priorities', 'Adaptive initial choices', 'Free code / graph']
    with plt.rc_context({'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False, 'svg.hashsalt': SCHEMA}):
        fig, axes = plt.subplots(2, 3, figsize=(8, 5.1))
        for y, objective in enumerate(OBJECTIVES):
            group = [p for p in data['paths'] if p['objective'] == objective]
            values = [0] + [v for p in group for point in p['points'] for v in
                (point['observed_minus_reference'], point['best_own_minus_reference'], point['best_known_minus_reference']) if v is not None]
            lo, hi = min(values), max(values); margin = max(.25, (hi - lo) * .12)
            for x, method in enumerate(METHODS):
                ax = axes[y, x]; path = next(p for p in group if p['method'] == method); points = path['points']
                xs = [p['generation'] + 1 for p in points]
                ax.axhline(0, color='#89949d', ls=':', lw=1)
                ax.plot(xs, [p['best_own_minus_reference'] for p in points], color='#007f86', lw=1.8)
                ax.plot([0, *xs], [0, *[p['best_known_minus_reference'] for p in points]], color='#ae5a13', ls='--', lw=1.3)
                actual = [(i, p['observed_minus_reference']) for i, p in zip(xs, points) if p['observed_minus_reference'] is not None]
                if actual: ax.scatter(*zip(*actual), marker='o', s=28, facecolors='white', edgecolors='#213c64', linewidths=1.3, zorder=4)
                missing = [i for i, p in zip(xs, points) if p['observed_minus_reference'] is None]
                if missing: ax.scatter(missing, [1.025] * len(missing), transform=ax.get_xaxis_transform(), marker='x', color='#aa3349', clip_on=False, s=24)
                ax.set(xlim=(-.12, 4.2), xticks=range(5), ylim=(lo - margin, hi + margin))
                ax.grid(axis='y', color='#e9edf0', lw=.65)
                if y == 0: ax.set_title(names[x], fontsize=9, pad=8)
                else: ax.set_xlabel('Own proposal (0 = warm start)', labelpad=12)
                if x == 0: ax.set_ylabel(('U target' if y == 0 else 'C target') + '\nLoss minus visible reference')
                else: ax.tick_params(labelleft=False)
        handles = [Line2D([], [], color='#213c64', marker='o', markerfacecolor='white', lw=0, label='Observed own'),
            Line2D([], [], color='#007f86', lw=1.8, label='Best own'),
            Line2D([], [], color='#ae5a13', ls='--', label='Best known (incl. warm parent)'),
            Line2D([], [], color='#aa3349', marker='x', lw=0, label='Technical null (axis strip, not zero loss)')]
        fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.52, .10), ncol=2, frameon=False, fontsize=7)
        c = data['own_vs_reference_counts']
        fig.text(.08, .06, f"All24 own attempts: {c['better']} better / {c['tie']} tied / {c['worse']} worse / {c['unavailable']} unavailable. Lower is better.", fontsize=7)
        fig.text(.08, .025, 'One reused development world; one coupled four-step history per cell. No population uncertainty intervals.', fontsize=7)
        fig.subplots_adjust(left=.12, right=.98, top=.91, bottom=.32, hspace=.4, wspace=.18)
        for extension in ('png', 'svg'):
            fig.savefig(output / ('corrected-choice-loss-paths.' + extension), dpi=220,
                metadata={'Date': None} if extension == 'svg' else None)
        plt.close(fig)


def export(args):
    origin = {key: str(getattr(args, 'origin_' + key).resolve()) for key in ('run', 'source', 'analysis', 'readouts')}
    out = args.output.resolve()
    if out.exists() or any(out.is_relative_to(root) for root in (ROOT.resolve(), *map(Path, origin.values()))):
        raise ValueError('fresh figure output outside all reader/scientific evidence sources required')
    reader = pinned_revision(ROOT); raw = Path(origin['run'])
    origin['source_commit'] = read(raw / 'plan.json')['source_commit']
    origin['input_files'] = {str(p): file_sha256(p) for p in evidence_files(origin)}
    with (raw / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_SH | fcntl.LOCK_NB)
        _, _, _ = origin_evidence(origin, profile='corrected-choice-v1'); before = _inventory(raw)
        data = derive(read(Path(origin['readouts']) / 'report-1/report.json'))
        data.update(analysis_source_commit=reader, input_files=origin['input_files'])
        out.mkdir(parents=True); save(out / 'report.json', data)
        fields = ['method', 'objective', 'history', 'cell_id', 'generation', 'status', 'observed_loss',
            'best_own_loss', 'reference_loss', 'best_known_including_visible_parent', 'observed_minus_reference',
            'best_own_minus_reference', 'best_known_minus_reference']
        with (out / 'points.csv').open('x', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
            for path in data['paths']:
                for point in path['points']:
                    writer.writerow({**{k: path[k] for k in ('method', 'objective', 'history')}, **point})
        if args.render: render(data, out)
        if (before != _inventory(raw) or reader != pinned_revision(ROOT)
                or any(file_sha256(p) != sha for p, sha in origin['input_files'].items())):
            raise ValueError('original evidence or reader source changed during figure export')
        save(out / 'manifest.json', {'schema': SCHEMA + '.export', 'analysis_source_commit': reader,
            'input_files': origin['input_files'], 'render_requested': args.render, 'visual_review_complete': False,
            'files': {p.name: file_sha256(p) for p in sorted(out.iterdir())}, 'new_model_calls': 0,
            'new_native_worlds': 0, 'selection_changed': False, 'publication_ready': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'source', 'analysis', 'readouts'): parser.add_argument('--origin-' + key, type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--render', action='store_true')
    export(parser.parse_args())
