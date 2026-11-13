"""All eight controls and six own slots after normal double original audit."""
import argparse
import math
from pathlib import Path
import textwrap

from scripts.reports.native_objective_instrument_loop_v1 import export as export_study, cross_score_groups


def render(report, output):
    """Use all eight references; the earlier five-color renderer is not reused."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = ['#596b84', '#b47835', '#9c5d8a', '#a9444a', '#75914a', '#2c7f96', '#6f62a5', '#4e6b43']
    references = report['references']
    if len(references) != 8 or len(report['slots']) != 6 or report['score_order'] != ['throughput', 'content-utility']:
        raise ValueError('literal eight-reference/six-slot T/U report required')
    key = ['R' + str(i + 1) + ' = ' + r['label'] for i, r in enumerate(references)]
    with plt.rc_context({'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False,
                        'svg.hashsalt': report['schema']}):
        fig, axes = plt.subplots(1, 2, figsize=(11, 5.3))
        for ax, objective, title in zip(axes, report['score_order'], ['Count objective T', 'Content objective U']):
            for i, (reference, color) in enumerate(zip(references, colors)):
                ax.axhline(reference['scores'][objective], color=color, lw=.9, ls='--', label='R' + str(i + 1))
            rows = [r for r in report['slots'] if r['objective'] == objective]
            path, best = [], None
            for row in rows:
                if row['loss'] is None:
                    ax.text(row['generation'], .02, 'null', transform=ax.get_xaxis_transform(), ha='center', color='#a9444a')
                else:
                    ax.scatter(row['generation'], row['loss'], s=32, color='#087f8c', zorder=3)
                    best = row['loss'] if best is None else min(best, row['loss'])
                path.append(math.nan if best is None else best)
            ax.plot([r['generation'] for r in rows], path, color='#087f8c', label='Best own submission')
            ax.set(title=title, xlabel='Consumed proposal generation', ylabel='Assigned loss (lower is better)',
                   xticks=[0, 1, 2], xlim=(-.3, 2.3))
            ax.grid(axis='y', color='#ededed'); ax.legend(fontsize=6, loc='best', ncol=2)
        fig.suptitle('Free native planning/allocation: every control and own slot, development seed61001', fontsize=10)
        fig.tight_layout(rect=(0, .27, 1, .94))
        for x, rows in ((.06, key[:4]), (.53, key[4:])):
            fig.text(x, .04, '\n'.join(rows), va='bottom', fontsize=7, linespacing=1.5)
        for ext in ('png', 'svg'):
            fig.savefig(output / ('objective-loss-paths.' + ext), dpi=200, metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)
        fig, axes = plt.subplots(2, 2, figsize=(11, 7.2), gridspec_kw={'height_ratios': [3, 1.15]})
        ax, table_ax, key_ax, note_ax = axes.ravel()
        groups, unavailable = cross_score_groups(report)
        for group in groups:
            ax.scatter(group['T'], group['U'], s=38, color='#087f8c')
            ax.annotate(group['group'], (group['T'], group['U']), xytext=(5, 5), textcoords='offset points', fontsize=8)
        ax.set(title='Exact score points with all ties', xlabel='Count loss T (lower is better)', ylabel='Content loss U (lower is better)')
        ax.grid(color='#ededed')
        for coordinate, setter in [('T', ax.set_xlim), ('U', ax.set_ylim)]:
            values = {g[coordinate] for g in groups}
            if len(values) == 1:
                v = next(iter(values)); setter(v - .5, v + .5)
        table_ax.axis('off')
        cells = [[g['group'], f"{g['T']:g}", f"{g['U']:g}", textwrap.fill(', '.join(g['labels']), 28)] for g in groups]
        if cells:
            table = table_ax.table(cellText=cells, colLabels=['Point', 'T', 'U', 'All world labels'],
                                   colWidths=[.12, .15, .15, .58], bbox=(0, .03, 1, .94), cellLoc='left')
            table.auto_set_font_size(False); table.set_fontsize(7)
            for (i, j), cell in table.get_celld().items():
                cell.set_edgecolor('#d8dee5'); cell.set_linewidth(.5)
                if i == 0: cell.set_facecolor('#edf2f5')
        key_ax.axis('off'); note_ax.axis('off')
        key_ax.text(0, 1, '\n'.join(key[:4]), va='top', fontsize=7, linespacing=1.6)
        note_ax.text(0, 1, '\n'.join(key[4:]), va='top', fontsize=7, linespacing=1.6)
        note = 'T/U labels = own-objective generation. No coordinate jitter or independent-history claim.'
        if unavailable: note += '\nUnavailable cross-score: ' + ', '.join(unavailable)
        fig.text(.06, .025, note, va='bottom', fontsize=7)
        fig.suptitle('Both fixed criteria on the same completed native planning worlds', fontsize=10)
        fig.tight_layout(rect=(0, .08, 1, .94))
        for ext in ('png', 'svg'):
            fig.savefig(output / ('objective-cross-scores.' + ext), dpi=200, metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def export(args):
    return export_study(args, study='planning-v1', renderer=render)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'audit-one', 'audit-two', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__': main()
