"""Interpret a normally closed paired readout; optional print figure, no inference."""
import argparse
import csv
import json
from pathlib import Path

from scripts.reports.native_terminal_cost_semantics_v1 import describe
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-terminal-cost-interpretation.v1'


def derive(report):
    checked(report)
    if (report['schema'] != 'scienceutopia.native-terminal-cost-pilot-readout.v1'
            or [w['condition'] for w in report['worlds']] != ['strong-related-reference', 'terminal-consolidation']
            or report['new_model_calls'] != 0 or report['new_code_executions'] != 0
            or report['automatic_invention'] or report['held_out_evaluation']):
        raise ValueError('literal two-control original readout scope required')
    result = describe(report['worlds'], coefficient=0.1)
    if result['status'] != 'measured-diagnostic':
        raise ValueError('completed original readout unexpectedly lacks cost/loss measurements')
    annual = []
    for world in report['worlds']:
        values = world['annual_resource_categories']
        if [row['year'] for row in values] != [1, 2, 3, 4]:
            raise ValueError('four literal measured original annual ledgers required')
        annual.append({'condition': world['condition'], 'years': [
            {key: row[key] for key in ('year', 'collected_activity_cost', 'uncollected_activity_cost',
                'requested_activity_cost', 'closing_active_authors', 'closing_resources')}
            for row in values]})
    return {**result, 'schema': SCHEMA, 'literal_readout_content_sha256': report['content_sha256'],
        'scientific_source_commit': report['scientific_source_commit'],
        'original_readout_source_commit': report['analysis_source_commit'],
        'annual_cost_support': annual, 'requested_cost_score_is_optimized': False,
        'new_code_executions': 0, 'automatic_invention': False,
        'held_out_evaluation': False, 'independent_optimizer_replications': False}


def render(report, output):
    """Render recorded values only, never simulate a favorable result."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import MaxNLocator
    with plt.rc_context({'font.size': 7.5, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.hashsalt': SCHEMA}):
        fig, axes = plt.subplots(2, 1, figsize=(5.5, 5.4))
        colors = ['#087f8c', '#b47835']
        maximum = 0
        for index, world in enumerate(report['annual_cost_support']):
            years = world['years']; x = [row['year'] + (-0.18 if index == 0 else 0.18) for row in years]
            collected = [row['collected_activity_cost'] for row in years]
            unpaid = [row['uncollected_activity_cost'] for row in years]
            axes[0].bar(x, collected, width=0.30, color=colors[index])
            axes[0].bar(x, unpaid, bottom=collected, width=0.30, facecolor='white',
                        edgecolor=colors[index], hatch='////', linewidth=0.8)
            maximum = max(maximum, *[a + b for a, b in zip(collected, unpaid)])
        axes[0].set(title='A  Original requested charges: collected + unpaid',
            xlabel='Native year', ylabel='Native resource units', xticks=[1, 2, 3, 4],
            ylim=(0, max(1, maximum) * 1.55))
        axes[0].legend(handles=[Patch(color=colors[0], label='Reference collected'),
            Patch(color=colors[1], label='Control collected'),
            Patch(facecolor='white', edgecolor='#59636d', hatch='////', label='Unpaid component')],
            fontsize=6, loc='upper left', frameon=False, ncol=2)
        contrast = report['contrast_control_minus_reference']
        values = [contrast['reported_C_loss'], contrast['requested_cost_score_diagnostic_not_optimized']]
        labels = ['Declared C\n(collected cost)', 'Requested-cost diagnostic\n(not optimized)']
        axes[1].barh([1, 0], values, height=0.45, color=[colors[0], '#9aa7b5'])
        scale = max(1, *map(abs, values))
        axes[1].set(title='B  Observed loss contrast: control minus reference',
            yticks=[1, 0], yticklabels=labels, xlabel='Content-opinion loss units (lower is better)',
            xlim=(min(0, *values) - 0.25 * scale, max(0, *values) + 0.25 * scale), ylim=(-0.6, 1.6))
        axes[1].axvline(0, color='#85909c', lw=0.7)
        for y, value in zip([1, 0], values):
            axes[1].text(value + (0.04 * scale if value >= 0 else -0.04 * scale), y,
                f'{value:.5g}', va='center', ha='left' if value >= 0 else 'right')
        axes[0].yaxis.set_major_locator(MaxNLocator(integer=True))
        for axis in axes:
            axis.grid(axis='x' if axis is axes[1] else 'y', color='#e8edf2', lw=0.6)
            axis.set_axisbelow(True)
        fig.suptitle('Collected cost is not requested expense', fontsize=10.5, y=0.97)
        fig.text(0.03, 0.055,
            'One reused development condition; hand controls, not autonomous invention.\n'
            'The requested-cost diagnostic does not change or veto the declared C objective.', fontsize=6.5)
        fig.subplots_adjust(left=0.30, right=0.96, top=0.88, bottom=0.20, hspace=0.85)
        for ext in ('png', 'svg'):
            fig.savefig(output / ('collected-versus-requested.' + ext), dpi=250,
                        metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def export(args):
    readouts, frozen, out = args.readouts.resolve(), args.frozen_reader.resolve(), args.output.resolve()
    source, original_reader = pinned_revision(ROOT), pinned_revision(frozen)
    if out.exists() or any(out.is_relative_to(p) for p in (ROOT, frozen, readouts)):
        raise ValueError('fresh interpretation outside original readouts and both sources required')
    read = lambda path: checked(json.loads(path.read_text()))
    start, end = read(readouts / 'started.json'), read(readouts / 'ended.json')
    if (start['schema'] != 'scienceutopia.native-terminal-cost-readout.v1.finish'
            or start['analysis_source_commit'] != original_reader or end['status'] != 'closed'
            or end['steps'] != [{'stage': 'report-1', 'exit_code': 0}, {'stage': 'report-2', 'exit_code': 0}]
            or end['new_model_calls'] != 0 or end['new_native_worlds'] != 0):
        raise ValueError('original normally closed paired readout continuation required')
    names = ('report.json', 'controls.csv', 'manifest.json')
    paths = [readouts / name for name in ('started.json', 'ended.json')]
    for i in (1, 2):
        directory = readouts / f'report-{i}'
        if sorted(p.name for p in directory.iterdir()) != sorted(names):
            raise ValueError('exact complete original readout file set required')
        manifest = read(directory / 'manifest.json')
        if any(file_sha256(directory / name) != value for name, value in manifest['files'].items()):
            raise ValueError('original readout manifest differs')
        if {name: file_sha256(directory / name) for name in names} != end['report_files']:
            raise ValueError('literal paired readout closure differs')
        paths.extend(directory / name for name in names)
    inputs = {str(path): file_sha256(path) for path in paths}
    report = read(readouts / 'report-1/report.json')
    if (report['analysis_source_commit'] != original_reader
            or report['scientific_source_commit'] != start['scientific_source_commit']):
        raise ValueError('literal original source identities differ')
    result = {**derive(report), 'analysis_source_commit': source, 'inputs': inputs}
    if inputs != {str(path): file_sha256(path) for path in paths} or pinned_revision(ROOT) != source:
        raise ValueError('readout inputs or interpretation source changed')
    out.mkdir(parents=True)
    save(out / 'report.json', result)
    fields = list(result['worlds'][0])
    with (out / 'accounting.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(result['worlds'])
    if args.render:
        render(result, out)
    save(out / 'manifest.json', {'schema': SCHEMA + '.export', 'analysis_source_commit': source,
        'original_readout_source_commit': original_reader, 'inputs': inputs,
        'files': {p.name: file_sha256(p) for p in sorted(out.iterdir())},
        'new_model_calls': 0, 'new_native_worlds': 0, 'visual_review_complete': False})
    print(json.dumps({'status': result['status'], 'contrast': result['contrast_control_minus_reference']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('readouts', 'frozen-reader', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--render', action='store_true')
    export(parser.parse_args())


if __name__ == '__main__':
    main()
