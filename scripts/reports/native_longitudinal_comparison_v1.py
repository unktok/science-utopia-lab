"""Four histories, two objectives: all paths/nulls, never independent replicates."""
import argparse
from pathlib import Path

from scripts.reports.native_workflow_objective_loop_v1 import export


def render(report, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    arms = report['information_arms']; colors = ('#087f8c', '#a54c7a')
    with plt.rc_context({'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False,
            'svg.hashsalt': report['schema']}):
        fig, axes = plt.subplots(2, 2, figsize=(10, 6.2), sharex='col')
        for column, objective in enumerate(report['score_order']):
            for arm, color in zip(arms, colors):
                style = '--' if arm == 'parent-trajectory' else '-'
                path = report['loss_paths'][arm+'::'+objective]
                x = [r['generation'] for r in path]
                own = [float('nan') if r['best_own_loss'] is None else r['best_own_loss'] for r in path]
                axes[0, column].plot(x, own, color=color, label=arm, lw=1.7, ls=style)
                valid = [r for r in path if r['status'] == 'complete']
                axes[0, column].scatter([r['generation'] for r in valid], [r['observed_loss'] for r in valid],
                    color=color, s=23, zorder=3)
                nulls = [r['generation'] for r in path if r['status'] != 'complete']
                if nulls:
                    axes[0, column].scatter(nulls, [.97]*len(nulls), transform=axes[0, column].get_xaxis_transform(),
                        color=color, marker='x', s=24, label=arm+' null (no loss)', zorder=4)
                initial = min(r['scores'][objective] for r in report['references'] if r['optimizer_visible'])
                axes[1, column].plot([-1]+x, [initial]+[r['best_known_loss'] for r in path],
                    color=color, lw=1.7, ls=style, marker='o', ms=3, label=arm)
            for row in range(2):
                ax = axes[row, column]
                for reference, color in zip(report['references'], ('#7c8793', '#c18034')):
                    ax.axhline(reference['scores'][objective], color=color, ls='--', lw=.9, label=reference['label'])
                ax.grid(axis='y', color='#e8ebef')
                ax.set(title=objective+(' / all proposals and best own' if row == 0 else ' / reference-inclusive incumbent'),
                    ylabel='Assigned loss (lower is better)', xticks=[-1, 0, 1, 2])
                ax.legend(fontsize=6, loc='best')
            axes[1, column].set_xlabel('Generation (-1: initial visible reference only)')
        fig.suptitle('Additional trajectory access: four histories on one reused development condition\n'
            'Dots: completed own proposals; crosses: nulls without numerical penalties; no independent error bars', fontsize=10)
        fig.tight_layout(rect=(0, 0, 1, .92))
        for ext in ('png', 'svg'):
            fig.savefig(output/('objective-loss-paths.'+ext), dpi=200, metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'audit-one', 'audit-two', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__': main()
