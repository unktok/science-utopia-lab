"""Print-sized views of the complete, retained fourteen-world planning study."""
import argparse
import json
import math
from pathlib import Path

from scripts.reports.native_objective_instrument_loop_v1 import cross_score_groups
from scripts.reports.native_planning_content_contributions_v1 import summarize
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.native_planning_controls import ORDER
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-planning-paper-figures.v1'


def validate(report, content):
    checked(report); checked(content)
    if (report['schema'] != 'scienceutopia.native-planning-objective-report.v1'
            or report['score_order'] != ['throughput', 'content-utility']
            or tuple(r['label'] for r in report['references']) != ORDER
            or len(report['physical_worlds']) != 14 or len(report['slots']) != 6
            or {(s['objective'], s['generation']) for s in report['slots']}
                != {(o, g) for o in report['score_order'] for g in range(3)}
            or any(w['status'] != 'complete' for w in report['physical_worlds'])
            or summarize(report) != content):
        raise ValueError('exact complete original planning report and signed-content join required')


def render(report, content, out):
    validate(report, content)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import MaxNLocator
    with plt.rc_context({'font.size': 9, 'axes.titlesize': 10, 'axes.spines.top': False,
            'axes.spines.right': False, 'svg.hashsalt': SCHEMA}):
        fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.05))
        for ax, objective, title in zip(axes, report['score_order'], ['Count loss T', 'Content loss U']):
            for i, reference in enumerate(report['references']):
                ax.axhline(reference['scores'][objective], color='#7a8794', ls='--', lw=.9,
                    label='Fresh references' if i == 0 else None, zorder=1)
            rows = sorted((s for s in report['slots'] if s['objective'] == objective), key=lambda s: s['generation'])
            best = None; path = []
            for row in rows:
                if row['loss'] is None:
                    path.append(math.nan)
                else:
                    ax.scatter(row['generation'], row['loss'], color='#087f8c', s=29, zorder=4)
                    best = row['loss'] if best is None else min(best, row['loss']); path.append(best)
            ax.plot([r['generation'] for r in rows], path, color='#087f8c', lw=1.6, label='Best own submission')
            ax.set(title=title, xlabel='Consumed generation', ylabel='Assigned loss', xticks=[0, 1, 2], xlim=(-.25, 2.25))
            ax.margins(y=.12); ax.grid(axis='y', color='#e9edef'); ax.set_axisbelow(True)
            ax.legend(fontsize=7.5, loc='center right', framealpha=.95)
        fig.tight_layout(pad=.5, w_pad=.9)
        _save(fig, out, 'loss-paths'); plt.close(fig)

        groups, unavailable = cross_score_groups(report)
        if unavailable:
            raise ValueError('complete retained study must keep every cross-score')
        fig, ax = plt.subplots(figsize=(6.4, 3.05))
        for i, group in enumerate(groups):
            ax.scatter(group['T'], group['U'], color='#087f8c', s=34, zorder=3)
            offset = (12, -12) if i == 0 else (12, 10) if i == 1 else (9, 3)
            ax.annotate(group['group'], (group['T'], group['U']), xytext=offset,
                textcoords='offset points', fontsize=9, arrowprops={'arrowstyle': '-', 'color': '#607180', 'lw': .65})
        ax.set(xlabel='Count loss T (lower is better)', ylabel='Content loss U (lower is better)',
            xticks=[-18, -12, 0], xlim=(-19.5, 1.2), ylim=(-14.6, 1.1))
        ax.grid(color='#e9edef'); ax.set_axisbelow(True); fig.tight_layout(pad=.5)
        _save(fig, out, 'cross-scores'); plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.3))
        colors = {'positive': '#087f8c', 'zero': '#a8b0bc', 'negative': '#b47835'}
        for i, world in enumerate(content['worlds']):
            bottom = 0
            for sign, color in colors.items():
                count = world['sign_counts'][sign]
                axes[0].bar(i, count, bottom=bottom, color=color, width=.7); bottom += count
            axes[1].bar(i, world['recorded_utility_by_sign']['positive'], color=colors['positive'], width=.7)
            axes[1].bar(i, world['recorded_utility_by_sign']['negative'], color=colors['negative'], width=.7)
        labels = [w['label'] for w in content['worlds']]
        for ax in axes:
            ax.set(xticks=range(len(labels)), xticklabels=labels, xlim=(-.7, len(labels)-.3))
            ax.tick_params(axis='x', labelsize=7, rotation=90)
            ax.grid(axis='y', color='#e9edef'); ax.set_axisbelow(True)
        count_top = max(1, 1.12 * max(sum(w['sign_counts'].values()) for w in content['worlds']))
        axes[0].set(title='Accepted occurrences', ylabel='Count (T = -count)', ylim=(0, count_top))
        axes[0].yaxis.set_major_locator(MaxNLocator(integer=True))
        utility_low = min(0, 1.12 * min(w['recorded_utility_by_sign']['negative'] for w in content['worlds']))
        utility_high = max(1, 1.12 * max(w['recorded_utility_by_sign']['positive'] for w in content['worlds']))
        axes[1].set(title='Signed content utility', ylabel='Utility sum (U = -sum)', ylim=(utility_low, utility_high))
        fig.legend(handles=[Patch(color=c, label=s) for s, c in colors.items()],
            loc='lower center', ncol=3, fontsize=8, frameon=False, bbox_to_anchor=(.5, -.01))
        fig.tight_layout(rect=(0, .085, 1, 1), pad=.5, w_pad=1.)
        _save(fig, out, 'content-contributions'); plt.close(fig)


def _save(fig, output, name):
    for ext in ('png', 'svg'):
        fig.savefig(output / (name+'.'+ext), dpi=300, metadata={'Date': None} if ext == 'svg' else None)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('report', 'content', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args(); source = pinned_revision(ROOT)
    if args.output.exists():
        raise ValueError('fresh paper-figure directory required')
    hashes = {str(path): file_sha256(path) for path in (args.report, args.content)}
    report, content = [checked(json.loads(path.read_text())) for path in (args.report, args.content)]
    validate(report, content); args.output.mkdir(parents=True); render(report, content, args.output)
    if hashes != {str(path): file_sha256(path) for path in (args.report, args.content)} or pinned_revision(ROOT) != source:
        raise ValueError('original inputs or figure source changed')
    save(args.output/'manifest.json', {'schema': SCHEMA, 'source_commit': source, 'inputs': hashes,
        'report_content_sha256': report['content_sha256'], 'content_report_sha256': content['content_sha256'],
        'files': {f.name: file_sha256(f) for f in sorted(args.output.iterdir())},
        'coordinates_or_losses_changed': False, 'new_model_calls': 0, 'new_code_executions': 0})


if __name__ == '__main__':
    main()
