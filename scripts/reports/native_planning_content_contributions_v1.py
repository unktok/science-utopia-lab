"""Recorded T/U preferences and signed accepted-content contributions after closure."""
import argparse
import csv
from fractions import Fraction
import json
import math
from pathlib import Path
from types import SimpleNamespace

from scripts.reports.native_objective_preference_geometry_v1 import geometry
from scripts.reports.native_planning_objective_loop_v1 import export as source_export
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest
from utopia.system.native_planning_controls import ORDER
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-planning-content-contributions.v1'
OBJECTIVES = ['throughput', 'content-utility']


def contributions(rows, cache):
    result = []
    for i, row in enumerate(rows):
        rating = row['rating']; scores = [r['score'] for r in rating['ratings']]
        key = rating['content_sha256']
        if (type(row['year']) is not int or not 1 <= row['year'] <= 4
                or not isinstance(row['paper_id'], str) or not row['paper_id']
                or not isinstance(key, str) or len(key) != 64 or any(c not in '0123456789abcdef' for c in key)
                or rating['status'] != 'measured' or len(scores) != 3
                or any(type(s) is not int or not 1 <= s <= 5 for s in scores)
                or rating['mean_score'] != math.fsum(scores) / 3
                or (key in cache and cache[key] != scores)):
            raise ValueError('literal consistent three-critic accepted records required')
        cache[key] = scores
        exact = Fraction(sum(scores), 3) - 3
        result.append({'occurrence_index': i, 'year': row['year'], 'paper_id': row['paper_id'],
            'content_sha256': key, 'critic_scores': scores, 'mean_score': rating['mean_score'],
            'recorded_centered_utility': rating['mean_score'] - 3,
            'exact_centered_utility': str(exact),
            'sign': 'positive' if exact > 0 else 'negative' if exact < 0 else 'zero'})
    return result


def summarize(report):
    checked(report)
    if (report['schema'] != 'scienceutopia.native-planning-objective-report.v1'
            or report['score_order'] != OBJECTIVES or len(report['slots']) != 6
            or [r['label'] for r in report['references']] != list(ORDER)
            or report['interpretation']['held_out_evaluation']
            or report['interpretation']['new_model_calls'] or report['interpretation']['new_code_executions']):
        raise ValueError('complete original planning T/U development report required')
    names = {r['physical_job']: 'R'+str(i+1) for i, r in enumerate(report['references'])}
    for slot in report['slots']:
        if slot['physical_job'] is not None:
            names[slot['physical_job']] = ('T' if slot['objective'] == 'throughput' else 'U') + str(slot['generation'])
    if (set(names) != {w['identity'] for w in report['physical_worlds']}
            or len(names) != len(report['physical_worlds'])
            or {(s['objective'], s['generation']) for s in report['slots']} != {(o, g) for o in OBJECTIVES for g in range(3)}):
        raise ValueError('all original references and unique own slots/worlds required')
    cache = {}; worlds = []
    for world in report['physical_worlds']:
        row = {k: clone(world[k]) for k in ('identity', 'role', 'seed', 'status', 'scores')}
        row.update(label=names[world['identity']], accepted_records=None, sign_counts=None,
                   recorded_utility_by_sign=None, exact_utility_by_sign=None, exact_utility_sum=None)
        if world['status'] == 'complete':
            measurement, = world['measurements']; observer = checked(measurement['common_content_observer'])
            records = contributions(observer['accepted_decisions'], cache)
            n = len(records); q = math.fsum(r['mean_score'] for r in records)
            u = math.fsum(r['recorded_centered_utility'] for r in records)
            expected = {'native.accepted_decisions': n, 'native.common_content_score_sum': q,
                        'native.common_content_utility_sum': u}
            if (any(measurement['metrics'][k] != {'status': 'measured', 'value': v} for k, v in expected.items())
                    or world['scores'] != {'throughput': -float(n), 'content-utility': -u}
                    or observer['unique_contents'] != len({r['content_sha256'] for r in records})):
                raise ValueError('original measurements and operational T/U scores differ')
            signs = ('positive', 'zero', 'negative')
            row.update(accepted_records=records,
                sign_counts={s: sum(r['sign'] == s for r in records) for s in signs},
                recorded_utility_by_sign={s: math.fsum(r['recorded_centered_utility'] for r in records if r['sign'] == s) for s in signs},
                exact_utility_by_sign={s: str(sum((Fraction(r['exact_centered_utility']) for r in records if r['sign'] == s), Fraction(0))) for s in signs},
                exact_utility_sum=str(sum((Fraction(r['exact_centered_utility']) for r in records), Fraction(0))))
        elif any(v is not None for v in world['scores'].values()):
            raise ValueError('failed world must retain missing loss, not a zero contribution')
        worlds.append(row)
    result = {'schema': SCHEMA, 'original_report_content_sha256': report['content_sha256'],
        'scientific_source_commit': report['source_commit'], 'plan_sha256': report['plan_sha256'],
        'audit_content_sha256': report['audit_sha256'], 'worlds': worlds,
        'unavailable_own_slots': [{k: clone(s[k]) for k in ('objective', 'generation', 'status', 'physical_job')}
            for s in report['slots'] if s['status'] != 'complete'],
        'recorded_preference_geometry': geometry(report['physical_worlds'], OBJECTIVES),
        'scope': 'Every accepted decision occurrence, including repeated paper/content records, '
            'contributes once. Signs use the fixed three-position mean minus the declared center3. '
            'Rational components explain arithmetic; literal floating-point losses alone determine '
            'the reported observed preferences, and no original loss or selection is recomputed in '
            'a different numeric representation. Rejected or unproduced content is not rerated. '
            'These realized accepted sets and opinions are not causal mediation, attainable subset '
            'optima, verified science, independent critic errors or independent optimizer histories.',
        'loss_changed': False, 'candidate_reselection': False, 'causal_mediation_claimed': False,
        'new_model_calls': 0, 'new_native_worlds': 0, 'new_code_executions': 0, 'publication_ready': False}
    result['content_sha256'] = digest(result); return result


def render(report, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    worlds = report['worlds']; colors = {'positive': '#087f8c', 'zero': '#a8b0bc', 'negative': '#b47835'}
    with plt.rc_context({'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False, 'svg.hashsalt': SCHEMA}):
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
        for i, world in enumerate(worlds):
            if world['status'] != 'complete':
                for ax in axes: ax.text(i, .02, 'null', transform=ax.get_xaxis_transform(), ha='center', color='#a9444a')
                continue
            bottom = 0
            for sign in colors:
                value = world['sign_counts'][sign]
                axes[0].bar(i, value, bottom=bottom, color=colors[sign], width=.65); bottom += value
            for sign in ('positive', 'negative'):
                axes[1].bar(i, world['recorded_utility_by_sign'][sign], color=colors[sign], width=.65)
        axes[0].set(title='Accepted decision occurrences', ylabel='Count N (T = -N)')
        axes[1].set(title='Signed fixed-content contributions', ylabel='Recorded utility sum (U = -sum)')
        complete = [w for w in worlds if w['status'] == 'complete']
        axes[0].set_ylim(0, max(1, 1.12 * max((sum(w['sign_counts'].values()) for w in complete), default=0)))
        low = min((w['recorded_utility_by_sign']['negative'] for w in complete), default=0)
        high = max((w['recorded_utility_by_sign']['positive'] for w in complete), default=0)
        axes[1].set_ylim(min(0, 1.12 * low), max(1, 1.12 * high))
        for ax in axes:
            ax.set(xticks=range(len(worlds)), xticklabels=[w['label'] for w in worlds]); ax.axhline(0, color='#8c96a2', lw=.8)
            ax.grid(axis='y', color='#eeeeee'); ax.set_axisbelow(True)
        from matplotlib.patches import Patch
        fig.legend(handles=[Patch(color=c, label=s+' centered content opinion') for s, c in colors.items()],
                   loc='lower center', bbox_to_anchor=(.5, .09), ncol=3, frameon=False, fontsize=7)
        fig.suptitle('What the two recorded losses count', fontsize=11)
        fig.text(.04, .025, 'R1–R8 retain the original reference order; T/U labels identify own generations. '
                 'Unavailable slots remain in the table. No rerating or reselection.', fontsize=7)
        fig.tight_layout(rect=(0, .18, 1, .94))
        for ext in ('png', 'svg'): fig.savefig(output / ('accepted-content-contributions.'+ext), dpi=200,
            metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def export(args):
    output = args.output.resolve(); source = pinned_revision(ROOT)
    if output.exists(): raise ValueError('fresh output required')
    source_export(SimpleNamespace(run=args.run, audit_one=args.audit_one, audit_two=args.audit_two, output=output/'source-report'))
    path = output/'source-report/report.json'; report = summarize(json.loads(path.read_text())); before = file_sha256(path)
    save(output/'report.json', {k: v for k, v in report.items() if k != 'content_sha256'}); render(report, output)
    with (output/'accepted-records.csv').open('x', newline='') as stream:
        fields = ['world', 'label', 'occurrence_index', 'year', 'paper_id', 'content_sha256',
                  'mean_score', 'recorded_centered_utility', 'exact_centered_utility', 'sign']
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for world in report['worlds']:
            for row in world['accepted_records'] or []:
                writer.writerow({'world': world['identity'], 'label': world['label'], **{k: row[k] for k in fields[2:]}})
    if file_sha256(path) != before or pinned_revision(ROOT) != source: raise ValueError('source report or reader changed')
    save(output/'manifest.json', {'schema': SCHEMA+'.export', 'analysis_source_commit': source,
        'original_report_file_sha256': before, 'report_content_sha256': report['content_sha256'],
        'files': {str(p.relative_to(output)): file_sha256(p) for p in sorted(output.rglob('*')) if p.is_file()},
        'new_model_calls': 0, 'new_native_worlds': 0, 'candidate_reselection': False})
    print(json.dumps({'worlds': len(report['worlds']), 'content_sha256': report['content_sha256']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'audit-one', 'audit-two', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__': main()
