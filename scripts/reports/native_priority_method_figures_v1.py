"""Plot the exact closed finite method paths, not new scientific observations."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from scripts.reports.native_priority_method_readout_v1 import METHODS, OBJECTIVES, SCHEMA as READOUT
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-priority-method-figures.v1'


def derive(report, closed):
    checked(report); checked(closed)
    if (report['schema'] != READOUT
            or closed['schema'] != 'scienceutopia.native-priority-method-comparison-closed.v1'
            or report['content_sha256'] != closed['readout_content_sha256']
            or report['scientific_source_commit'] != closed['source_commits']['scientific']
            or report['frozen_selection_content_sha256'] != closed['frozen_selection_content_sha256']
            or report['coverage'] != closed['coverage']
            or report['coverage'] != {'complete_own_slots': 24, 'declared_own_slots': 24,
                'execution_or_measurement_nulls': 0, 'generation_nulls': 0, 'physical_worlds': 27}
            or any(v != 0 for v in closed['actual_exit_codes'].values())
            or report['selection_changed'] or report['held_out_evaluation']
            or report['new_model_calls'] or report['new_code_executions']):
        raise ValueError('literal complete original paired closure and readout required')
    expected = {(m, h, o, g) for m in METHODS for h in range(2) for o in OBJECTIVES for g in range(2)}
    slots = report['slots']
    identities = [(r['method'], r['replication'], r['objective'], r['generation']) for r in slots]
    if len(slots) != 24 or set(identities) != expected:
        raise ValueError('all24 original compound slots required')
    paths = []
    for method in METHODS:
        for objective in OBJECTIVES:
            for history in range(2):
                key = '/'.join((method, str(history), objective))
                selected = [s for s in report['selected'] if (s['method'], s['replication'], s['objective'])
                            == (method, history, objective)]
                if len(selected) != 1: raise ValueError('one literal own-only selection required')
                reference = selected[0]['reference_loss']; best = None; points = []
                rows = sorted((r for r in slots if (r['method'], r['replication'], r['objective'])
                    == (method, history, objective)), key=lambda r: r['generation'])
                for row, original in zip(rows, report['paths'][key], strict=True):
                    if row['status'] != 'complete' or row['loss'] != row['cross_scores'][objective]:
                        raise ValueError('complete assigned original loss required, not imputed nulls')
                    best = row['loss'] if best is None else min(best, row['loss'])
                    point = {'cell_id': row['cell_id'], 'generation': row['generation'], 'status': row['status'],
                        'observed_loss': row['loss'], 'best_own_loss': best, 'reference_loss': reference,
                        'best_known_including_visible_parent': min(reference, best)}
                    if original != point: raise ValueError('literal original path differs')
                    points.append({**point, 'observed_minus_reference': row['loss'] - reference,
                        'best_own_minus_reference': best - reference})
                if len(points) != 2 or selected[0]['loss'] != best:
                    raise ValueError('exact two-point path and frozen own minimum required')
                paths.append({'method': method, 'objective': objective, 'history': history, 'points': points})
    return {'schema': SCHEMA, 'original_closed_content_sha256': closed['content_sha256'],
        'original_readout_content_sha256': report['content_sha256'], 'paths': clone(paths),
        'scope': 'One reused researcher condition, two coupled optimizer histories per cell. '
            'Original context-v1 author-phase confound remains. This is not an isolated method comparison, '
            'independent-population interval, corrected-author benefit or useful invention.',
        'new_model_calls': 0, 'new_code_executions': 0, 'new_native_worlds': 0,
        'selection_changed': False, 'held_out_evaluation': False, 'publication_ready': False}


def render(data, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    colors = ['#203f65', '#12858a']; markers = ['o', 'D']
    names = ['Uniform priorities', 'Adaptive priorities', 'Free code / graph']
    with plt.rc_context({'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.hashsalt': SCHEMA}):
        fig, axes = plt.subplots(2, 3, figsize=(6.8, 4.8))
        for row, objective in enumerate(OBJECTIVES):
            for col, method in enumerate(METHODS):
                ax = axes[row, col]; ax.axhline(0, color='#8c969f', ls='--', lw=1)
                for history in range(2):
                    path = next(p for p in data['paths'] if (p['method'], p['objective'], p['history'])
                                == (method, objective, history))['points']
                    x = [p['generation'] + 1 + (-.035 if history == 0 else .035) for p in path]
                    ax.plot(x, [p['best_own_minus_reference'] for p in path], color=colors[history], lw=1.6)
                    ax.scatter(x, [p['observed_minus_reference'] for p in path], color=colors[history],
                        marker=markers[history], s=26, facecolors='white', zorder=4, linewidths=1.2)
                ax.set(xlim=(.72, 2.28), xticks=[1, 2], ylim=(-.16, 1.16) if row == 0 else (-.35, 3.35))
                ax.grid(axis='y', color='#e5e9ed', lw=.6)
                if row == 0: ax.set_title(names[col], fontsize=9, pad=8)
                else: ax.set_xlabel('Own proposal', labelpad=4)
                if col == 0:
                    ax.set_ylabel(('U target' if row == 0 else 'C target') + '\nLoss minus visible reference')
                else: ax.tick_params(labelleft=False)
        legend = [Line2D([], [], color=colors[h], marker=markers[h], markerfacecolor='white',
                    label='History ' + str(h)) for h in range(2)]
        legend += [Line2D([], [], color='#526171', marker='o', markerfacecolor='white', lw=0,
                       label='Observed loss'), Line2D([], [], color='#526171', lw=1.6, label='Best own loss'),
                   Line2D([], [], color='#8c969f', ls='--', label='Visible reference (zero gap)')]
        fig.legend(handles=legend, loc='lower center', bbox_to_anchor=(.52, .14), ncol=3,
                   frameon=False, fontsize=7)
        fig.text(.05, .09, 'Lower is better. No submitted proposal improves the visible reference.', fontsize=7)
        fig.text(.05, .055, 'Two coupled histories; one reused researcher condition. No uncertainty intervals.', fontsize=7)
        fig.text(.05, .02, 'Original author-interface confound remains; this is not an isolated method effect.', fontsize=7)
        fig.subplots_adjust(left=.12, right=.98, top=.91, bottom=.33, hspace=.40, wspace=.18)
        for extension in ('png', 'svg'):
            fig.savefig(output / ('method-loss-paths.' + extension), dpi=240,
                metadata={'Date': None} if extension == 'svg' else None)
        plt.close(fig)


def export(args):
    out = args.output.resolve(); source = pinned_revision(ROOT)
    if out.exists() or out.is_relative_to(ROOT): raise ValueError('fresh external figure output required')
    raw = args.report.read_bytes(); raw = gzip.decompress(raw) if args.report.suffix == '.gz' else raw
    closed = checked(json.loads(args.closed.read_text()))
    if hashlib.sha256(raw).hexdigest() != closed['paired_matching_files']['readouts']['report.json']:
        raise ValueError('exact original readout bytes required')
    inputs = {str(p.resolve()): file_sha256(p) for p in (args.closed, args.report)}
    data = {**derive(checked(json.loads(raw)), closed), 'analysis_source_commit': source, 'inputs': inputs}
    out.mkdir(parents=True); save(out / 'report.json', data); render(data, out)
    if pinned_revision(ROOT) != source or inputs != {p: file_sha256(p) for p in inputs}:
        raise ValueError('source/evidence changed during figure export')
    save(out / 'manifest.json', {'schema': SCHEMA + '.manifest', 'analysis_source_commit': source,
        'inputs': inputs, 'files': {p.name: file_sha256(p) for p in sorted(out.iterdir())},
        'new_model_calls': 0, 'new_native_worlds': 0, 'selection_changed': False,
        'visual_review_complete': False, 'publication_ready': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('closed', 'report', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__': main()
