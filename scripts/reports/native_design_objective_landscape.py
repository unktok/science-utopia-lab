"""Post-hoc objective geometry of closed V2 observations, not new search.

No researcher, designer, generated institution or simulator is executed.
Reference features are explicitly recovered from three independent saved scores;
candidate features come from saved measurements. Neither changes frozen losses.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess

from scripts.reports.native_design_reproduce import DATA, ROOT, load_report
from scripts.reports.native_design_tex import summarize
from utopia.system.design_patch import digest

SCHEMA = 'scienceutopia.native-objective-landscape-analysis.v1'
KEYS = ('native.accepted_decisions', 'native.accepted_peer_score_sum', 'native.review_records')
TOL = 1e-10  # Analysis/display ties only; never replaces frozen exact selection.


def finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def features_from_scores(scores):
    """Invert T=-A, E=-Q+.5R, C=4A-Q+.1R, preserving roundoff."""
    if any(not finite(scores.get(k)) for k in ('throughput', 'efficiency', 'selective')):
        raise ValueError('three finite independent saved scores required')
    a = -scores['throughput']
    r = (4*a + scores['efficiency'] - scores['selective']) / .4
    q = .5*r - scores['efficiency']
    # Integer counts are algebraically determined. Keep recovery roundoff explicit.
    if abs(a-round(a)) > TOL or abs(r-round(r)) > TOL or min(a, r, q) < -TOL:
        raise ValueError('scores inconsistent with nonnegative native counts')
    return [round(a), max(0., q), round(r)], {'A': a-round(a), 'R': r-round(r),
                                           'Q_negative_roundoff': min(0., q)}


def loss(profile, alpha, beta):
    if len(profile) != 3 or not all(finite(x) for x in (*profile, alpha, beta)):
        raise ValueError('finite A/Q/R and coefficients required')
    a, q, r = profile
    return alpha*a-q+beta*r


def minima(observations, alpha, beta):
    if not observations:
        raise ValueError('nonempty observed pool required')
    scored = [(x['id'], loss(x['AQR'], alpha, beta)) for x in observations]
    best = min(v for _, v in scored)
    return best, [name for name, v in scored if abs(v-best) <= TOL]


def family(profile):
    a, q, r = profile
    if a == 0 and abs(q) <= TOL and r == 0:
        return 'no-publication-no-review'
    if a > 0 and abs(q) <= TOL and r == 0:
        return 'publication-without-review'
    if a > 0 and q > TOL and r > 0:
        return 'review-backed-publication'
    return 'other'


def analyze(report, *, alphas=None, betas=None):
    # Validates source, digest, all 120 rows, original exact selection and ties.
    table = summarize(report, expected_source=report['source_commit'])
    refs = []
    for name, scores in sorted(report['reference_scores'].items()):
        profile, residual = features_from_scores(scores)
        refs.append({'id': 'reference:'+name, 'AQR': profile,
            'feature_origin': 'algebraic-inversion-of-saved-T-C-E-not-new-raw-measurements',
            'recovery_roundoff': residual, 'original_cross_scores': deepcopy(scores)})
    if len(refs) != 9:
        raise ValueError('nine same-source references required')
    observations = []
    for row in report['all_candidate_rows']:
        if row['status'] != 'complete':
            continue
        metrics = row['metrics']
        if any(metrics.get(k, {}).get('status') != 'measured' for k in KEYS):
            raise ValueError('complete row missing measured A/Q/R')
        profile = [metrics[k]['value'] for k in KEYS]
        if (not all(finite(x) for x in profile) or min(profile) < 0
                or type(profile[0]) is not int or type(profile[2]) is not int):
            raise ValueError('nonnegative measured A/Q/R with integer counts required')
        a, q, r = profile
        expected = {'throughput': -a, 'selective': 4*a-q+.1*r, 'efficiency': -q+.5*r}
        if any(not math.isclose(expected[k], row['cross_scores'][k], abs_tol=1e-12, rel_tol=1e-13)
               for k in expected):
            raise ValueError('measured features disagree with frozen scores')
        observations.append({'id': row['row_id'], 'run': row['run'], 'arm': row['arm'],
            'generation': row['generation'], 'system_fingerprint': row['system_fingerprint'],
            'AQR': profile, 'feature_origin': 'retained-native-measurements',
            'original_cross_scores': deepcopy(row['cross_scores'])})
    if len(observations) != 64:
        raise ValueError('64 complete observations required; nulls never become profiles')
    pooled = refs+observations
    lookup = {r['id']: r for r in pooled}
    alphas = [i/10 for i in range(-20, 61)] if alphas is None else list(alphas)
    betas = [i*3/100 for i in range(51)] if betas is None else list(betas)
    if (not alphas or not betas or any(not finite(v) for v in alphas+betas)
            or any(a >= b for a, b in zip(alphas, alphas[1:]))
            or any(a >= b for a, b in zip(betas, betas[1:]))):
        raise ValueError('finite strictly increasing coefficient axes required')
    categories = ('no-publication-no-review', 'publication-without-review',
                  'review-backed-publication', 'other', 'mixed-family-tie')
    panels = {}; counts = {}
    for scope, pool in (('references', refs), ('all_observations', pooled)):
        image = []; frequency = Counter()
        for beta in betas:
            line = []
            for alpha in alphas:
                _, winners = minima(pool, alpha, beta)
                groups = {family(lookup[name]['AQR']) for name in winners}
                label = next(iter(groups)) if len(groups) == 1 else 'mixed-family-tie'
                frequency[label] += 1
                line.append(categories.index(label))
            image.append(line)
        panels[scope] = image
        counts[scope] = dict(sorted(frequency.items()))
    checks = []
    for name, alpha, beta in (('V2-selective', 4., .1),
                             ('diagnostic-E-not-an-optimized-arm', 0., .5),
                             ('historical-U-formula-on-V2-records-only', 3.25, .05)):
        ref_best, ref_ids = minima(refs, alpha, beta)
        search_best, search_ids = minima(observations, alpha, beta)
        checks.append({'name': name, 'alpha': alpha, 'beta': beta,
            'reference_best': ref_best, 'reference_ids': ref_ids,
            'search_best': search_best, 'search_ids': search_ids,
            'search_minus_reference': search_best-ref_best,
            'post_hoc_observation_selection_not_optimizer_performance': True})
    repeated = []
    groups = defaultdict(list)
    for row in observations:
        groups[row['system_fingerprint']].append(row)
    for fingerprint, rows in sorted(groups.items()):
        if len(rows) < 2:
            continue
        spread = [max(r['AQR'][k] for r in rows)-min(r['AQR'][k] for r in rows)
                  for k in range(3)]
        repeated.append({'system_fingerprint': fingerprint, 'row_ids': [r['id'] for r in rows],
            'profiles': [r['AQR'] for r in rows], 'AQR_range': spread,
            'differs_beyond_analysis_tolerance': any(v > TOL for v in spread)})
    per_history = []
    for run, arms in sorted(report['search_arms'].items()):
        for arm, body in sorted(arms.items()):
            statuses = Counter(r['status'] for r in body['rows'])
            measured = [r for r in body['rows'] if r['status'] == 'complete']
            previous = body['initial_loss']; improvements = []
            for row in body['rows']:
                if row['own_loss'] is not None and row['own_loss'] < previous:
                    improvements.append(row['generation']); previous = row['own_loss']
            per_history.append({'run': run, 'arm': arm, 'statuses': dict(statuses),
                'strict_best_improvement_generations': improvements,
                'completed_count': len(measured), 'best_including_initial': body['best_including_initial'],
                'initial_loss': body['initial_loss'],
                'declared_graph_change_completed_rows': sum(any(
                    r['lineage']['vs_initial']['counts'][k] > 0 for k in
                    ('nodes_added', 'nodes_removed', 'edges_added', 'edges_removed', 'rewired_endpoint_pairs'))
                    for r in measured)})
    # At a fixed cost coefficient, exact pairwise linear crossings are finite.
    # They concern individual saved outcomes, not expected values or global optima.
    slices = []
    for beta in (.05, .1, .5):
        intersections = []
        for i, left in enumerate(pooled):
            for right in pooled[i+1:]:
                da = left['AQR'][0]-right['AQR'][0]
                if da == 0:
                    continue
                alpha = ((left['AQR'][1]-right['AQR'][1])
                         - beta*(left['AQR'][2]-right['AQR'][2]))/da
                if -2 <= alpha <= 6:
                    best, names = minima(pooled, alpha, beta)
                    if left['id'] in names and right['id'] in names:
                        intersections.append(alpha)
        unique = []
        for x in sorted(intersections):
            if not unique or abs(unique[-1]-x) > TOL:
                unique.append(x)
        slices.append({'beta': beta, 'lower_envelope_crossings_alpha': unique})
    numeric = [r for r in report['all_candidate_rows'] if r['arm'].endswith(':parameters')]
    steps = [s for r in numeric for s in r['authoring_diagnostics']['steps']]
    finishes = [s for s in steps if s['compiled_tool'] == 'finish']
    finish_errors = Counter()
    for step in finishes:
        if not isinstance(step['transition_errors'], list):
            raise ValueError('finish diagnosis requires recorded transition errors')
        finish_errors.update(e.get('message', '<structured diagnostic without message>')
                             for e in step['transition_errors'])
    times = [r['physical_evidence']['annual_checkpoints'][-1]['llm_call_stats']['elapsed_seconds']
             for r in report['all_candidate_rows'] if r['status'] == 'complete']
    if any(not finite(v) or v < 0 for v in times):
        raise ValueError('recorded completed-only scientist times required')
    result = {'schema': SCHEMA, 'classification': 'post-hoc-analysis-of-retained-V2-observations',
        'experiment_source_commit': report['source_commit'],
        'input_report_content_sha256': report['content_sha256'],
        'input_audit_content_sha256': report['input_audit_content_sha256'],
        'formula': 'alpha*A - Q + beta*R (minimize)',
        'analysis_tie_tolerance': TOL, 'frozen_exact_selection_changed': False,
        'search_slot_counts': table['counts'], 'reference_observations': refs,
        'complete_search_observations': observations, 'point_checks': checks,
        'coefficient_grid': {'alphas': alphas, 'betas': betas, 'family_categories': list(categories),
            'panels': panels, 'point_counts': counts,
            'grid_count_is_not_probability_volume_or_independent_samples': True},
        'envelope_slices': slices, 'same_fingerprint_repeated_observations': repeated,
        'same_fingerprint_different_AQR_beyond_tolerance': sum(
            r['differs_beyond_analysis_tolerance'] for r in repeated),
        'per_history': per_history,
        'numeric_interface_diagnosis': {
            'slots': len(numeric), 'recorded_steps': len(steps),
            'terminal_reasons': dict(Counter(r['authoring_diagnostics']['terminal_failure_reason'] for r in numeric)),
            'finish_attempts': len(finishes), 'finish_status_counts': dict(Counter(s['status'] for s in finishes)),
            'finish_transition_error_messages': dict(finish_errors),
            'compiled_tool_counts': dict(Counter(s['compiled_tool'] if s['compiled_tool'] is not None
                                               else '<unavailable>' for s in steps)),
            'read_virtual_filename_counts': dict(Counter(s['virtual_filename'] for s in steps
                                                       if s['compiled_tool'] == 'read_file')),
            'steps_without_recorded_transition_error_list': sum(not isinstance(s['transition_errors'], list)
                                                               for s in steps),
            'multiple_step_errors_are_not_independent_failed_candidates': True,
            'single_root_cause_established': False},
        'completed_development_scientist_call_seconds': {
            'observations': len(times), 'minimum': min(times), 'median': statistics.median(times),
            'maximum': max(times), 'sum': math.fsum(times),
            'scope': 'Saved completed-world model-call component only, not end-to-end time or 4-year forecast.',
            'failures_designer_load_container_and_other_time_excluded': True},
        'new_model_calls': 0, 'new_native_worlds': 0,
        'new_generated_code_executions': 0, 'held_out_values_used_to_reselect': False,
        'interpretation': ['Finite saved observations, not an optimal policy frontier.',
            'Post-hoc E winners were not E-optimized or selection-fixed for this analysis.',
            'A single-observation advantage can reflect fresh researcher responses or selection bias.',
            'Controller histories share development world seed42; no method superiority inference.',
            'Reference A/Q/R were algebraically inverted, not newly read raw measurements.']}
    result['content_sha256'] = digest(result)
    return result


def plot(data, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Patch
    import numpy as np
    g = data['coefficient_grid']; xs = g['alphas']; ys = g['betas']
    colors = ['#e8b55b', '#45a8b0', '#5356a8', '#8b8b8b', '#cf74aa']
    cmap = ListedColormap(colors); norm = BoundaryNorm(np.arange(-.5, 5.5), cmap.N)
    with plt.rc_context({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.hashsalt': 'native-objective-landscape-v1'}):
        fig, axes = plt.subplots(1, 2, figsize=(11.5, 6.1))
        for ax, scope, title in zip(axes, ('references', 'all_observations'),
                                   ('Nine reference observations', 'References + 64 completed search observations')):
            ax.pcolormesh(xs, ys, g['panels'][scope], shading='nearest', cmap=cmap, norm=norm)
            for label, x, y in (('C', 4., .1), ('E*', 0., .5), ('U*', 3.25, .05)):
                ax.scatter([x], [y], marker='o', s=32, color='white', edgecolor='#202020', zorder=4)
                ax.annotate(label, (x, y), xytext=(5, 6), textcoords='offset points', fontsize=9)
            ax.set(title=title, xlabel='alpha: acceptance coefficient', ylabel='beta: review-cost coefficient',
                   xlim=(xs[0], xs[-1]), ylim=(ys[0], ys[-1]))
        labels = ['No publication / no review', 'Publication without review',
                  'Review-backed publication', 'Other', 'Mixed-family tie']
        fig.legend(handles=[Patch(facecolor=c, label=l) for c, l in zip(colors, labels)],
                   loc='lower center', bbox_to_anchor=(.5, .105), ncol=3, frameon=False, fontsize=9)
        fig.suptitle('Which observed behavior minimizes alpha A - Q + beta R?', fontsize=14)
        fig.text(.5, .035, 'Post-hoc development observations, not new objective-conditioned search. '
                 'C: original V2 loss; E*/U*: diagnostic formulas only.\n'
                 'Colors describe observed outcomes, not general policy equivalence. '
                 'No method or held-out superiority claim.', ha='center', fontsize=9)
        fig.subplots_adjust(top=.86, bottom=.27, wspace=.24)
        for ext in ('png', 'svg'):
            fig.savefig(Path(output)/('observed-objective-map.'+ext), dpi=180,
                        metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if args.output.exists() or args.output.is_symlink() or ROOT.is_relative_to(output):
        raise ValueError('fresh non-source-root destination required')
    git = lambda *a: subprocess.check_output(['git', '-C', str(ROOT), *a], text=True).strip()
    source = git('rev-parse', 'HEAD')
    if git('status', '--porcelain'):
        raise ValueError('clean committed analysis source required')
    names = [DATA+'manifest.json', DATA+'closed-report.json.gz']
    inputs = {name: (ROOT/name).read_bytes() for name in names}
    for name, body in inputs.items():
        if subprocess.check_output(['git', '-C', str(ROOT), 'show', source+':'+name]) != body:
            raise ValueError('retained input differs from committed source')
    report = load_report(inputs[names[1]], json.loads(inputs[names[0]]))
    data = analyze(report)
    output.mkdir(parents=True)
    (output/'analysis.json').write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False)+'\n')
    plot(data, output)
    def sha(body):
        return hashlib.sha256(body).hexdigest()
    manifest = {'schema': SCHEMA+'.files', 'analysis_source_commit': source,
        'input_files': {n: sha(b) for n, b in inputs.items()},
        'input_report_content_sha256': report['content_sha256'],
        'analysis_content_sha256': data['content_sha256'],
        'files': {p.name: sha(p.read_bytes()) for p in sorted(output.iterdir())},
        'new_model_calls': 0, 'new_native_worlds': 0, 'new_generated_code_executions': 0}
    if git('rev-parse', 'HEAD') != source or any((ROOT/n).read_bytes() != b for n, b in inputs.items()):
        raise ValueError('source or numerical input changed during analysis')
    # Fresh output may be tracked later; it is the only permitted new worktree state.
    status_args = ['status', '--porcelain', '--', '.']
    if output.is_relative_to(ROOT):
        status_args.append(':(exclude)'+str(output.relative_to(ROOT)))
    if git(*status_args):
        raise ValueError('unrelated source changes during analysis; preserve partial output')
    manifest['content_sha256'] = digest(manifest)
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'output': str(output), 'content_sha256': data['content_sha256'],
                      'completed_observations': len(data['complete_search_observations'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
