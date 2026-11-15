"""Separate-study cost/output graphics from actual closed development readouts."""
import argparse
from collections import defaultdict
from fractions import Fraction
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked, save
from utopia.utils.data_utils import file_sha256

SCHEMA = 'scienceutopia.native-resource-cost-development-summary.v1'


def summarize(reports):
    groups = []
    for report in reports:
        if report['schema'] != 'scienceutopia.native-resource-cost-readout.v1':
            raise ValueError('closed development resource readout required')
        points, unknown = defaultdict(list), []
        for w in report['worlds']:
            if w['resource_cost_status'] == 'unknown':
                if w['resource_cost'] is not None:
                    raise ValueError('unknown resource cost must not have a numerical value')
                unknown.append(w['identity'])
                continue
            if w['resource_cost_status'] != 'measured' or w['status'] != 'complete':
                raise ValueError('complete measured resource-cost world required')
            points[(w['resource_cost']['value'], w['accepted_decisions'])].append(w['identity'])
        groups.append({'scope': report['scope'], 'input_content_sha256': report['content_sha256'],
            'measured_worlds': sum(len(v) for v in points.values()), 'unknown_worlds': unknown,
            'observed_points': [{'collected_activity_cost': k, 'accepted_decisions': a,
                                 'physical_worlds': members} for (k, a), members in sorted(points.items())]})
    dev = next(r for r in reports if r['scope'] == 'longitudinal-development')
    by = {w['identity']: w for w in dev['worlds']}
    r7, hand = [by[k] for k in ('workflow-reference-r7-original', 'workflow-reference-post-funding-cost')]
    da = hand['accepted_decisions'] - r7['accepted_decisions']
    dk = Fraction(str(hand['resource_cost']['value'])) - Fraction(str(r7['resource_cost']['value']))
    cross = None if dk == 0 else Fraction(da) / dk
    return {'schema': SCHEMA, 'studies': groups,
        'fixed_observed_pair_algebra': {'left': r7['identity'], 'right': hand['identity'],
            'candidate_new_loss_not_adopted': '-accepted_decisions + lambda * collected_activity_cost',
            'right_minus_left_accepted': da, 'right_minus_left_cost': str(dk),
            'equal_loss_lambda': None if cross is None else str(cross),
            'lambda_units': 'accepted decisions per native resource unit',
            'scope': 'Algebra of two already observed development policies only; not a new optimization, '
                'prospective objective choice, expected frontier, causal cost intervention or held-out selection.'},
        'new_model_calls': 0, 'new_native_worlds': 0, 'loss_changed': False,
        'policy_selection': False, 'studies_pooled': False, 'publication_ready': False}


def render(summary, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    with plt.rc_context({'font.size': 11, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.hashsalt': 'native-resource-cost-paper-v1'}):
        fig, axes = plt.subplots(1, 2, figsize=(10, 5.2), sharex=True, sharey=True)
        fig.subplots_adjust(left=.08, right=.975, bottom=.23, top=.79, wspace=.15)
        for ax, study in zip(axes, summary['studies']):
            for point in study['observed_points']:
                k, a = point['collected_activity_cost'], point['accepted_decisions']
                if study['scope'] == 'longitudinal-development':
                    label, color = ('R7 + all 10 valid own policies\n11 coincident outcomes', '#254a70') if k == 190 else ('Hand control', '#ac6f18')
                    offset, align = ((7, -29), 'left') if k == 190 else ((-7, 8), 'right')
                else:
                    label = {20: 'Direct assignment', 14: 'Native choice', 16: 'Native choice + advice'}[a]
                    color = '#ac6f18' if a == 20 else '#254a70'
                    offset, align = (-8, 8), 'right'
                ax.scatter([k], [a], color=color, s=55, edgecolor='white', linewidth=.7, zorder=4)
                ax.annotate(label, (k, a), textcoords='offset points', xytext=offset,
                            ha=align, va='bottom', fontsize=10, color=color)
            ax.set(xlim=(185, 205), ylim=(12, 22), xticks=[190, 200], yticks=[14, 16, 18, 20],
                   xlabel='Collected activity resources (K)')
            ax.grid(color='#e7ebee', linewidth=.7)
        axes[0].set(title='A  Closed longitudinal development', ylabel='Accepted decision occurrences (A)')
        axes[1].set(title='B  Closed original-choice controls')
        fig.suptitle('Observed output–resource support, not a new optimization', y=.965, fontsize=15)
        fig.text(.5, .865, 'Costs reconstructed with each original checkpoint decoder and native ledger.',
                 ha='center', fontsize=11, color='#46515d')
        fig.text(.08, .115, 'A: 12 complete worlds; 2 failed own worlds retain unknown cost.  B: 3 complete hand controls.',
                 fontsize=10, color='#46515d')
        fig.text(.08, .065, 'Separate studies, one known development seed each; no pooled frontier or independent error bars.',
                 fontsize=10, color='#46515d')
        for ext in ('png', 'svg'):
            fig.savefig(output / ('output-resource-support.' + ext), dpi=200,
                        metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development', type=Path, required=True)
    parser.add_argument('--choices', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh figure/summary output required')
    inputs = [args.development, args.choices]
    reports = [checked(json.loads(p.read_text())) for p in inputs]
    if [r['scope'] for r in reports] != ['longitudinal-development', 'legacy-choice-controls']:
        raise ValueError('separate explicitly ordered development and control studies required')
    summary = summarize(reports)
    args.output.mkdir(parents=True)
    save(args.output / 'summary.json', summary)
    render(summary, args.output)
    save(args.output / 'manifest.json', {
        'schema': SCHEMA + '.export', 'inputs': {str(p): file_sha256(p) for p in inputs},
        'renderer_sha256': file_sha256(__file__),
        'files': {p.name: file_sha256(p) for p in sorted(args.output.iterdir())},
        'new_model_calls': 0, 'visual_review_complete': False})


if __name__ == '__main__':
    main()
