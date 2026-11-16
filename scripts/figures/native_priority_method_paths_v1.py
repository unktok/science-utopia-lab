"""Plot every objective-conditioned history without pooling seeds or nulls.

Rendering is a post-closure operation, not allowed as independent heavy work
during live inference. Importing this module does not import a plotting backend.
"""
import argparse
from pathlib import Path

from scripts.reports.native_priority_method_readout_v1 import SCHEMA, METHODS, OBJECTIVES, read
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]


def plot_data(report):
    if report['schema'] != SCHEMA or report['coverage']['declared_own_slots'] != 24:
        raise ValueError('complete mixed-method all-slot readout required')
    panels = []
    for method in METHODS:
        for objective in OBJECTIVES:
            histories = []
            for rep in range(2):
                path = report['paths']['/'.join((method, str(rep), objective))]
                if [r['generation'] for r in path] != [0, 1]:
                    raise ValueError('both actual generations, including nulls, required')
                selected = [s for s in report['selected'] if
                    (s['method'], s['replication'], s['objective']) == (method, rep, objective)]
                if len(selected) != 1: raise ValueError('one exact frozen own selection required')
                histories.append({'replication': rep, 'path': path, 'selected_cell_id': selected[0]['cell_id']})
            panels.append({'method': method, 'objective': objective, 'histories': histories})
    return panels


def render(report, output):
    data = plot_data(report)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    styles = {'font.size': 7, 'axes.titlesize': 8, 'axes.labelsize': 7,
        'xtick.labelsize': 7, 'ytick.labelsize': 7, 'svg.hashsalt': 'scienceutopia-priority-method-paths-v1'}
    method_names = dict(zip(METHODS, ('Uniform priorities', 'Adaptive priorities', 'Free code / graph')))
    objective_names = {OBJECTIVES[0]: 'Content utility: -U', OBJECTIVES[1]: 'Resource-aware content: -U + 0.1 K'}
    colors = ('#087f8c', '#9b4b9c'); markers = ('o', '^')
    with plt.rc_context(styles):
        fig, axes = plt.subplots(3, 2, figsize=(6.8, 7.2), squeeze=False)
        for panel, ax in zip(data, axes.flat):
            for history in panel['histories']:
                rep, path = history['replication'], history['path']; color = colors[rep]
                x = [r['generation'] for r in path]
                y = [float('nan') if r['best_own_loss'] is None else r['best_own_loss'] for r in path]
                ax.plot(x, y, color=color, lw=1.2)
                ax.plot(x, [r['best_known_including_visible_parent'] for r in path], color=color, ls=':', lw=1.)
                for row in path:
                    if row['observed_loss'] is None:
                        ax.text(row['generation'], .045 + .085 * rep, 'R' + str(rep) + ' null',
                            transform=ax.get_xaxis_transform(), ha='center', va='bottom', color=color,
                            fontsize=6, bbox={'facecolor': 'white', 'edgecolor': 'none', 'pad': 1.2})
                    else:
                        ax.scatter(row['generation'], row['observed_loss'], color=color, marker=markers[rep], s=19, zorder=3)
                        if row['cell_id'] == history['selected_cell_id']:
                            ax.scatter(row['generation'], row['observed_loss'], marker='*', s=68,
                                facecolors='none', edgecolors=color, linewidths=.8, zorder=4)
            reference = panel['histories'][0]['path'][0]['reference_loss']
            ax.axhline(reference, color='#7d8da0', lw=.8, ls='--', zorder=0)
            ax.set(title=method_names[panel['method']] + '\n' + objective_names[panel['objective']],
                   xlabel='Own proposal generation', ylabel='Declared loss (lower is better)', xticks=[0, 1], xlim=(-.15, 1.15))
            ax.grid(axis='y', color='#e9edf0', lw=.6); ax.spines[['top', 'right']].set_visible(False)
        handles = [Line2D([], [], color=colors[i], marker=markers[i], label='History ' + str(i), lw=1.) for i in range(2)]
        handles += [Line2D([], [], color='#56677c', ls='-', label='Best own'),
                    Line2D([], [], color='#56677c', ls=':', label='Best incl. visible parents'),
                    Line2D([], [], color='#7d8da0', ls='--', label='Strong visible reference'),
                    Line2D([], [], color='#56677c', ls='None', marker='*', markerfacecolor='none', label='Frozen own selection')]
        fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.5, .945), ncol=3, frameon=False, fontsize=6.4)
        fig.suptitle('Objective-conditioned institution search: all three methods', y=.99, fontsize=10)
        fig.text(.055, .017, 'One reused development condition; two optimizer seeds, not independent researcher populations.\n'
            'All slots remain. Null labels have no numeric vertical meaning. No method-superiority or truth claim.', fontsize=6.5)
        fig.tight_layout(rect=(.015, .065, .995, .88), h_pad=1.5, w_pad=1.2)
        for ext in ('png', 'svg'):
            fig.savefig(output / ('objective-method-paths.' + ext), dpi=220,
                        metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def export(args):
    source = pinned_revision(ROOT); report = read(args.report); out = args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT) or out.is_relative_to(args.report.resolve().parent):
        raise ValueError('fresh figure output outside renderer source and report data required')
    before = file_sha256(args.report); data = plot_data(report)
    out.mkdir(parents=True); render(report, out)
    save(out / 'manifest.json', {'schema': 'scienceutopia.native-priority-method-paths-figure.v1',
        'renderer_source_commit': source, 'report_file_sha256': before,
        'report_content_sha256': report['content_sha256'], 'plot_data_sha256': digest(data),
        'files': {p.name: file_sha256(p) for p in sorted(out.iterdir())},
        'new_model_calls': 0, 'new_code_executions': 0, 'publication_ready': False})
    if before != file_sha256(args.report) or pinned_revision(ROOT) != source:
        raise ValueError('source or report changed during rendering')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    export(p.parse_args())


if __name__ == '__main__': main()
