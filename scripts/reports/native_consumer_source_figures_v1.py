"""Literal matched-search plot data; render only after original paired closure.

No inference, generated-code execution, raw-world replay or changed selection.
Figures are outputs of measured paths, never an objective or admission gate.
"""
import argparse
import csv
import json
from pathlib import Path

from scripts.reports.native_consumer_source_comparison_v1 import ARMS, OBJECTIVES, REFERENCES, SCORES
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_resource_cost import METRIC, UNCOLLECTED_METRIC
from utopia.system.design_patch import clone
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-consumer-source-figures.v1'


def derive(report):
    """All references/slots, own paths, and requested costs stay literal."""
    checked(report)
    interpretation = report['interpretation']
    if (report['schema'] != 'scienceutopia.native-consumer-source-comparison.v1.readout'
            or report['score_order'] != SCORES or report['consumed_own_slots'] != 8
            or interpretation['new_model_calls'] or interpretation['new_code_executions']
            or interpretation['loss_or_selection_changed'] or interpretation['held_out_evaluation']
            or interpretation['independent_optimizer_replications']
            or interpretation['equal_measured_compute_claimed']):
        raise ValueError('literal finite matched original readout required')
    references, slots = report['references'], report['slots']
    expected = {(a, o, g) for a in ARMS for o in OBJECTIVES for g in range(2)}
    if ([r['label'] for r in references] != REFERENCES
            or [r['optimizer_visible'] for r in references] != [True, True, False]
            or len(slots) != 8 or [r['slot_index'] for r in slots] != list(range(8))
            or {(r['arm'], r['objective'], r['generation']) for r in slots} != expected
            or report['selection']['baseline_fallback']):
        raise ValueError('all original slots and reference visibility required')
    paths = {}
    for arm in ARMS:
        for objective in OBJECTIVES:
            key = arm + '::' + objective
            path = report['loss_paths'][key]
            rows = sorted((r for r in slots if r['arm'] == arm and r['objective'] == objective),
                          key=lambda r: r['generation'])
            own = None
            known = min(r['cross_scores'][objective] for r in references if r['optimizer_visible'])
            for generation, (point, row) in enumerate(zip(path, rows)):
                if row['status'] == 'complete':
                    own = row['loss'] if own is None else min(own, row['loss'])
                    known = min(known, row['loss'])
                if (point != {'generation': generation, 'status': row['status'], 'observed_loss': row['loss'],
                        'best_own_loss': own, 'best_known_loss_including_visible_references': known}
                        or (row['status'] == 'complete') != (row['loss'] is not None)):
                    raise ValueError('literal original path differs; no new winner or null imputation')
            if len(path) != 2 or report['selection']['selected'][key]['loss'] != own:
                raise ValueError('literal own-only selection and two points required')
            paths[key] = clone(path)
    values = []
    for row in [*references, *slots]:
        collected, unpaid = [row['metrics'][key]['value'] for key in (METRIC, UNCOLLECTED_METRIC)]
        requested = None if collected is None or unpaid is None else collected + unpaid
        if row['requested_activity_cost'] != requested:
            raise ValueError('original requested cost does not reconcile')
        own = 'slot_index' in row
        values.append({'kind': 'own-slot' if own else 'reference',
            'label': (row['arm'] + ' / ' + row['objective'] + ' / g' + str(row['generation'])) if own else row['label'],
            'physical_job': row['physical_job'], 'status': row['status'],
            'arm': row.get('arm'), 'objective': row.get('objective'), 'generation': row.get('generation'),
            'optimizer_visible_reference': None if own else row['optimizer_visible'],
            **clone(row['cross_scores']), 'collected_cost': collected, 'unpaid_cost': unpaid,
            'requested_cost': requested, 'institutional_work_events': row['institutional_work_events'],
            'graph_from_parent': clone(row.get('graph_from_parent'))})
    return {'schema': SCHEMA, 'scientific_source_commit': report['scientific_source_commit'],
        'original_readout_source_commit': report['analysis_source_commit'],
        'original_readout_content_sha256': report['content_sha256'],
        'loss_specs': clone(report['loss_specs']), 'paths': paths, 'outcomes': values,
        'selection': clone(report['selection']), 'comparisons': clone(report['comparisons']),
        'literal_consumers_minus_interface_own_best': clone(report['literal_consumers_minus_interface_own_best']),
        'scope': 'One openly reused development condition; paired information packages, not independent '
            'optimizer replications or isolated comprehension. Every slot stays visible. Lower assigned loss '
            'is better under its declared preference, not scientific truth. Known terminal rule is withheld '
            'from both authors, not part of the reference-inclusive incumbent unless recovered by an own submission.',
        'unknown_is_zero': False, 'unpaid_or_activity_veto': False, 'requested_cost_is_optimized': False,
        'loss_or_selection_changed': False, 'new_model_calls': 0, 'new_code_executions': 0,
        'new_native_worlds': 0, 'independent_optimizer_replications': False,
        'held_out_evaluation': False, 'publication_ready': False}


def render(data, output):
    """Recorded path points only; nulls are labeled and never plotted as zero."""
    import math
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    colors = dict(zip(ARMS, ('#147d92', '#9a4c87')))
    names = dict(zip(ARMS, ('Interface only', 'Literal consumers')))
    refs = [r for r in data['outcomes'] if r['kind'] == 'reference']
    with plt.rc_context({'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.hashsalt': SCHEMA}):
        # Native manuscript width keeps typography legible without shrinking
        # a wide dashboard. A null annotation is screen-positioned, not a loss.
        fig, axes = plt.subplots(1, 2, figsize=(6.8, 4.8))
        for ax, objective in zip(axes, OBJECTIVES):
            for row, color, style in zip(refs, ('#92a1b0', '#a37d3a', '#424b60'), ('--', '--', '-.')):
                ax.axhline(row[objective], color=color, ls=style, lw=1)
            for arm in ARMS:
                path = data['paths'][arm + '::' + objective]
                offset = -.035 if arm == ARMS[0] else .035
                x = [p['generation'] + offset for p in path]
                y = [math.nan if p['best_own_loss'] is None else p['best_own_loss'] for p in path]
                ax.plot(x, y, color=colors[arm], lw=1.5)
                ax.plot(x, [p['best_known_loss_including_visible_references'] for p in path],
                        color=colors[arm], ls=':', lw=1)
                for point, position in zip(path, x):
                    if point['observed_loss'] is None:
                        ax.text(position, .12 if arm == ARMS[0] else .20, names[arm] + ': null',
                            transform=ax.get_xaxis_transform(), ha='center', color=colors[arm], fontsize=7,
                            bbox={'facecolor': 'white', 'edgecolor': 'none', 'pad': 2})
                    else:
                        ax.scatter(position, point['observed_loss'], s=24, color=colors[arm], zorder=3)
            ax.set(title={'content-utility': 'Content utility',
                          'resource-aware-content': 'Resource-aware content'}[objective],
                   xticks=[0, 1], xlim=(-.3, 1.3), xlabel='Own proposal generation',
                   ylabel='Declared loss (lower is better)')
            ax.grid(axis='y', color='#e9edf1', lw=.6)
        handles = [Line2D([], [], color=colors[a], label=names[a]) for a in ARMS]
        handles += [Line2D([], [], color='#536474', marker='o', lw=0, label='Observed own loss'),
            Line2D([], [], color='#536474', lw=1.5, label='Best own loss'),
            Line2D([], [], color='#536474', ls=':', label='Best known incl. visible parents'),
            Line2D([], [], color='#92a1b0', ls='--', label='Visible core reference'),
            Line2D([], [], color='#a37d3a', ls='--', label='Visible related reference'),
            Line2D([], [], color='#424b60', ls='-.', label='Known terminal rule (withheld)')]
        fig.suptitle('Objective-conditioned institution search', fontsize=11, y=.97)
        fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .105), ncol=2,
                   frameon=False, fontsize=7)
        fig.text(.04, .055, 'One reused development condition; no independent optimizer replications.', fontsize=7)
        fig.text(.04, .025, 'Information packages differ; measured compute need not match.', fontsize=7)
        fig.subplots_adjust(left=.10, right=.98, top=.85, bottom=.40, wspace=.40)
        for ext in ('png', 'svg'):
            fig.savefig(output / ('matched-loss-paths.' + ext), dpi=220,
                        metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)
        rows = data['outcomes']; number = lambda x: 'unknown' if x is None else f'{x:.6g}'
        cells = [[r['label'] + (' [' + r['status'] + ']' if r['status'] != 'complete' else ''),
            *[number(r[k]) for k in SCORES], number(r['collected_cost']), number(r['unpaid_cost']),
            number(r['requested_cost'])] for r in rows]
        fig, ax = plt.subplots(figsize=(12.0, 5.8)); ax.axis('off')
        table = ax.table(cellText=cells,
            colLabels=['Original reference / every own slot', 'T loss', 'U loss', 'C loss', 'Collected K', 'Unpaid', 'Requested'],
            colWidths=[.52, .08, .08, .08, .08, .08, .08], cellLoc='left', bbox=(0, .15, 1, .78))
        table.auto_set_font_size(False); table.set_fontsize(6.7)
        for (i, j), cell in table.get_celld().items():
            cell.set_edgecolor('#d5dfe7'); cell.set_linewidth(.45)
            if i == 0:
                cell.set_facecolor('#e9f0f5')
            elif 'unknown' == cell.get_text().get_text():
                cell.set_facecolor('#efefef')
        fig.suptitle('Literal cross-objective outcomes and original resource accounting', fontsize=11, y=.97)
        fig.text(.025, .055, 'All 8 slots remain, including nulls. Unknown is not zero. Requested = collected + unpaid; '
            'requested cost is diagnostic, not an optimized loss.\nKnown terminal hand control is comparison-only. '
            'Neither resource accounting nor an edited graph by itself establishes better science.', fontsize=7)
        fig.subplots_adjust(left=.025, right=.985, top=.92, bottom=.10)
        for ext in ('png', 'svg'):
            fig.savefig(output / ('matched-outcomes.' + ext), dpi=220,
                        metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def closed_readout(readouts, frozen):
    """Require both actual completed exports and their original closure hashes."""
    source = pinned_revision(frozen)
    read = lambda path: checked(json.loads(path.read_text()))
    start, end = read(readouts / 'started.json'), read(readouts / 'ended.json')
    if (start['schema'] != 'scienceutopia.native-consumer-source-comparison.v1.readout.finish'
            or start['analysis_source_commit'] != source or end['status'] != 'closed'
            or end['steps'] != [{'stage': 'report-1', 'exit_code': 0}, {'stage': 'report-2', 'exit_code': 0}]
            or end['new_model_calls'] or end['new_native_worlds']):
        raise ValueError('original normally closed paired readout continuation required')
    names = ('report.json', 'slots.csv', 'manifest.json')
    paths = [readouts / 'started.json', readouts / 'ended.json']
    for i in (1, 2):
        directory = readouts / ('report-' + str(i))
        if sorted(p.name for p in directory.iterdir()) != sorted(names):
            raise ValueError('exact complete original readout file set required')
        manifest = read(directory / 'manifest.json')
        if (any(file_sha256(directory / name) != value for name, value in manifest['files'].items())
                or {name: file_sha256(directory / name) for name in names} != end['report_files']):
            raise ValueError('literal paired readout bytes differ from closure')
        paths.extend(directory / name for name in names)
    report = read(readouts / 'report-1/report.json')
    if (report['analysis_source_commit'] != source
            or report['scientific_source_commit'] != start['scientific_source_commit']):
        raise ValueError('literal original reader/scientific source identities differ')
    return report, {str(p): file_sha256(p) for p in paths}


def export(args):
    readouts, frozen, out = args.readouts.resolve(), args.frozen_reader.resolve(), args.output.resolve()
    source = pinned_revision(ROOT)
    if out.exists() or any(out.is_relative_to(p) for p in (ROOT, frozen, readouts)):
        raise ValueError('fresh interpretation outside original readouts and both sources required')
    report, hashes = closed_readout(readouts, frozen)
    data = {**derive(report), 'analysis_source_commit': source, 'inputs': hashes}
    if hashes != {p: file_sha256(Path(p)) for p in hashes}:
        raise ValueError('original readout inputs changed')
    out.mkdir(parents=True); save(out / 'report.json', data)
    fields = ['kind', 'label', 'physical_job', 'status', 'arm', 'objective', 'generation',
              'optimizer_visible_reference', *SCORES, 'collected_cost', 'unpaid_cost', 'requested_cost',
              'institutional_work_events']
    with (out / 'outcomes.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        writer.writerows({k: r[k] for k in fields} for r in data['outcomes'])
    if args.render:
        render(data, out)
    save(out / 'manifest.json', {'schema': SCHEMA + '.export', 'analysis_source_commit': source,
        'inputs': hashes, 'adapter_file_sha256': file_sha256(Path(__file__)),
        'files': {p.name: file_sha256(p) for p in sorted(out.iterdir())},
        'new_model_calls': 0, 'new_native_worlds': 0, 'visual_review_complete': False})
    if hashes != {p: file_sha256(Path(p)) for p in hashes} or pinned_revision(ROOT) != source:
        raise ValueError('original inputs or interpretation source changed during export')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('readouts', 'frozen-reader', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--render', action='store_true')
    export(parser.parse_args())


if __name__ == '__main__':
    main()
