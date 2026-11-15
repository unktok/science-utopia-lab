"""Compact fixed-condition figure: one row per physical job, not logical alias."""
import argparse
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked, save
from utopia.utils.data_utils import file_sha256

LABELS = {'reference:R7-original': 'R7', 'reference:post-funding-cost': 'Hand control',
          'selected:scalar::throughput': 'Scalar / T',
          'selected:scalar::content-utility': 'Scalar / U',
          'selected:parent-trajectory::throughput': 'Parent trajectory / T',
          'selected:parent-trajectory::content-utility': 'Parent trajectory / U'}


def physical_rows(report):
    if report['schema'] != 'scienceutopia.native-longitudinal-fixed-report.v1' or len(report['seeds']) != 1:
        raise ValueError('one closed original longitudinal unused condition required')
    rows = {}
    for row in report['logical_rows']:
        if row['status'] != 'complete' or row['label'] not in LABELS:
            raise ValueError('all six completed literal labels required for this figure')
        item = rows.setdefault(row['physical_job'], {'labels': [], 'scores': row['scores']})
        if item['scores'] != row['scores']:
            raise ValueError('shared physical job has inconsistent scores')
        item['labels'].append(row['label'])
    if len(rows) != 5 or {x for r in rows.values() for x in r['labels']} != set(LABELS):
        raise ValueError('five physical jobs/six exact logical labels required')
    return list(rows.values())


def render(report, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows = physical_rows(report)
    with plt.rc_context({'font.size': 12, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.hashsalt': 'longitudinal-fixed-paper-v1'}):
        fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.9), sharey=True)
        for ax, objective, title in zip(axes, report['score_order'], ('Throughput loss', 'Content-utility loss')):
            values = [r['scores'][objective] for r in rows]
            span = max(values) - min(values)
            ax.axvline(values[0], color='#9aa4ae', ls=':', lw=1)
            for i, (row, value) in enumerate(zip(rows, values)):
                color = '#b67723' if 'reference:post-funding-cost' in row['labels'] else (
                    '#737f8b' if 'reference:R7-original' in row['labels'] else '#254a70')
                ax.scatter(value, i, s=48, color=color, zorder=3)
                ax.annotate(f'{value:g}' if value == int(value) else f'{value:.2f}',
                            (value, i), xytext=(8, 0), textcoords='offset points', va='center', fontsize=11)
            ax.set(xlim=(min(values)-.25*span, max(values)+.5*span), xlabel=title + ' (lower is better)',
                   yticks=list(range(len(rows))))
            ax.grid(axis='x', color='#e4e8ec')
        axes[0].set_yticklabels([' + '.join(LABELS[x] for x in row['labels']) for row in rows])
        axes[0].invert_yaxis(); axes[1].tick_params(axis='y', labelleft=False)
        fig.suptitle('Frozen selections: no gain on one unused condition', fontsize=16, y=.97)
        fig.text(.5, .035, 'Five physical worlds for six labels; the shared R7 / scalar-U job appears once. '
                 'No independent error bars.', ha='center', fontsize=10)
        fig.subplots_adjust(left=.25, right=.98, top=.82, bottom=.23, wspace=.28)
        for ext in ('png', 'svg'):
            fig.savefig(output / ('fixed-policy-scores-print.' + ext), dpi=200,
                        metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); report = checked(json.loads(args.report.read_text()))
    physical_rows(report)
    if args.output.exists():
        raise ValueError('fresh figure output required')
    args.output.mkdir(parents=True); render(report, args.output)
    save(args.output / 'manifest.json', {'schema': 'scienceutopia.native-longitudinal-fixed-paper-figure.v1',
         'input_file_sha256': file_sha256(args.report), 'input_content_sha256': report['content_sha256'],
         'renderer_sha256': file_sha256(__file__),
         'files': {p.name: file_sha256(p) for p in sorted(args.output.iterdir())},
         'new_model_calls': 0, 'new_scientific_worlds': 0, 'visual_review_complete': False})


if __name__ == '__main__':
    main()
