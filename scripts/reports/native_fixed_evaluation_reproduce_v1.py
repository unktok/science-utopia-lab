"""Recompute portable fixed-policy numbers/figures, not the original raw audit."""
import argparse
import csv
import io
import json
import math
from pathlib import Path

from scripts.reports.native_design_benchmark import descriptive, number
from scripts.reports.native_fixed_evaluation_v1 import SCHEMA, render_paths
from scripts.reports.pre_scale_search_reproduce_v1 import METRICS, TERMS
from scripts.reports.pre_scale_search_v1 import render_evaluation
from scripts.run_native_fixed_candidate_evaluation_v1 import REFERENCES, SEEDS
from utopia.optimization.native_numeric_designer import checked, save
from utopia.utils.data_utils import file_sha256

ARMS = tuple(o + ':' + m for m in ('parameters', 'code-fixed-graph', 'code-and-graph')
             for o in ('throughput', 'efficiency'))
FILES = ('report.json', 'physical-components.csv', 'stopped-search-paths.png',
         'stopped-search-paths.svg', 'selection-fixed-common-scores.png',
         'selection-fixed-common-scores.svg')


def validate(r):
    checked(r)
    if (r['schema'] != SCHEMA or r['original_search_status'] != 'stopped'
            or r['evaluation_seeds'] != list(SEEDS) or set(r['fixed_selection']) != set(ARMS)):
        raise ValueError('exact separate fixed-evaluation report required')
    slots = r['search_slots']
    order = [(arm, g) for g in (0, 1) for arm in ARMS[g:] + ARMS[:g]]
    if ([(s['arm'], s['generation']) for s in slots] != order
            or [s['slot_index'] for s in slots] != list(range(12))
            or [i for i, s in enumerate(slots) if s['status'] == 'not-submitted'] != [11]):
        raise ValueError('all chronological stopped-prefix slots required')
    for s in slots:
        if s['loss'] != s['cross_scores'][s['arm'].split(':')[0]]:
            raise ValueError('assigned development loss differs from retained score')
        if s['status'] != 'complete' and s['loss'] is not None:
            raise ValueError('technical failure acquired a numerical loss')
        if s['status'] == 'not-submitted' and s['physical_job'] is not None:
            raise ValueError('unsubmitted slot acquired a physical world')
    for arm, selection in r['fixed_selection'].items():
        pool = [s for s in slots if s['arm'] == arm and s['status'] == 'complete']
        best = min((number(s['loss']) for s in pool), default=None)
        ties = [s['physical_job'] for s in pool if s['loss'] == best]
        if (selection['loss'] != best or selection['all_tied_ids'] != ties
                or selection['selected_id'] != (ties[0] if ties else None)
                or selection['complete_candidates'] != len(pool)
                or selection['submitted_worlds'] != sum(s['arm'] == arm and s['status'] != 'not-submitted' for s in slots)
                or selection['status'] != ('selected' if ties else 'no-completed-submission')
                or (selection['policy_sha256'] is None) != (not ties)):
            raise ValueError('selection changed, lost a tie or acquired a fallback')
    worlds = {w['physical_job']: w for w in r['physical_worlds']}
    if len(worlds) != len(r['physical_worlds']) or len(worlds) != r['physical_evaluation_worlds']:
        raise ValueError('unique declared physical worlds required')
    lookup = {}
    for w in worlds.values():
        if set(w['scores']) != set(TERMS) or w['seed'] not in SEEDS:
            raise ValueError('declared scores and seeds required')
        values = {name: w['measurement']['metrics'][metric] for name, metric in METRICS.items()}
        for key, terms in TERMS.items():
            if any(values[n]['status'] != 'measured' or number(values[n]['value']) is None for n in terms):
                raise ValueError('available score requires measured finite inputs')
            expected = math.fsum(c * values[n]['value'] for n, c in terms.items())
            if number(w['scores'][key]) is None or not math.isclose(expected, w['scores'][key], abs_tol=1e-12, rel_tol=1e-12):
                raise ValueError('score differs from retained A/Q/R')
        for label in w['labels']:
            key = label, w['seed']
            if key in lookup:
                raise ValueError('duplicate label and seed')
            if label.startswith('selected:') and w['policy_sha256'] != r['fixed_selection'][label[9:]]['policy_sha256']:
                raise ValueError('evaluation changed its selected policy')
            lookup[key] = {'label': label, 'seed': w['seed'], 'physical_job': w['physical_job'],
                           'status': 'complete', 'scores': w['scores']}
    labels = ['reference:' + n for n in REFERENCES] + ['selected:' + a for a in ARMS]
    if r['evaluation_label_order'] != labels or set(r['score_order']) != set(TERMS) or len(r['score_order']) != len(TERMS):
        raise ValueError('explicit display/CSV order required across JSON serialization')
    for arm, choice in r['fixed_selection'].items():
        if choice['selected_id'] is None:
            for seed in SEEDS:
                key = 'selected:' + arm, seed
                if key in lookup:
                    raise ValueError('unavailable arm acquired evaluation')
                lookup[key] = {'label': key[0], 'seed': seed, 'physical_job': None,
                               'status': 'no-completed-submission', 'scores': dict.fromkeys(TERMS)}
    if set(lookup) != {(label, seed) for label in labels for seed in SEEDS}:
        raise ValueError('complete label/seed availability matrix required')
    rows = [lookup[label, seed] for label in labels for seed in SEEDS]
    if (r['evaluation_rows'] != rows or r['logical_evaluation_rows'] != len(rows)
            or r['unavailable_label_seed_rows'] != sum(x['physical_job'] is None for x in rows)):
        raise ValueError('logical/physical joins or unavailable rows changed')
    summaries = {label: {k: descriptive([{'value': lookup[label, s]['scores'][k]} for s in SEEDS], 'value')
                        for k in TERMS} for label in labels}
    pairs = []
    for label in labels[len(REFERENCES):]:
        for reference in REFERENCES:
            for seed in SEEDS:
                a, b = lookup[label, seed], lookup['reference:' + reference, seed]
                pairs.append({'label': label, 'reference': reference, 'seed': seed,
                    'physical_job': a['physical_job'], 'reference_physical_job': b['physical_job'],
                    'shared_same_physical_job': a['physical_job'] is not None and a['physical_job'] == b['physical_job'],
                    'differences': {k: None if a['scores'][k] is None else a['scores'][k] - b['scores'][k] for k in TERMS}})
    if summaries != r['evaluation_summary'] or pairs != r['paired_reference_differences']:
        raise ValueError('summaries or paired differences changed')
    return r


def components_csv(r):
    buf = io.StringIO(newline='')
    fields = ['physical_job', 'seed', 'policy_sha256', 'labels', *r['score_order'],
              'accepted_decisions', 'accepted_peer_score_sum', 'review_records']
    writer = csv.DictWriter(buf, fieldnames=fields); writer.writeheader()
    for row in r['physical_worlds']:
        metrics = row['measurement']['metrics']
        writer.writerow({**{k: row[k] for k in fields[:3]}, 'labels': ' | '.join(row['labels']),
                         **row['scores'], **{k: metrics['native.' + k]['value'] for k in fields[-3:]}})
    return buf.getvalue().encode()


def reproduce(report, manifest, figures, output):
    if output.exists() or output.resolve().is_relative_to(figures.resolve()):
        raise ValueError('fresh independent output required')
    r = validate(json.loads(report.read_text())); m = checked(json.loads(manifest.read_text()))
    if (m['schema'] != SCHEMA + '.portable.v1' or m['report_content_sha256'] != r['content_sha256']
            or set(m['files']) != set(FILES) or file_sha256(report) != m['files']['report.json']
            or any(file_sha256(figures / n) != m['files'][n] for n in FILES if n != 'report.json')):
        raise ValueError('exact portable report/CSV/figure binding required')
    before = {p: file_sha256(p) for p in (report, manifest, *(figures / n for n in FILES if n != 'report.json'))}
    output.mkdir(parents=True)
    save(output / 'report.json', {k: v for k, v in r.items() if k != 'content_sha256'})
    render_paths(r, output)
    import matplotlib.pyplot as plt
    with plt.rc_context({'svg.hashsalt': SCHEMA, 'font.size': 8.5,
                        'axes.spines.top': False, 'axes.spines.right': False}):
        render_evaluation(r, output)
    (output / 'physical-components.csv').write_bytes(components_csv(r))
    if any(file_sha256(output / n) != m['files'][n] for n in FILES):
        raise ValueError('rebuilt numeric/figure bytes differ')
    if any(file_sha256(p) != h for p, h in before.items()):
        raise ValueError('retained inputs changed')
    result = {'schema': SCHEMA + '.reproduction.v1', 'report_content_sha256': r['content_sha256'],
              'files': m['files'], 'all_six_outputs_byte_identical': True,
              'raw_audit_repeated': False, 'model_inference_repeated': False,
              'executable_policy_reconstructed_from_hash': False, 'new_model_calls': 0,
              'new_native_worlds': 0, 'new_code_executions': 0}
    save(output / 'reproduction.json', result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('report', 'manifest', 'figures', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); reproduce(a.report, a.manifest, a.figures, a.output)
    print(json.dumps({'six_outputs_identical': True, 'new_model_calls': 0}))


if __name__ == '__main__':
    main()
