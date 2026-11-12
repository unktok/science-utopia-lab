"""Print-size literal all-seed T/U view; no reselection or new observations."""
import argparse
import json
from pathlib import Path

from scripts.reports.native_objective_fixed_evaluation_v1 import SCHEMA as REPORT_SCHEMA
from utopia.optimization.native_numeric_designer import checked, save
from utopia.utils.data_utils import file_sha256

SCHEMA = 'scienceutopia.native-objective-fixed-paper-figure.v1'
LABELS = ['Reviewed all + transfer', 'One-reviewer all + transfer', 'No-review all + transfer',
          'No-review reject + transfer', 'Reviewed all; transfer cut', 'T-selected',
          'U-selected (= reviewed)']


def export(report, output):
    before = file_sha256(report); r = checked(json.loads(report.read_text()))
    if (r['schema'] != REPORT_SCHEMA
            or len(r['labels']) != 7 or r['seeds'] != [64101, 64107, 64113]
            or len(r['logical_rows']) != 21 or len(r['physical_worlds']) != 18
            or output.exists()):
        raise ValueError('original complete three-seed T/U report and fresh output required')
    rows = {(v['label'], v['seed']): v for v in r['logical_rows']}
    if len(rows) != 21 or any(v['status'] != 'complete' for v in rows.values()):
        raise ValueError('every original complete logical cell required')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    output.mkdir(parents=True)
    with plt.rc_context({'font.size': 9, 'svg.hashsalt': SCHEMA,
                         'axes.spines.top': False, 'axes.spines.right': False}):
        fig, axes = plt.subplots(1, 2, figsize=(6.2, 3.7), sharey=True)
        for ax, score, title in zip(axes, r['score_order'], ['T: publication count', 'U: content proxy']):
            for j, (seed, color) in enumerate(zip(r['seeds'], ['#118895', '#9a5d8d', '#b87932'])):
                ax.scatter([rows[label, seed]['scores'][score] for label in r['labels']],
                           [i+(j-1)*.14 for i in range(7)], color=color, s=21,
                           label=str(seed), zorder=3)
            ax.set_title(title, fontsize=9.5, pad=9)
            ax.set_xlabel('Loss (lower is better)', fontsize=8.5)
            ax.set_yticks(range(7)); ax.grid(axis='x', color='#e2e7eb', linewidth=.6)
            ax.axhline(4.5, color='#b5c0ca', linewidth=.8)
            ax.margins(x=.12); ax.tick_params(labelsize=8)
        axes[0].set_yticklabels(LABELS, fontsize=8.2)
        axes[0].set_ylim(6.6, -.6)
        fig.suptitle('Fixed submissions; three unused world seeds', fontsize=10.5, y=.98)
        fig.text(.60, .89, '18 physical worlds / 21 logical cells; no reselection', ha='center', fontsize=7.5)
        fig.legend(*axes[0].get_legend_handles_labels(), loc='lower center',
                   bbox_to_anchor=(.60, .015), ncol=3, frameon=False, fontsize=8)
        fig.subplots_adjust(left=.35, right=.985, top=.81, bottom=.22, wspace=.27)
        for ext in ('png', 'svg'):
            fig.savefig(output/('fixed-tu-comparison.'+ext), dpi=280,
                        metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)
    if file_sha256(report) != before:
        raise ValueError('retained original report changed during rendering')
    save(output/'manifest.json', {'schema': SCHEMA, 'input_report_file_sha256': before,
        'input_report_content_sha256': r['content_sha256'], 'renderer_sha256': file_sha256(Path(__file__)),
        'files': {p.name: file_sha256(p) for p in sorted(output.iterdir())},
        'new_model_calls': 0, 'new_native_worlds': 0, 'candidate_reselection': False})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); export(a.report, a.output)


if __name__ == '__main__':
    main()
