"""Print actual three-control outcomes without implying optimizer improvement."""
import argparse
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked, save
from utopia.utils.data_utils import file_sha256


def render(report, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    rows = report['worlds']
    if [r['condition'] for r in rows] != ['core-assignment', 'native-choice', 'native-choice-advice']:
        raise ValueError('complete original ordered three-control readout required')
    labels = ['Direct core assignment', 'Native choice', 'Native choice + advice']
    with plt.rc_context({'font.size': 11, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.hashsalt': 'native-choice-controls-paper-v1'}):
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.7))
        fig.subplots_adjust(left=.225, right=.95, top=.76, bottom=.20, wspace=.40)
        for ax, key, title in zip(axes, ['throughput', 'content-utility'],
                                ['Accepted decisions (A)', 'Frozen content-opinion utility (U)']):
            values = [-r['scores'][key] for r in rows]
            ax.barh(range(3), values, color=['#ac6f18', '#254a70', '#4c889d'], height=.56)
            for y, value in enumerate(values):
                ax.text(value + .25, y, f'{value:.2f}'.rstrip('0').rstrip('.'), va='center', fontsize=11)
            ax.set(yticks=range(3), yticklabels=labels if key == 'throughput' else ['', '', ''],
                   xlim=(0, max(values) * 1.19), title=title, xlabel='Higher is better')
            ax.invert_yaxis(); ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
            ax.set_axisbelow(True); ax.grid(axis='x', color='#e7ebee')
        fig.suptitle('Advice improves native choice here, but not the strong control', y=.965, fontsize=14)
        fig.text(.5, .855, 'Three hand-designed institutions; original four-year world and fixed Qwen3-8B scientists.',
                 ha='center', fontsize=10, color='#46515d')
        fig.text(.225, .08, 'One reused development seed; no error bars, autonomous invention or causal mediation claim.',
                 fontsize=9, color='#46515d')
        for ext in ('png', 'svg'):
            fig.savefig(output / ('native-choice-outcomes.' + ext), dpi=200,
                        metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = checked(json.loads(args.report.read_text()))
    if report['schema'] != 'scienceutopia.native-legacy-choice-pilot-report.v1' or args.output.exists():
        raise ValueError('actual original report and fresh figure output required')
    args.output.mkdir(parents=True)
    render(report, args.output)
    save(args.output / 'manifest.json', {
        'schema': 'scienceutopia.native-choice-control-paper-figure.v1',
        'input_file_sha256': file_sha256(args.report), 'input_content_sha256': report['content_sha256'],
        'renderer_sha256': file_sha256(__file__),
        'files': {p.name: file_sha256(p) for p in sorted(args.output.iterdir())},
        'new_model_calls': 0, 'new_native_worlds': 0, 'visual_review_complete': False})


if __name__ == '__main__':
    main()
