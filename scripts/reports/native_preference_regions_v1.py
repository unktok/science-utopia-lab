"""Exact conditional preference regions of the closed T/U observed archive.

No prospective loss, candidate selection, model call or native world is changed.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path

from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-observed-preference-regions.v1'


def exact(value):
    if type(value) not in (float, int):
        raise ValueError('literal finite score required')
    return Fraction(str(value))


def regions(curves, lower=Fraction(1), upper=Fraction(5)):
    """Finite lower envelope, rational arithmetic on literal reported decimals."""
    if not curves or lower >= upper:
        raise ValueError('nonempty finite curves and increasing interval required')
    def at(c):
        values = [a*c+b for a, b in curves]
        best = min(values)
        return [i for i, value in enumerate(values) if value == best]
    cuts = {lower, upper}
    for i, (a, b) in enumerate(curves):
        for d, e in curves[i+1:]:
            if a != d:
                crossing = (e-b)/(a-d)
                if lower < crossing < upper:
                    cuts.add(crossing)
    cuts = sorted(cuts); spans = []
    for left, right in zip(cuts, cuts[1:]):
        winners = at((left+right)/2)
        if spans and spans[-1]['winning_curve_indices'] == winners:
            spans[-1]['right'] = str(right)
        else:
            spans.append({'left': str(left), 'right': str(right), 'winning_curve_indices': winners})
    boundaries = sorted({Fraction(s[k]) for s in spans for k in ('left', 'right')})
    return {'open_intervals': spans,
        'boundaries': [{'center': str(c), 'winning_curve_indices': at(c)} for c in boundaries]}


def summarize(report):
    checked(report)
    if report['schema'] != 'scienceutopia.native-objective-instrument-report.v1':
        raise ValueError('closed native T/U development report required')
    worlds = report['physical_worlds']
    if len({w['identity'] for w in worlds}) != len(worlds) or len({w['seed'] for w in worlds}) != 1:
        raise ValueError('distinct recorded worlds on the same development seed required')
    grouped = {}; failed = []
    for w in worlds:
        scores = w['scores']
        if w['status'] != 'complete':
            if any(v is not None for v in scores.values()):
                raise ValueError('technical null must not acquire a hypothetical loss')
            failed.append(w['identity']); continue
        count = -exact(scores['throughput']); u = exact(scores['content-utility'])
        if count < 0 or count.denominator != 1:
            raise ValueError('original throughput must be a nonnegative integer count')
        # U_3 = -Q+3A. Keep the literal exported values, not newly rerated Q.
        intercept = u-3*count
        grouped.setdefault((count, intercept), []).append(w['identity'])
    pairs = sorted(grouped)
    curves = [{'index': i, 'accepted_occurrences': int(a),
        'derived_fixed_score_sum': str(-b), 'loss_slope': str(a), 'loss_intercept': str(b),
        'physical_world_ids': sorted(grouped[a, b])} for i, (a, b) in enumerate(pairs)]
    geometry = regions(pairs)
    current = [a*3+b for a, b in pairs]; minimum = min(current)
    return {'schema': SCHEMA, 'original_report_content_sha256': report['content_sha256'],
        'scientific_source_commit': report['source_commit'], 'plan_sha256': report['plan_sha256'],
        'audit_content_sha256': report['audit_sha256'], 'development_seed': worlds[0]['seed'],
        'family': {'formula': 'L_c = U_3 + (c-3) A = c A - Q',
            'plotted_center_interval': ['1', '5'], 'actual_optimized_center': '3',
            'retrospective_conditional_analysis': True, 'new_objective_adopted': False},
        'curves': curves, 'geometry': geometry, 'failed_world_ids': sorted(failed),
        'physical_attempts': len(worlds), 'complete_observed_worlds': len(worlds)-len(failed),
        'current_center_winning_curve_indices': [i for i, value in enumerate(current) if value == minimum],
        'scope': 'Lower envelope over observed completed worlds, not global or expected policy optima. '
            'Records, content panels, trajectories and original T/U selections are fixed. The family '
            'is a retrospective preference analysis, not optimization of a new loss or of the center. '
            'A policy reoptimized under another center could induce different future records. '
            'Coincident curves group observed score vectors, not equivalent programs or independent '
            'replications. Failed attempts remain outside the envelope with no loss imputation. '
            'Rational arithmetic represents literal exported decimals, not independent rerating or truth.',
        'new_model_calls': 0, 'new_code_executions': 0, 'new_native_worlds': 0,
        'candidate_reselection': False, 'publication_ready': False}


def render(summary, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.rc_context({'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.hashsalt': SCHEMA}):
        fig, ax = plt.subplots(figsize=(6.6, 3.5))
        colors = ['#67778e', '#b77b35', '#087f8c', '#9c5d8a']
        for curve in summary['curves']:
            a, b = Fraction(curve['loss_slope']), Fraction(curve['loss_intercept'])
            xs = [1., 5.]; ys = [float(a*x+b) for x in xs]
            n = len(curve['physical_world_ids'])
            ax.plot(xs, ys, lw=1.5, color=colors[curve['index'] % len(colors)],
                label=f'A={int(a)}, Q={curve["derived_fixed_score_sum"]} ({n} observed '+('world)' if n == 1 else 'worlds)'))
        for span in summary['geometry']['open_intervals']:
            left, right = float(Fraction(span['left'])), float(Fraction(span['right']))
            i = span['winning_curve_indices'][0]
            ax.axvspan(left, right, alpha=.08, color=colors[i % len(colors)], lw=0)
        for boundary in summary['geometry']['boundaries'][1:-1]:
            c = float(Fraction(boundary['center']))
            ax.axvline(c, color='#a6adb6', ls=':', lw=.9)
            ax.text(c, .98, ' c='+format(c, '.6g'), transform=ax.get_xaxis_transform(), va='top', fontsize=8)
        ax.axvline(3, color='#333333', ls='--', lw=.9, label='Actual optimized center c=3')
        ax.set(xlim=(1, 5), xlabel='Hypothetical content-score center c',
            ylabel='Conditional loss (fixed records)',
            title='Preference regions of the completed observed archive')
        ax.set_axisbelow(True); ax.grid(axis='y', color='#edf0f2')
        ax.legend(loc='upper left', fontsize=8, framealpha=.95)
        fig.text(.02, .02, f'{summary["complete_observed_worlds"]} completed observed worlds; '
            f'{len(summary["failed_world_ids"])} technical nulls excluded without imputation. No new optimization.', fontsize=7.5)
        fig.tight_layout(rect=(0, .06, 1, 1))
        for ext in ('png', 'svg'):
            fig.savefig(output/('preference-regions.'+ext), dpi=240, metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def export(args):
    source = pinned_revision(ROOT); report, output = args.report.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(report.parent) or report.is_relative_to(output):
        raise ValueError('fresh separate output required')
    before = file_sha256(report); summary = summarize(json.loads(report.read_text()))
    output.mkdir(parents=True); save(output/'summary.json', summary); render(summary, output)
    if file_sha256(report) != before or pinned_revision(ROOT) != source:
        raise ValueError('original report or analysis source changed')
    save(output/'manifest.json', {'schema': SCHEMA+'.export', 'analysis_source_commit': source,
        'report_file_sha256': before, 'original_report_content_sha256': summary['original_report_content_sha256'],
        'files': {p.name: file_sha256(p) for p in sorted(output.iterdir())},
        'new_model_calls': 0, 'new_native_worlds': 0, 'candidate_reselection': False})
    print(json.dumps({'complete_observed_worlds': summary['complete_observed_worlds'],
                      'distinct_score_lines': len(summary['curves'])}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    export(p.parse_args())


if __name__ == '__main__':
    main()
