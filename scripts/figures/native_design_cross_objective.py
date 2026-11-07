"""Every selected/reference policy scored under all three fixed V2 losses.

Raw unused-condition scores, explicit missingness and exact physical sharing.
No ranking, normalization, cross-loss aggregation or inferential intervals.
"""
import argparse
from copy import deepcopy
import hashlib
from pathlib import Path

from scripts.figures.native_design_evaluation import panel_data, METHODS, COLORS
from scripts.reports.native_design_benchmark import SCHEMA, descriptive, number
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json, write_json_atomic

REFERENCES = ('legacy', 'open-seed', 'open-rank-rate', 'open-accept-all',
              'open-reject-all', 'open-score-3', 'open-score-4',
              'open-no-review-accept-all', 'open-no-review-reject-all')
REFERENCE_TITLES = ('Legacy', 'Editable seed', 'Rank / rate', 'Accept all', 'Reject all',
                    'Review score >= 3', 'Review score >= 4', 'No review / accept', 'No review / reject')
METHOD_TITLES = ('Numeric', 'Code / fixed graph', 'Code + graph', 'Technical-only', 'Uniform numeric')
LOSSES = ('throughput', 'selective', 'efficiency')
LOSS_TITLES = ('Throughput\nT = -A', 'Selective production\nC = 4A - Q + 0.1R',
               'Reviewed utility (diagnostic)\nE = -Q + 0.5R')
SEEDS = (31001, 31013, 31019, 31033, 31039)
CONDITIONS = {(s, 2) for s in SEEDS} | {(31001, 4)}


def cross_objective_data(report):
    # Keep the existing own-objective pair/source-score consistency checks.
    # This projection additionally exposes the third loss and shared raw levels.
    panel_data(report)
    if set(report['reference_scores']) != set(REFERENCES):
        raise ValueError('all nine fixed V2 references must be retained')
    arms = [o + ':' + m for o in ('throughput', 'selective') for m in METHODS]
    labels = ['reference:' + r for r in REFERENCES] + ['selected:' + arm for arm in arms]
    selected = report['selection']['selected']
    expected = {l for l in labels if l.startswith('reference:') or selected[l[9:]]['system'] is not None}
    jobs = report['evaluation']; lookup = {}; policies = {}; physical = {}; job_ids = set()
    if report['physical_evaluation_jobs'] != len(jobs) or report['logical_evaluation_labels'] != len(expected):
        raise ValueError('physical/logical evaluation counts differ')
    for job in jobs:
        condition = job['seed'], job['years']; identity = job['policy_sha256']
        if condition not in CONDITIONS or type(job['seed']) is not int or type(job['years']) is not int:
            raise ValueError('exact unused-condition seeds/horizons required')
        if (not isinstance(job['job_id'], str) or not job['job_id'] or job['job_id'] in job_ids
                or not isinstance(identity, str) or not identity):
            raise ValueError('unique physical job and explicit policy identities required')
        job_ids.add(job['job_id'])
        if not job['labels'] or len(set(job['labels'])) != len(job['labels']) or not set(job['labels']) <= expected:
            raise ValueError('undeclared, repeated or unselected evaluated label')
        if set(job['cross_scores']) != set(LOSSES):
            raise ValueError('all three exact fixed losses required')
        for value in job['cross_scores'].values(): number(value)
        physical_key = identity, *condition
        if physical_key in physical:
            raise ValueError('same exact policy/condition split into multiple physical jobs')
        physical[physical_key] = job['job_id']
        for label in job['labels']:
            key = label, *condition
            if key in lookup: raise ValueError('duplicate label/condition')
            lookup[key] = job
            if label in policies and policies[label] != identity:
                raise ValueError('selected policy changes across evaluation conditions')
            policies[label] = identity
            if label.startswith('selected:') and selected[label[9:]]['policy_sha256'] != identity:
                raise ValueError('evaluated policy differs from fixed selected identity')
    if set(lookup) != {(l, s, y) for l in expected for s, y in CONDITIONS}:
        raise ValueError('missing or extra logical evaluation condition')
    for arm, choice in selected.items():
        if (choice['system'] is not None and choice['selected_row_id'] == 'reference:open-seed'
                and policies['selected:' + arm] != policies['reference:open-seed']):
            raise ValueError('initial selection must share the actual initial policy/jobs')
    # The existing figure checks own-objective pairs. Here the diagnostic and
    # cross-objective pair blocks must also match the exact physical levels.
    for arm in arms:
        if selected[arm]['system'] is None: continue
        for reference in REFERENCES:
            for loss in LOSSES:
                for years, seeds in ((2, SEEDS), (4, (31001,))):
                    block = report['paired_vs_all_references'][arm][reference][loss][str(years)]
                    expected_pairs = []
                    for seed in seeds:
                        a, b = lookup['selected:' + arm, seed, years], lookup['reference:' + reference, seed, years]
                        x, y = a['cross_scores'][loss], b['cross_scores'][loss]
                        expected_pairs.append({'seed': seed, 'years': years, 'target_job_id': a['job_id'],
                            'reference_job_id': b['job_id'], 'physically_shared': a['job_id'] == b['job_id'],
                            'target_loss': x, 'reference_loss': y, 'difference': x - y if x is not None and y is not None else None})
                    for pair in block['pairs']:
                        for key in ('target_loss', 'reference_loss', 'difference'): number(pair[key])
                        if type(pair['physically_shared']) is not bool:
                            raise ValueError('physical-sharing flag must be Boolean')
                    if block['pairs'] != expected_pairs or block['summary'] != descriptive(expected_pairs, 'difference'):
                        raise ValueError('cross-objective pairs differ from exact physical scores/sharing')
    groups = {}
    for label in labels:
        if label in policies: groups.setdefault(policies[label], 'P' + str(len(groups) + 1).zfill(2))
    panels = []
    for years, seeds in ((2, SEEDS), (4, (31001,))):
        rows = []
        for index, label in enumerate(labels):
            is_reference = label.startswith('reference:')
            title = ('R' + str(index + 1) + ' ' + REFERENCE_TITLES[index] if is_reference else
                ('T' if index < 14 else 'C') + ' | ' + METHOD_TITLES[(index - 9) % 5])
            identity = policies.get(label); available = label in expected
            choice = None if is_reference else selected[label[9:]]
            initial = choice is not None and choice['selected_row_id'] == 'reference:open-seed'
            if initial: title += '*'
            cells = {}
            for loss in LOSSES:
                points = [{'seed': seed, 'years': years, 'job_id': lookup[label, seed, years]['job_id'],
                    'policy_sha256': identity,
                    'observation_status': lookup[label, seed, years]['observation_status'],
                    'value': lookup[label, seed, years]['cross_scores'][loss],
                    'shared_labels': deepcopy(lookup[label, seed, years]['labels'])}
                    for seed in seeds] if available else []
                cells[loss] = {'points': points, 'summary': descriptive(points, 'value') if available else None}
            rows.append({'label': label, 'display': title, 'selection_available': available,
                'search_objective': None if is_reference else label[9:].split(':')[0],
                'policy_sha256': identity, 'physical_group': groups.get(identity),
                'initial_reference_selected': initial,
                'selected_row_id': None if choice is None else choice['selected_row_id'],
                'all_tied_row_ids': [] if choice is None else deepcopy(choice['all_tied_row_ids']),
                'cells': cells})
        panels.append({'years': years, 'seeds': list(seeds), 'single_seed_diagnostic': years == 4, 'rows': rows})
    data = {'schema': SCHEMA + '.cross-objective-plot-data',
        'input_report_content_sha256': report['content_sha256'], 'classification': report['classification'],
        'loss_order': list(LOSSES), 'panels': panels, 'physical_policies': len(groups),
        'physical_evaluation_jobs': len(jobs), 'logical_evaluation_labels': len(expected),
        'display_order_is_not_ranking_or_search_chronology': True,
        'arm_label_is_not_a_claim_of_authored_invention_or_actual_graph_edit': True,
        'losses_normalized_or_aggregated': False, 'horizons_pooled': False, 'null_losses_imputed': False,
        'shared_labels_count_as_new_replication': False, 'confidence_intervals_or_significance_claimed': False,
        'scope': 'All fixed selected representatives and all references under T/C/E. Raw levels and available-score means, not expected performance; E is diagnostic, never a new search objective.'}
    data['content_sha256'] = digest(data)
    return data


def _render(panel, data, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    with plt.rc_context({'font.size': 8, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.fonttype': 'none'}):
        fig, axes = plt.subplots(1, 3, figsize=(8.2, 7.7), sharey=True)
        fig.subplots_adjust(left=.265, right=.94, top=.79, bottom=.17, wspace=.55)
        for ax, loss, title in zip(axes, LOSSES, LOSS_TITLES):
            for i, row in enumerate(panel['rows']):
                cell = row['cells'][loss]
                if not row['selection_available']:
                    ax.text(.5, i, 'No selection', transform=ax.get_yaxis_transform(),
                            ha='center', va='center', color='#666', fontsize=7)
                    continue
                for j, point in enumerate(cell['points']):
                    y = i + (j - (len(panel['seeds']) - 1) / 2) * .12
                    if point['value'] is None:
                        ax.plot(1.025, y, marker='x', color=COLORS[j], ms=4,
                                transform=ax.get_yaxis_transform(), clip_on=False, ls='none')
                    else:
                        ax.scatter(point['value'], y, color=COLORS[j], s=13, zorder=3)
                summary = cell['summary']
                if summary['mean'] is not None and panel['years'] == 2:
                    ax.scatter(summary['mean'], i, marker='D', facecolors='none',
                               edgecolors='#222', s=34, lw=.9, zorder=4)
                ax.text(1.115, i, str(summary['available']) + '/' + str(summary['scheduled']),
                        transform=ax.get_yaxis_transform(), fontsize=6.7, va='center', color='#555')
            ax.set(title=title, xlabel='Raw loss (lower is better)',
                   yticks=range(len(panel['rows'])), ylim=(len(panel['rows']) - .55, -.55))
            ax.tick_params(axis='y', length=0); ax.grid(axis='x', alpha=.2)
            ax.axhline(8.5, color='#bbb', lw=.8); ax.axhline(13.5, color='#ddd', lw=.8)
            ax.axvline(0, color='#aaa', lw=.6, ls='--')
            if not any(p['value'] is not None for r in panel['rows'] for p in r['cells'][loss]['points']):
                ax.set_xlim(-.5, .5)
        axes[0].set_yticklabels([r['display'] + (' [' + r['physical_group'] + ']' if r['physical_group'] else '')
                                for r in panel['rows']])
        horizon = 'Five unused seeds / two years' if panel['years'] == 2 else 'Four-year SINGLE-SEED diagnostic'
        fig.suptitle('Objective-conditioned policies, common cross-scores\n' + horizon, fontsize=12, y=.99)
        handles = [Line2D([0], [0], marker='o', color=COLORS[j], ls='none', label='seed ' + str(s))
                   for j, s in enumerate(panel['seeds'])]
        if panel['years'] == 2:
            handles.append(Line2D([0], [0], marker='D', markerfacecolor='none', color='#222',
                                  ls='none', label='Available-score mean'))
        handles.append(Line2D([0], [0], marker='x', color='#555', ls='none', label='Null: outside data axis'))
        fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.57, .916),
                   ncol=3, frameon=False, fontsize=7.5)
        fig.text(.265, .105, 'T/C labels: objective used for search; all rows receive all three scores. E is diagnostic.\n'
            '[Pxx] identifies shared exact policies/jobs, not additional independent observations.\n'
            'Right gutter: available/scheduled scores. Missing scores are not zero. No confidence intervals.\n'
            'Separate loss scales; no ranking, cross-loss average or two/four-year pooling.\n'
            '* Initial seed selected; not a successful invented replacement for a failed proposal.', fontsize=7, va='top')
        if data['classification'].startswith('SCRIPTED'):
            fig.text(.55, .5, 'SCRIPTED QA - NOT EXPERIMENTAL RESULTS', ha='center', va='center',
                     rotation=30, color='#a51f2b', alpha=.23, fontsize=17)
        for suffix in ('png', 'svg'):
            fig.savefig(output / ('cross-objective-' + str(panel['years']) + 'y.' + suffix), dpi=180)
        plt.close(fig)


def plot_cross_objective(report, output):
    data = cross_objective_data(report); output = Path(output)
    if output.exists(): raise ValueError('fresh cross-objective figure directory required')
    output.mkdir(parents=True)
    for panel in data['panels']: _render(panel, data, output)
    write_json_atomic(output / 'plot-data.json', data, sort_keys=True, allow_nan=False, indent=2)
    manifest = {'schema': SCHEMA + '.cross-objective-figures',
        'input_report_content_sha256': report['content_sha256'], 'plot_data_content_sha256': data['content_sha256'],
        'plot_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
        'new_model_calls': 0, 'new_code_executions': 0, 'null_losses_imputed': False}
    manifest['content_sha256'] = digest(manifest)
    write_json_atomic(output / 'manifest.json', manifest, sort_keys=True, allow_nan=False, indent=2)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv); before = args.report.read_bytes()
    result = plot_cross_objective(decode_json(before.decode(), strict=True, finite_floats=True), args.output)
    if args.report.read_bytes() != before: raise ValueError('input report changed during figure rendering')
    print({'content_sha256': result['content_sha256'], 'files': len(result['files'])})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
