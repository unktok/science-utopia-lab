"""Print-scale view of the exact retained240 conditional command rows."""
import argparse
import csv
import json
import math
from pathlib import Path

from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-reserve-paper.v1'


def render(rows, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    colors = ['#087f8c', '#9c5d8a', '#b47835', '#536c45']
    with plt.rc_context({'font.size': 9, 'xtick.labelsize': 8, 'ytick.labelsize': 8,
            'axes.spines.top': False, 'axes.spines.right': False, 'svg.hashsalt': SCHEMA}):
        fig, axes = plt.subplots(1, 2, figsize=(5.5, 3.0))
        for ax, field, title, ylabel in zip(axes,
                ('requested_units', 'recipient_count'), ('(a) Transfer volume', '(b) Recipients'),
                ('Requested units', 'Recipient count')):
            for year, color in zip(range(1, 5), colors):
                selected = [r for r in rows if r['year'] == year]
                ax.step([r['reserve_units'] for r in selected], [r[field] for r in selected],
                    where='mid', color=color, label='Year ' + str(year), lw=1.4)
            for value in (10, 21): ax.axvline(value, color='#777777', lw=.75, ls=':')
            ax.set(title=title, xlabel='Integer reserve', ylabel=ylabel, xlim=(1, 60), xticks=[1, 20, 40, 60])
            ax.yaxis.set_major_locator(MaxNLocator(integer=True)); ax.grid(axis='y', color='#ededed')
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='upper center', ncol=4, frameon=False, fontsize=8,
            handlelength=1.3, columnspacing=1.3)
        fig.text(.5, .025, 'Fixed original inputs; requested commands, not world outcomes.',
            ha='center', fontsize=8)
        fig.subplots_adjust(left=.10, right=.98, bottom=.23, top=.78, wspace=.42)
        for ext in ('png', 'svg'):
            fig.savefig(output / ('reserve-response-print.' + ext), dpi=300,
                metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def run(args):
    source = pinned_revision(ROOT); csv_path, output = args.csv.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(csv_path.parent): raise ValueError('fresh independent figure output required')
    before = file_sha256(csv_path)
    rows = [{k: int(r[k]) for k in ('year', 'reserve_units', 'requested_units', 'recipient_count')}
        for r in csv.DictReader(csv_path.open())]
    if (len(rows) != 240 or {(r['year'], r['reserve_units']) for r in rows} != {
            (y, r) for y in range(1, 5) for r in range(1, 61)}):
        raise ValueError('all240 exact original year/reserve rows required')
    rows.sort(key=lambda r: (r['year'], r['reserve_units']))
    output.mkdir(parents=True); render(rows, output)
    if before != file_sha256(csv_path) or pinned_revision(ROOT) != source:
        raise ValueError('figure source or original numeric rows changed')
    save(output / 'manifest.json', {'schema': SCHEMA, 'analysis_source_commit': source,
        'csv_file_sha256': before, 'rows': len(rows), 'figure_width_inches': 5.5,
        'text_font_points': 9, 'tick_and_legend_font_points': 8,
        'files': {p.name: file_sha256(p) for p in sorted(output.iterdir())},
        'new_model_calls': 0, 'new_code_executions': 0, 'new_native_worlds': 0,
        'alternative_world_outcomes_or_optimum_claimed': False})


def run_incumbents(args):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    source = pinned_revision(ROOT); path, output = args.incumbents.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(path.parent): raise ValueError('fresh independent figure output required')
    before = file_sha256(path); report = checked(json.loads(path.read_text()))
    if (report['schema'] != 'scienceutopia.native-optimization-incumbents.v1'
            or report['software_qa_plot'] or report['history_order'] != ['throughput', 'content-utility']
            or any(h['source_scope'] != 'numeric' or [r['consumed_slots'] for r in h['path']] != [0, 1, 2, 3]
                for h in report['histories'])):
        raise ValueError('complete actual numeric incumbent readout required')
    output.mkdir(parents=True)
    with plt.rc_context({'font.size': 9, 'xtick.labelsize': 8, 'ytick.labelsize': 8,
            'axes.spines.top': False, 'axes.spines.right': False, 'svg.hashsalt': SCHEMA + '.incumbents'}):
        fig, axes = plt.subplots(1, 2, figsize=(5.5, 3.0))
        for ax, h, title in zip(axes, report['histories'], ('Count objective T', 'Content objective U')):
            rows = h['path']; x = [r['consumed_slots'] for r in rows]
            ax.step(x, [r['best_known']['loss'] for r in rows], where='post', color='#596b84',
                lw=1.4, ls='--', label='Best known (with references)')
            ax.plot(x, [math.nan if r['best_own']['loss'] is None else r['best_own']['loss'] for r in rows],
                color='#087f8c', lw=1.5, marker='o', ms=4, label='Best own numeric proposal')
            ax.set(title=title, xlabel='Consumed slots', ylabel='Loss (lower is better)', xticks=[0, 1, 2, 3], xlim=(-.1, 3.1))
            ax.grid(axis='y', color='#ededed')
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='upper center', ncol=2, frameon=False, fontsize=8,
            handlelength=1.6, columnspacing=1.4)
        fig.text(.5, .025, 'One reused development world seed; no optimizer replication.', ha='center', fontsize=8)
        fig.subplots_adjust(left=.10, right=.98, bottom=.23, top=.78, wspace=.48)
        for ext in ('png', 'svg'):
            fig.savefig(output / ('incumbent-paths-print.' + ext), dpi=300,
                metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)
    if before != file_sha256(path) or pinned_revision(ROOT) != source:
        raise ValueError('incumbent source/input changed')
    save(output / 'manifest.json', {'schema': SCHEMA + '.incumbents', 'analysis_source_commit': source,
        'input_report_file_sha256': before, 'figure_width_inches': 5.5, 'font_points': 9,
        'files': {p.name: file_sha256(p) for p in sorted(output.iterdir())},
        'new_model_calls': 0, 'new_native_worlds': 0, 'selection_or_objective_changed': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--csv', type=Path); inputs.add_argument('--incumbents', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    (run if args.csv else run_incumbents)(args)


if __name__ == '__main__': main()
