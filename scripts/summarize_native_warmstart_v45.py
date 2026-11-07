#!/usr/bin/env python3
"""Project a completed original-source V45 audit; no new native/model audit.

The saved full audit remains authoritative. This separate post-freeze helper
checks its file/content identity and produces a small publication index, without
opening historical caches, importing authored code, or contacting a provider.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import atomic_open, decode_json, file_sha256

SCHEMA = 'scienceutopia.native-warmstart-audit-summary.v45'
FULL_SCHEMA = 'scienceutopia.native-warmstart-audit.v45'
ARMS = ('efficiency', 'throughput')
PHYSICAL_FIELDS = ('consumed_native_slots', 'technical_failures', 'physical_native_worlds',
    'physical_world_directory_count', 'physical_researcher_responses', 'completed_researcher_responses',
    'physical_wire_requests', 'recorded_code_executions_including_partial',
    'completed_researcher_model_call_seconds')


def _errors(value):
    """Retain diagnostic text/hash, not arbitrary embedded source/JSON bodies."""
    return [{'type': row.get('error_type', row.get('type')), 'message': row.get('error', row.get('message')),
             'run_id': row.get('run_id'), 'seed': row.get('seed'), 'error_sha256': digest(row)}
            for row in value]


def _lineage(value):
    if value is None:
        return None
    return {key: clone(value[key]) for key in ('from_fingerprint', 'to_fingerprint', 'counts',
        'source_changes', 'source_bodies_added', 'source_bodies_removed',
        'same_source_body_renamed_ids', 'scope') if key in value}


def _arm(run, comparison):
    rows = run['observations']
    if (run.get('terminal') is not True or run.get('consumed_native_slots') != 1
            or len(rows) != 1 or run.get('pending') is not None):
        raise ValueError('compact V45 requires exactly one terminal new slot per arm')
    row = rows[0]
    if row['status'] not in ('complete', 'technical-failure', 'generation-failure'):
        raise ValueError('unknown terminal native slot status')
    if row['status'] != 'complete' and row['loss'] is not None:
        raise ValueError('technical failure must remain null, not a historical success/penalty')
    original = row.get('observation') or {}
    if row['status'] == 'complete' and (type(row['loss']) not in (int, float)
            or not math.isfinite(row['loss']) or original.get('status') != 'complete'
            or original.get('loss') != row['loss']):
        raise ValueError('complete slot must preserve its finite original measured loss')
    metadata = original.get('metadata', {})
    record = run['records'][0]
    parent = record['request']['parent_system']
    # Fingerprints are diagnostics of literal documents, not behavioral novelty.
    from utopia.system import SystemSpec
    parent_fingerprint = SystemSpec.from_dict(parent).fingerprint
    current_fingerprint = row.get('system_fingerprint')
    slot = {key: clone(row.get(key)) for key in ('status', 'loss', 'generation', 'slot',
        'request_sha256', 'version_sha256', 'observation_id', 'run_id', 'checkpoint_sha256')}
    slot.update(parent_system_fingerprint=parent_fingerprint, system_fingerprint=current_fingerprint,
        based_on_observation_id=record['request'].get('based_on_observation_id'),
        initial_evidence_sha256=record['request']['initial_evidence']['bank_sha256'],
        original_observation_status=original.get('status'), original_observation_loss=original.get('loss'),
        generation_error=clone(row.get('generation_error')),
        technical_errors=_errors(metadata.get('technical_failures', [])),
        literal_lineage={key: _lineage(value) for key, value in (row.get('lineage') or {}).items()},
        measurements={key: clone((row.get('metrics') or {}).get(metric)) for key, metric in (
            ('A', 'native.accepted_decisions'), ('Q', 'native.accepted_peer_score_sum'),
            ('R', 'native.review_records'))},
        retrospective_cross_scores=clone(row.get('cross_scores')),
        cross_scores_are_not_original_arm_feedback=True,
        new_source_measurement=original.get('status') == 'complete',
        semantic_novelty_or_scientific_benefit_established=False)
    designer = run['designer']
    generations = []
    for proof in designer.get('proofs', []):
        steps = []
        for index, step in enumerate(proof.get('completed_records', [])):
            if step is None:
                steps.append({'step': index, 'status': 'interrupted-response-unknown', 'error': None})
                continue
            transition = step.get('transition') or {}
            error = step.get('error')
            steps.append({'step': step.get('step', index), 'status': step['status'],
                'tool': transition.get('tool'), 'error': clone(error),
                'errors': _errors(step.get('errors', [])),
                'transition_errors': _errors(transition.get('errors', []))})
        generations.append({'request_sha256': proof['request_sha256'],
            'definition_sha256': proof['definition_sha256'],
            'status': proof['result']['status'], 'counts': clone(proof['counts']),
            'literal_change': clone(proof.get('authoring_change')), 'steps': steps})
    return {'loss_spec': clone(run['loss_spec']), 'new_slot': slot,
        'comparison': clone(comparison),
        'physical_costs': {key: run.get(key) for key in PHYSICAL_FIELDS},
        'physical_response_caches': clone(run.get('physical_response_caches', [])),
        'designer_counts': {key: clone(value) for key, value in designer.items()
            if key not in ('proofs', 'cost_measurements')},
        'designer_cost_measurements': clone(designer.get('cost_measurements')),
        'authoring_generations': generations}


def summarize_saved_audit(path, *, expected_source):
    """Validate saved identities, not reexecute the original-source auditor."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('explicit regular saved full audit required')
    before = file_sha256(path)
    report = decode_json(path.read_text(encoding='utf-8'), strict=True, finite_floats=True)
    if (not isinstance(expected_source, str) or not re.fullmatch('[0-9a-f]{40}', expected_source)
            or report.get('schema') != FULL_SCHEMA or report.get('source_commit') != expected_source
            or report.get('content_sha256') != digest({k: v for k, v in report.items() if k != 'content_sha256'})
            or report.get('budget_terminal') is not True
            or report.get('status') not in ('budget-complete', 'budget-complete-with-failures')
            or report.get('consumed_native_slots') != 2
            or set(report.get('runs', {})) != set(ARMS)
            or set(report.get('comparisons', {})) != set(ARMS)):
        raise ValueError('exact source-bound completed full V45 audit required')
    audit = report['audit']
    if (audit.get('raw_files_verified_unchanged') is not True
            or audit.get('exact_authoring_and_native_truth_reused') is not True
            or report.get('new_model_calls_during_audit') != 0
            or report.get('new_code_executions_during_audit') != 0):
        raise ValueError('saved audit does not establish its declared read-only verification')
    protocols = {name: value for name, value in audit['source_proofs']['files'].items()
        if re.fullmatch(r'research/protocols/campaigns/native-warmstart-v45-a[0-9]+\.md', name)}
    if len(protocols) != 1:
        raise ValueError('one exact prospective protocol proof required')
    writer = report['terminal_writer_and_progress']
    start, end = writer['started'], writer['ended']
    elapsed = (datetime.fromisoformat(end['ended_utc']) - datetime.fromisoformat(start['started_utc'])).total_seconds()
    if elapsed < 0 or end.get('status') != 'exited' or end.get('exit_code') != 0:
        raise ValueError('matching successful terminal writer timing required')
    summary = {'schema': SCHEMA, 'source_commit': expected_source,
        'classification': report['classification'], 'status': report['status'], 'budget_terminal': True,
        'plan_sha256': report['plan_sha256'], 'initial_evidence_sha256': report['initial_evidence_sha256'],
        'historical_source_audit': clone(report['historical_source_audit']),
        'protocol_source_proof': protocols,
        'full_audit': {'path': str(path.resolve()), 'file_sha256': before,
            'content_sha256': report['content_sha256'], 'input_file_count': audit['input_file_count'],
            'input_inventory_sha256': audit['input_inventory_sha256']},
        'arms': {name: _arm(report['runs'][name], report['comparisons'][name]) for name in ARMS},
        'physical_costs': {key: report.get(key) for key in PHYSICAL_FIELDS},
        'designer_counts': clone(report['designer_costs']),
        'writer': {'started_utc': start['started_utc'], 'ended_utc': end['ended_utc'],
            'elapsed_seconds': elapsed, 'pid': start.get('pid'), 'argv': clone(start.get('argv'))},
        'calibration_cold_replay': clone(report['calibration_cold_replay']),
        'calibration_times': {'age_seconds_at_writer_start': report['calibration_cold_replay'].get('age_seconds'),
            'started_utc': None, 'completed_utc': None,
            'note': 'Absolute calibration times are not copied into the full audit; not inferred as zero.'},
        'role_loading': clone(report['role_loading']), 'claims': clone(report['claims']),
        'projection': {'helper_source_sha256': file_sha256(Path(__file__)),
            'saved_full_audit_identity_verified': True, 'fresh_raw_or_scientific_audit': False,
            'new_model_calls': 0, 'new_code_executions': 0,
            'historical_pooling_is_not_new_improvement': True,
            'literal_changes_do_not_establish_behavioral_changes': True}}
    summary['content_sha256'] = digest(summary)
    if file_sha256(path) != before:
        raise ValueError('saved full audit changed during compact projection')
    return summary


def write_summary(full_audit, output, *, expected_source, raw_run):
    target, raw = Path(output), Path(raw_run).resolve()
    if (target.exists() or target.is_symlink() or target.resolve().is_relative_to(raw)
            or target.resolve() == Path(full_audit).resolve()):
        raise ValueError('summary output must be fresh and outside the raw run/full audit')
    value = summarize_saved_audit(full_audit, expected_source=expected_source)
    argv = value['writer']['argv']
    declared = []
    for index, token in enumerate(argv or []):
        if token == '--output' and index + 1 < len(argv):
            declared.append(argv[index + 1])
        elif isinstance(token, str) and token.startswith('--output='):
            declared.append(token.partition('=')[2])
    if (len(declared) != 1 or not Path(declared[0]).is_absolute()
            or Path(declared[0]).resolve() != raw):
        raise ValueError('raw-run must match the absolute original writer output argument')
    # Exclusive publication also protects against a concurrent output writer.
    with atomic_open(target, 'w', exclusive=True, private=True) as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False, ensure_ascii=False, indent=2)
        stream.write('\n')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-audit', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--raw-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    summary = write_summary(args.full_audit, args.output, expected_source=args.expected_source, raw_run=args.raw_run)
    print(json.dumps({key: summary[key] for key in ('status', 'source_commit', 'content_sha256')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
