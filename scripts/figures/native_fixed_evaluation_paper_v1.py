"""Print-sized views of retained fixed-policy results; no new observations."""
import argparse
import json
from pathlib import Path

from scripts.reports.native_fixed_evaluation_reproduce_v1 import validate
from utopia.optimization.native_numeric_designer import save
from utopia.utils.data_utils import file_sha256

SCHEMA = 'scienceutopia.native-fixed-evaluation-paper-figures.v1'
LABELS = ['Seed', 'Legacy', 'Reviewed / all', 'No review / all', 'Route 1 / all',
          'Route 2 / all', 'T / numeric', 'E / numeric', 'T / fixed code',
          'E / fixed code', 'T / code + graph', 'E / code + graph']
COLORS = ('#168e96', '#bc8033', '#7a63a7')


def render(r, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.rc_context({'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.hashsalt': SCHEMA}):
        fig, axes = plt.subplots(1, 2, figsize=(6.2, 5.1), sharey=True)
        for ax, objective, title in zip(axes, ('throughput', 'efficiency'),
                                        ('T: -A', 'E: -Q + 0.5R')):
            for j, seed in enumerate(r['evaluation_seeds']):
                lookup = {x['label']: x for x in r['evaluation_rows'] if x['seed'] == seed}
                pairs = [(i, lookup[label]['scores'][objective]) for i, label in enumerate(r['evaluation_label_order'])]
                ax.scatter([v for i, v in pairs if v is not None],
                           [i + (j - 1) * .15 for i, v in pairs if v is not None],
                           color=COLORS[j], s=22, label=str(seed), zorder=3)
            for i, label in enumerate(r['evaluation_label_order']):
                if all(x['physical_job'] is None for x in r['evaluation_rows'] if x['label'] == label):
                    ax.text(.97, i, 'no policy', transform=ax.get_yaxis_transform(),
                            ha='right', va='center', color='#777777', fontsize=8)
            ax.set_title(title, fontsize=10, pad=12)
            ax.set_xlabel('Proxy loss (lower is better)', fontsize=8.5)
            ax.set_yticks(range(len(LABELS)))
            ax.grid(axis='x', color='#e5e7eb', lw=.6)
            ax.axhline(5.5, color='#bac4cd', lw=.8)
            ax.margins(x=.09)
        axes[0].set_yticklabels(LABELS)
        axes[0].set_ylim(-.6, len(LABELS) - .4)
        axes[0].invert_yaxis()
        fig.suptitle('Fixed submissions on three unused seeds', fontsize=11, y=.985)
        fig.text(.5, .933, '30 physical worlds; 6 unavailable label/seed rows', ha='center', fontsize=8)
        fig.legend(*axes[0].get_legend_handles_labels(), loc='lower center', ncol=3,
                   frameon=False, bbox_to_anchor=(.56, .013), fontsize=8)
        fig.subplots_adjust(left=.27, right=.985, top=.84, bottom=.16, wspace=.23)
        for ext in ('png', 'svg'):
            fig.savefig(output / ('fixed-submission-comparison.' + ext), dpi=260,
                        metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)

        fig, axes = plt.subplots(2, 3, figsize=(6.2, 3.7))
        for row, objective in enumerate(('throughput', 'efficiency')):
            for col, (method, title) in enumerate(zip(
                    ('parameters', 'code-fixed-graph', 'code-and-graph'),
                    ('Numeric', 'Fixed code', 'Code + graph'))):
                ax = axes[row, col]
                slots = [s for s in r['search_slots'] if s['arm'] == objective + ':' + method]
                best = None; path = []
                for s in slots:
                    v = s['loss']
                    if v is not None:
                        best = v if best is None else min(best, v)
                        ax.scatter([s['generation']], [v], color=COLORS[0], s=20, zorder=3)
                    else:
                        ax.text(s['generation'], .08, 'not sent' if s['status'] == 'not-submitted' else 'failed',
                                transform=ax.get_xaxis_transform(), ha='center', fontsize=7.5, color='#a2473f')
                    path.append(best)
                ax.plot([s['generation'] for s in slots], path, color=COLORS[0], lw=1)
                ax.set(title=('T' if row == 0 else 'E') + ' / ' + title,
                       xticks=[0, 1], xlim=(-.3, 1.3), xlabel='Generation')
                if col == 0: ax.set_ylabel('Assigned loss')
                if all(v is None for v in path): ax.set_yticks([])
                ax.tick_params(labelsize=8)
                ax.grid(axis='y', color='#e5e7eb', lw=.6)
        fig.suptitle('Stopped search: all 12 slots', fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, .94), pad=.8)
        for ext in ('png', 'svg'):
            fig.savefig(output / ('stopped-search-paths.' + ext), dpi=260,
                        metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def export(report, output):
    if output.exists(): raise ValueError('fresh paper-figure output required')
    before = file_sha256(report); r = validate(json.loads(report.read_text()))
    output.mkdir(parents=True); render(r, output)
    if file_sha256(report) != before: raise ValueError('retained report changed')
    save(output / 'manifest.json', {'schema': SCHEMA, 'input_report_file_sha256': before,
         'input_report_content_sha256': r['content_sha256'],
         'renderer_sha256': file_sha256(Path(__file__)),
         'files': {p.name: file_sha256(p) for p in sorted(output.iterdir())},
         'comparison_objectives': ['throughput', 'efficiency'],
         'descriptive_selective_score_retained_in_original_report': True,
         'new_model_calls': 0, 'new_native_worlds': 0})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); export(a.report, a.output)
    print(json.dumps({'paper_figures_built': True, 'new_model_calls': 0}))


if __name__ == '__main__': main()
