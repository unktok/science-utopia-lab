#!/usr/bin/env python3
"""Offline review of an existing audited, single-world-per-slot search summary.

This is retrospective cross-scoring, NOT a new audit, optimizer, candidate bank,
simulation, cross-arm feedback injection, or evidence of a newly improved system.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utopia.optimization.loss import evaluate_loss, loss_spec_sha256, validate_loss_spec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.retrospective-search-review.v1'
INPUT_SCHEMA = 'scienceutopia.native-staged-search-audit-summary.v15'
METRICS = {'A': 'native.accepted_decisions', 'Q': 'native.accepted_peer_score_sum',
    'R': 'native.review_records'}


def _equal(actual, expected):
    return (type(actual) in (int, float) and math.isfinite(actual)
        and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12))


def _best(rows, loss_id):
    eligible = [r for r in rows if r['scores'][loss_id] is not None]
    value = min((r['scores'][loss_id] for r in eligible), default=None)
    return {'loss': value, 'ties': [r['row_id'] for r in eligible if r['scores'][loss_id] == value]}


def review_summary(summary, *, expected_source, expected_full_audit):
    if summary.get('schema') != INPUT_SCHEMA:
        raise ValueError('saved staged audit summary required')
    if digest({k: v for k, v in summary.items() if k != 'content_sha256'}) != summary.get('content_sha256'):
        raise ValueError('saved summary content hash differs')
    if (summary.get('source_commit') != expected_source
            or summary.get('exact_full_audit_content_sha256') != expected_full_audit):
        raise ValueError('expected experiment source/full audit binding differs')
    audit = summary.get('audit', {})
    if (audit.get('exact_raw_tools_draft_source_definition_replayed') is not True
            or audit.get('own_history_loss_and_all_ties_replayed') is not True
            or audit.get('source_proofs', {}).get('status') !=
                'verified-exact-staged-runtime-driver-helper-source-blobs'):
        raise ValueError('original audit evidence is incomplete')
    if summary.get('budget_terminal') is not True or summary.get('queue_terminal') is not True:
        raise ValueError('terminal campaign required; no provisional selection')
    runs = summary['runs']
    specs = {name: run['loss_spec'] for name, run in runs.items()}
    if not specs or len({s['id'] for s in specs.values()}) != len(specs):
        raise ValueError('distinct explicit objective IDs required')
    for spec in specs.values():
        validate_loss_spec(spec)
        if (spec['across_seeds']['minimum_valid_runs'] != 1
                or spec['across_seeds']['dispersion_weight'] != 0
                or any(t['metric_id'] not in METRICS.values() or t['slice_id'] is not None
                    for t in spec['per_run']['terms'])):
            raise ValueError('review supports only single-world A/Q/R loss projections')
    rows, seen = [], set()
    for arm, run in runs.items():
        for item in run['observations']:
            identity = f"{arm}:slot-{item['slot']}"
            if identity in seen:
                raise ValueError('duplicate logical slot')
            seen.add(identity)
            status = item['status']
            if status not in ('complete', 'technical-failure', 'generation-failure'):
                raise ValueError('unknown terminal observation status')
            scores = {s['id']: None for s in specs.values()}
            values = None
            if status == 'complete':
                if item['original_observation_status'] != 'complete':
                    raise ValueError('complete row lacks a complete original observation')
                values = item['native_A_Q_R']
                metrics = {metric: values[short] for short, metric in METRICS.items()}
                # Logical archived observation ID, not an invented physical run.
                measured = {'run_id': item['observation_id'], 'metrics': metrics}
                for spec in specs.values():
                    result = evaluate_loss(spec, [measured])
                    if result['status'] != 'complete':
                        raise ValueError('complete row has unmeasured/nonfinite inputs')
                    value = result['loss']
                    if not _equal(item['cross_scores'][spec['id']], value):
                        raise ValueError('archived cross-score and canonical loss differ')
                    scores[spec['id']] = value
                own = scores[specs[arm]['id']]
                if not _equal(item['loss'], own) or not _equal(item['original_observation_loss'], own):
                    raise ValueError('original and independently scored own loss differ')
            elif item['loss'] is not None or any(v is not None for v in item['cross_scores'].values()):
                raise ValueError('technical failure cannot carry a numerical loss')
            rows.append({'row_id': identity, 'arm': arm, 'generation': item['generation'],
                'status': status, 'system_fingerprint': item['system_fingerprint'],
                'checkpoint_sha256': item['checkpoint_sha256'], 'observation_id': item['observation_id'],
                'A_Q_R': {k: v['value'] for k, v in values.items()} if values else None,
                'scores': scores})
    if len(rows) != summary['consumed_native_slots'] or len(rows) != summary['planned_native_slots']:
        raise ValueError('logical slot counts differ; no dropped failure slots')
    selection = {}
    for arm, spec in specs.items():
        own = _best([r for r in rows if r['arm'] == arm], spec['id'])
        pooled = _best(rows, spec['id'])
        selection[arm] = {'loss_id': spec['id'], 'loss_spec_sha256': loss_spec_sha256(spec),
            'original_arm_observed_best': own, 'retrospective_pooled_best': pooled,
            'retrospective_pool_gap': own['loss'] - pooled['loss']
                if own['loss'] is not None and pooled['loss'] is not None else None}
    result = {'schema': SCHEMA, 'source_commit': expected_source,
        'input_summary_content_sha256': summary['content_sha256'],
        'input_full_audit_content_sha256': expected_full_audit,
        'status_counts': dict(sorted(Counter(r['status'] for r in rows).items())),
        'logical_slots': len(rows), 'physical_native_worlds': summary['physical_native_worlds'],
        'physical_researcher_responses': summary['physical_researcher_responses'],
        'designer_costs': summary['designer_costs'], 'rows': rows, 'selection': selection,
        'new_model_calls': 0, 'new_world_executions': 0, 'new_code_executions': 0,
        'fresh_raw_audit': False, 'held_out': False, 'new_optimization_run': False,
        'new_institution_invented': False, 'historical_feedback_modified': False,
        'limitations': [
            'Projection of a supplied hash-bound audit summary, not a new verification of its raw files.',
            'Pooling is retrospective and was not available to the original independent search arms.',
            'Pool gaps are not fresh improvements, global regret bounds or equal-budget method comparisons.',
            'Logical observations can reuse checkpoints; they are not independent fresh worlds.',
            'Equal scores do not establish program equivalence; different source hashes do not establish novelty.',
            'Scope is one audited single-world-per-slot development campaign, not cross-source or held-out reuse.']}
    result['content_sha256'] = digest(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--expected-full-audit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise ValueError('output already exists; never overwrite evidence')
    before = file_sha256(args.summary)
    value = json.loads(args.summary.read_text())
    result = review_summary(value, expected_source=args.expected_source,
        expected_full_audit=args.expected_full_audit)
    if file_sha256(args.summary) != before:
        raise ValueError('input summary changed while reading')
    result['input_summary_file_sha256'] = before
    result['content_sha256'] = digest({k: v for k, v in result.items() if k != 'content_sha256'})
    write_json_atomic(args.output, result, sort_keys=True, allow_nan=False)
    print(json.dumps({k: result[k] for k in ('status_counts', 'logical_slots', 'new_model_calls')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
