"""Signed accepted-content arithmetic, after the complete corrected search.

Data only: no rendering, model calls, generated-code execution, counterfactual
worlds, loss rewriting or selection. A pure fixture is not audit provenance;
the public export requires the original paired closure/cost/readout chain.
"""
import argparse
import csv
import fcntl
from fractions import Fraction
import math
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_planning_content_contributions_v1 import contributions
from scripts.reports.native_priority_method_readout_v1 import analyze, collect, CORRECTED_SCHEMA, cell_id
from scripts.run_native_priority_fixed_evaluation_v1 import origin_evidence, evidence_files, read
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-corrected-choice-content.v1'
SIGNS = ('positive', 'zero', 'negative')


def summarize_observation(observation, cache):
    if observation is None:
        return None
    measurements = observation['metadata']['measurements']
    if observation['status'] != 'complete':
        if observation['loss'] is not None or measurements:
            raise ValueError('unavailable outcome must not acquire complete content or zero utility')
        return None
    if len(measurements) != 1:
        raise ValueError('one actual complete native measurement required')
    measurement, = measurements
    observer = checked(measurement['common_content_observer'])
    records = contributions(observer['accepted_decisions'], cache)
    q = math.fsum(r['mean_score'] for r in records)
    u = math.fsum(r['recorded_centered_utility'] for r in records)
    expected = {'native.accepted_decisions': len(records),
                'native.common_content_score_sum': q, 'native.common_content_utility_sum': u}
    if (any(measurement['metrics'][k] != {'status': 'measured', 'value': v}
            or type(measurement['metrics'][k]['value']) not in (int, float) for k, v in expected.items())
            or type(measurement['metrics']['native.accepted_decisions']['value']) is not int
            or type(observer['unique_contents']) is not int
            or observer['unique_contents'] != len({r['content_sha256'] for r in records})):
        raise ValueError('literal accepted records and original native content measurements differ')
    exact = {s: sum((Fraction(r['exact_centered_utility']) for r in records if r['sign'] == s), Fraction(0))
             for s in SIGNS}
    return {'observer_content_sha256': observer['content_sha256'], 'accepted_records': records,
        'accepted_occurrences': len(records), 'recorded_U': u,
        'distinct_contents': observer['unique_contents'],
        'within_world_repeated_occurrences': len(records) - observer['unique_contents'],
        'sign_counts': {s: sum(r['sign'] == s for r in records) for s in SIGNS},
        'exact_U_by_sign': {s: str(v) for s, v in exact.items()},
        'exact_U': str(sum(exact.values(), Fraction(0))),
        'fixed_record_deletion_arithmetic_gain': str(-exact['negative'])}


def derive(plan, audit, slots, references):
    report = analyze(plan, audit, slots, references)
    if report['schema'] != CORRECTED_SCHEMA:
        raise ValueError('explicit complete corrected four-step study required')
    entries = [('reference/' + label, references[label]) for label in plan['reference_order']]
    entries += [(cell_id(row['slot']), row['observation']) for row in slots]
    cache = {}; rows = []
    for identity, observation in entries:
        content = summarize_observation(observation, cache)
        rows.append({'cell_id': identity,
            'status': 'generation-null' if observation is None else observation['status'],
            'suggestion_id': None if observation is None else observation['suggestion_id'],
            'observation_canonical_sha256': None if observation is None else digest(
                {k: v for k, v in observation.items() if k != 'content_sha256'}),
            'assigned_loss': None if observation is None else observation['loss'],
            'content': content})
    complete = [r['content'] for r in rows if r['content'] is not None]
    return {'schema': SCHEMA, 'scientific_source_commit': report['scientific_source_commit'],
        'plan_content_sha256': report['plan_content_sha256'],
        'input_audit_content_sha256': report['input_audit_content_sha256'],
        'frozen_selection_content_sha256': report['frozen_selection_content_sha256'],
        'coverage': clone(report['coverage']), 'rows': rows,
        'accepted_occurrences': sum(r['accepted_occurrences'] for r in complete),
        'sum_per_world_distinct_contents': sum(r['distinct_contents'] for r in complete),
        'within_world_repeated_occurrences': sum(r['within_world_repeated_occurrences'] for r in complete),
        'distinct_content_hashes': len(cache),
        'sign_counts': {s: sum(r['sign_counts'][s] for r in complete) for s in SIGNS},
        'new_model_calls': 0, 'new_native_worlds': 0, 'new_code_executions': 0,
        'loss_changed': False, 'selection_changed': False, 'publication_ready': False,
        'scope': 'All3 references/all24 compound attempts, preserving generation/execution nulls. '
            'Within-world repeated content and cross-world shared content are distinct diagnostics; '
            'neither filters records or adopts a deduplicated loss. Repeated records, matching '
            'policies and panel positions are not independent samples. '
            'Rational signs explain original ratings; original floating losses/selections remain literal. '
            'Deletion arithmetic holds accepted records/scores and every other consequence fixed: '
            'it is not an attainable subset policy, causal mediation, a global optimum or an estimate '
            'of unobserved/rejected content, future research/resource/information effects or scientific truth.'}


def export(args):
    origin = {key: str(getattr(args, 'origin_' + key).resolve()) for key in ('run', 'source', 'analysis', 'readouts')}
    out = args.output.resolve()
    if out.exists() or any(out.is_relative_to(root) for root in (ROOT.resolve(), *map(Path, origin.values()))):
        raise ValueError('fresh content output outside all reader/scientific evidence sources required')
    reader = pinned_revision(ROOT); raw = Path(origin['run'])
    origin['source_commit'] = read(raw / 'plan.json')['source_commit']
    origin['input_files'] = {str(p): file_sha256(p) for p in evidence_files(origin)}
    with (raw / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_SH | fcntl.LOCK_NB)
        plan, audit, _ = origin_evidence(origin, profile='corrected-choice-v1')
        before = _inventory(raw); slots, references = collect(raw, plan)
        data = derive(plan, audit, slots, references)
        data.update(analysis_source_commit=reader, input_files=origin['input_files'])
        out.mkdir(parents=True); save(out / 'report.json', data)
        fields = ['cell_id', 'occurrence_index', 'year', 'paper_id', 'content_sha256',
                  'mean_score', 'recorded_centered_utility', 'exact_centered_utility', 'sign']
        with (out / 'accepted-records.csv').open('x', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
            for row in data['rows']:
                for record in [] if row['content'] is None else row['content']['accepted_records']:
                    writer.writerow({'cell_id': row['cell_id'], **{k: record[k] for k in fields[1:]}})
        if (before != _inventory(raw) or reader != pinned_revision(ROOT)
                or any(file_sha256(p) != sha for p, sha in origin['input_files'].items())):
            raise ValueError('original evidence or reader source changed during content export')
        save(out / 'manifest.json', {'schema': SCHEMA + '.export', 'analysis_source_commit': reader,
            'input_files': origin['input_files'], 'files': {p.name: file_sha256(p) for p in sorted(out.iterdir())},
            'new_model_calls': 0, 'new_native_worlds': 0, 'new_code_executions': 0,
            'loss_changed': False, 'selection_changed': False, 'publication_ready': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'source', 'analysis', 'readouts'):
        parser.add_argument('--origin-' + key, type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    export(parser.parse_args())
