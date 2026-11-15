"""Print paths from retained closed data; nulls have a separate nonnumeric strip."""
import argparse
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked, save
from utopia.utils.data_utils import file_sha256


def series(report, arm, objective):
    rows = sorted((r for r in report['slots'] if r['arm'] == arm
                   and r['objective'] == objective), key=lambda r: r['generation'])
    if len(rows) != 3 or [r['generation'] for r in rows] != [0, 1, 2]:
        raise ValueError('three original charged generations required')
    best, values = None, []
    for row in rows:
        if row['status'] == 'complete':
            if row['loss'] is None:
                raise ValueError('completed slot lacks assigned loss')
            best = row['loss'] if best is None else min(best, row['loss'])
        elif row['loss'] is not None:
            raise ValueError('null must not have a numerical loss')
        values.append({'generation': row['generation'], 'observed': row['loss'],
                       'best_own': best, 'null': row['status'] != 'complete'})
    return values


def render(report, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    navy, gray, gold, red = '#254a70', '#737f8b', '#b67723', '#b34545'
    rc = {'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False,
          'svg.hashsalt': 'native-longitudinal-paper-v1'}
    with plt.rc_context(rc):
        fig = plt.figure(figsize=(9.4, 6.9))
        grid = fig.add_gridspec(2, 2, left=.095, right=.98, top=.88, bottom=.17,
                               hspace=.55, wspace=.29)
        for i, arm in enumerate(report['information_arms']):
            for j, objective in enumerate(report['score_order']):
                cell = grid[i, j].subgridspec(2, 1, height_ratios=[4, .65], hspace=.08)
                ax = fig.add_subplot(cell[0]); strip = fig.add_subplot(cell[1], sharex=ax)
                values = series(report, arm, objective)
                x = [v['generation'] for v in values]
                ax.plot(x, [v['best_own'] for v in values], color=navy, lw=1.7)
                completed = [v for v in values if not v['null']]
                ax.scatter([v['generation'] for v in completed], [v['observed'] for v in completed],
                           s=35, color=navy, edgecolor='white', linewidth=.5, zorder=4)
                for reference in report['references']:
                    ax.axhline(reference['scores'][objective], lw=1.1,
                               color=gray if reference['optimizer_visible'] else gold,
                               ls=':' if reference['optimizer_visible'] else '--')
                numbers = [v['observed'] for v in completed]
                numbers += [r['scores'][objective] for r in report['references']]
                span = max(numbers) - min(numbers); pad = max(.35, span * .22)
                ax.set(ylim=(min(numbers)-pad, max(numbers)+pad), xlim=(-.15, 2.15),
                       title=('Scalar' if arm == 'scalar' else 'Parent trajectory') +
                       (' / throughput' if objective == 'throughput' else ' / content utility'))
                ax.set_ylabel('Assigned loss (lower is better)'); ax.grid(axis='y', color='#e4e8ec')
                ax.tick_params(axis='x', labelbottom=False, bottom=False)
                strip.set(ylim=(-1, 1), yticks=[], xticks=[0, 1, 2], xlabel='Generation')
                strip.set_facecolor('#f4f5f6'); strip.spines['left'].set_visible(False)
                strip.spines['bottom'].set_visible(False)
                strip.set_ylabel('Null', rotation=0, labelpad=20, va='center', color=red)
                nulls = [v['generation'] for v in values if v['null']]
                strip.scatter(nulls, [0] * len(nulls), marker='x', s=35, color=red)
        handles = [Line2D([], [], color=navy, marker='o', label='Own loss / best own'),
                   Line2D([], [], color=gray, ls=':', label='R7 (optimizer-visible)'),
                   Line2D([], [], color=gold, ls='--', label='Hand control (withheld)')]
        fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .045),
                   ncol=3, frameon=False, fontsize=8)
        fig.suptitle('Twelve own proposals: no assigned-loss improvement', y=.975, fontsize=13)
        fig.text(.5, .925, 'One reused development condition; no independent error bars. '
                 'Crosses are unknown losses, not penalties.', ha='center', fontsize=8.5, color='#46515d')
        for ext in ('png', 'svg'):
            fig.savefig(output / ('assigned-loss-paths-print.' + ext), dpi=200,
                        metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = checked(json.loads(args.report.read_text()))
    if report['schema'] != 'scienceutopia.native-longitudinal-comparison-report.v1':
        raise ValueError('original closed longitudinal score readout required')
    if args.output.exists():
        raise ValueError('fresh figure output required; retain the original figure')
    args.output.mkdir(parents=True)
    render(report, args.output)
    save(args.output / 'manifest.json', {'schema': 'scienceutopia.native-longitudinal-paper-figure.v1',
         'input_file_sha256': file_sha256(args.report),
         'input_content_sha256': report['content_sha256'], 'renderer_sha256': file_sha256(__file__),
         'files': {p.name: file_sha256(p) for p in sorted(args.output.iterdir())},
         'new_model_calls': 0, 'new_scientific_worlds': 0, 'visual_review_complete': False})


if __name__ == '__main__':
    main()
