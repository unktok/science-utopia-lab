#!/usr/bin/env python3
"""Read-only native v11 audit: opaque losses, open designs and exact score replay.

No model/factory/container or generated institution source is executed. Existing
native checkpoint, source, wire and response validators retain their strict
bindings; only explicit protocol/loss arguments select the v11 contract.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_native_open_v7 import (
    FIXTURE, ReadOnlyCampaign, _inventory, audit_native_run, authoring_proofs,
    partial_physical_proof, read,
)
from scripts.run_native_open_estimators_v11 import (
    ACTUAL, ARM_IDS, DRAWS, ESTIMATOR_CONFIG, EXPERIMENT, GENERATIONS,
    SCHEMA as RAW_SCHEMA, SEED, load_preregistered_loss, record_failed,
)
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_manifest_inbox import audit_manifest_inbox
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-open-estimators-independent-audit.v11'


def _without_provenance(value):
    """Remove explicitly labelled provenance only, never code/rules/wires/IDs."""
    if isinstance(value, dict):
        return {key: _without_provenance(v) for key, v in value.items() if key != 'provenance'}
    if isinstance(value, list):
        return [_without_provenance(v) for v in value]
    return value


def matched_initial_definitions(arms):
    records = [arms[arm]['records'] for arm in ARM_IDS]
    if any(not r for r in records):
        return {'status': 'not-yet-available', 'matched': None}
    definitions = [_without_provenance(r[0]['definition']) for r in records]
    if definitions[0] != definitions[1]:
        raise ValueError('initial arm definitions differ beyond explicitly labelled provenance')
    return {'status': 'verified', 'matched': True, 'definition_sha256': digest(definitions[0]),
        'scope': 'same full initial code/factors/coordinates/weights after removing provenance fields only; no shared physical trajectories'}


def incumbent_path(rows):
    """Retain every observed tie; never choose an arbitrary best institution."""
    best, ties, path = None, [], []
    for row in rows:
        loss = row['loss']
        identity = {'generation': row['generation'], 'draw_index': row['draw_index'],
            'observation_id': row['observation_id'], 'system_fingerprint': row['system_fingerprint']}
        if loss is not None:
            if best is None or loss < best:
                best, ties = loss, [identity]
            elif loss == best:
                ties.append(identity)
        path.append({'generation': row['generation'], 'draw_index': row['draw_index'],
            'observed_loss': loss, 'best_loss_so_far': best, 'best_observation_ties': deepcopy(ties)})
    return {'path': path, 'best_loss': best, 'best_observation_ties': ties,
        'tie_rule': 'exact equality of independently re-extracted native losses; all ties retained',
        'initial_unevaluated_system_scored': False}


def _validate_plan(raw, plan, expected_source):
    loss = load_preregistered_loss(ROOT / 'research/objectives/losses/native-joint-v5-net-reviewed-utility.json')
    if (raw.get('schema') != RAW_SCHEMA or plan.get('schema') != RAW_SCHEMA
            or digest({k: v for k, v in raw.items() if k != 'content_sha256'}) != raw.get('content_sha256')
            or raw.get('plan') != plan or raw.get('source_commit') != expected_source
            or plan.get('world', {}).get('source_commit') != expected_source
            or plan.get('loss_spec') != loss or plan.get('seed') != SEED
            or plan.get('generations') != GENERATIONS or plan.get('draws_per_generation') != DRAWS
            or plan.get('arm_ids') != list(ARM_IDS)
            or plan.get('methods') != {'blackbox': {'mode': 'blackbox', 'expectation_estimator': None},
                'score-control-variate': {'mode': 'score', 'expectation_estimator': ESTIMATOR_CONFIG}}
            or plan.get('population') != {'authors': 5, 'conference_setting': 1}
            or plan.get('shared_physical_trajectories') is not False
            or plan.get('scientific_benefit_required') is not False
            or plan.get('structural_novelty_reward') is not False
            or plan.get('experiment') != EXPERIMENT):
        raise ValueError('v11 source/loss/method/budget/native-world frozen plan differs')
    classification = plan['world'].get('classification')
    if classification not in {ACTUAL, FIXTURE} or raw.get('classification') != classification:
        raise ValueError('unknown or inconsistent actual/fixture classification')
    if classification == ACTUAL and (len(expected_source) != 40
            or raw.get('configured_researcher_provider') != 'qwen3:8b'
            or plan['world'].get('years') != 2 or plan['world'].get('corpus_years') != 4):
        raise ValueError('actual v11 requires explicit source and original fixed-Qwen native protocol')
    return loss, classification


def _read_arm(root, arm, raw, plan, loss):
    directory = root / 'arms' / arm / 'campaign'
    state = read(directory / 'native-adaptive-state.json')
    b = state['binding']
    method = plan['methods'][arm]
    if (b['world'] != plan['world'] or b['loss_spec'] != loss or b['initial_system'] != plan['initial_system']
            or b['seeds'] != [SEED] or b['seed'] != SEED or b['mode'] != method['mode']
            or b.get('expectation_estimator') != method['expectation_estimator']):
        raise ValueError('arm binding differs from frozen plan/loss/method')
    options = {k: b[k] for k in ('mode', 'seed', 'learning_rate', 'strategy_learning_rate', 'strategy_baseline', 'exploration')}
    if 'expectation_estimator' in b:
        options['expectation_estimator'] = b['expectation_estimator']
    controller = ReadOnlyCampaign(directory, initial_system=SystemSpec.from_dict(b['initial_system']),
        loss_spec=loss, seeds=b['seeds'], world_binding=b['world'], strategies=b['strategies'], **options)
    records, pending = controller.state['records'], controller.state['pending']
    all_records = records + ([pending] if pending else [])
    if (len(all_records) > GENERATIONS or any(r['request']['count'] != DRAWS for r in all_records)
            or raw['arms'][arm]['binding'] != b or raw['arms'][arm]['records'] != records
            or raw['arms'][arm]['pending'] != pending):
        raise ValueError('reported arm history/pending or two-by-two budget differs')
    # Replay already verifies history, strategy draw, weights, estimator refit,
    # Gaussian/categorical likelihoods, correction, and every saved update.
    for index, record in enumerate(all_records):
        if record['request']['history'] != controller._history(records[:index]):
            raise ValueError('request contains another arm, future, or changed history')
    inbox = root / 'arms' / arm / 'authoring'
    authoring = authoring_proofs(inbox, all_records)
    if raw['arms'][arm]['authoring'] != audit_manifest_inbox(inbox):
        raise ValueError('external authoring summary differs from actual request-bound inbox')
    return controller, all_records, authoring


def analyze(run, *, expected_source, require_complete=True):
    root = Path(run).resolve()
    before = _inventory(root)
    try:
        result = _analyze(root, expected_source=expected_source, require_complete=require_complete, inventory=before)
    finally:
        if _inventory(root) != before:
            raise ValueError('raw evidence changed during read-only audit; no stable result')
    return result


def _analyze(root, *, expected_source, require_complete, inventory):
    raw, plan = read(root / 'evidence.json'), read(root / 'plan.json')
    loss, classification = _validate_plan(raw, plan, expected_source)
    if set(raw['arms']) != set(ARM_IDS):
        raise ValueError('unexpected or missing method arm')
    arms, physical_ids, declared, proofs, rows = {}, set(), {}, [], []
    committed = failures = 0
    for arm in ARM_IDS:
        controller, all_records, authoring = _read_arm(root, arm, raw, plan, loss)
        arm_rows = []
        failures += sum(bool(r['generation_error']) for r in controller.state['records'])
        failures += sum(r['report']['status'] == 'not-updated-estimator-failure'
            for r in controller.state['records'])
        for record in all_records:
            for draw in record['draws']:
                if draw['suggestion'] is not None:
                    identity = draw['suggestion']['suggestion_id'] + '-s42'
                    if identity in declared:
                        raise ValueError('physical run identity reused by another logical draw/arm')
                    declared[identity] = SystemSpec.from_dict(draw['suggestion']['candidate'])
        for record in controller.state['records']:
            for index, (draw, observation) in enumerate(zip(record['draws'], record['observations'])):
                committed += 1
                valid = observation and observation['status'] == 'complete' and not observation['metadata'].get('technical_failures')
                row = {'arm': arm, 'generation': record['request']['generation'], 'draw_index': index,
                    'version_sha256': record['version_sha256'], 'assignment': draw['assignment'], 'latent': draw['latent'],
                    'observation_id': observation['observation_id'] if observation else None,
                    'system_fingerprint': SystemSpec.from_dict(draw['suggestion']['candidate']).fingerprint if draw['suggestion'] else None,
                    'loss': None, 'status': 'complete' if valid else 'technical-failure'}
                if valid:
                    run_evidence = observation['metadata']['runs']
                    if len(run_evidence) != 1:
                        raise ValueError('completed logical draw must have exactly one physical native run')
                    evidence = run_evidence[0]
                    if evidence['run_id'] in physical_ids or evidence['run_id'] not in declared:
                        raise ValueError('physical native run reused or not declared')
                    physical_ids.add(evidence['run_id'])
                    proof = audit_native_run(root, draw, observation, evidence, plan['world'], classification,
                        expected_experiment=EXPERIMENT, expected_loss=loss)
                    measurement = proof['measurement']
                    evaluated = evaluate_loss(loss, [measurement])
                    if ([measurement] != observation['metadata']['measurements']
                            or evaluated != observation['metadata']['loss_evaluation']
                            or evaluated['loss'] != observation['loss'] or proof['native_loss'] != observation['loss']):
                        raise ValueError('independent checkpoint native loss/measurements differ from saved observation')
                    row.update(loss=evaluated['loss'], run_id=evidence['run_id'],
                        metrics=measurement['metrics'], checkpoint_sha256=proof['checkpoint_sha256'])
                    proofs.append({'arm': arm, 'generation': row['generation'], 'draw_index': index,
                        'run_id': evidence['run_id'], **proof})
                else:
                    failures += 1
                    if observation is not None and observation['loss'] is not None:
                        raise ValueError('failed draw received a numeric loss')
                arm_rows.append(row)
                rows.append(row)
        records = controller.state['records']
        arms[arm] = {'records': records, 'pending': controller.state['pending'],
            'authoring_proofs': authoring, 'observations': arm_rows,
            'incumbents': incumbent_path(arm_rows),
            'loss_path': [r['loss'] for r in arm_rows],
            'updates': [{'generation': r['request']['generation'],
                'generation_error': r['generation_error'], 'mixed_report': r['report'].get('mixed'),
                'strategy_gradient': r['report'].get('strategy_gradient')} for r in records]}
    initial_match = matched_initial_definitions(arms)
    terminal = all(len(a['records']) == GENERATIONS and a['pending'] is None for a in arms.values())
    complete = terminal and len(physical_ids) == 8 and failures == 0
    stopped = any(record_failed(r) for a in arms.values() for r in a['records'])
    status = 'technically-stopped' if stopped else 'complete' if complete else 'budget-complete-with-failures' if terminal else 'in-progress'
    if (raw['status'] != status or raw['budget_terminal'] != terminal
            or raw['stopped_on_technical_failure'] != stopped
            or raw['planned_native_world_budget'] != 8 or raw['committed_draws'] != committed
            or raw['complete_native_worlds'] != len(physical_ids) or raw['technical_failures'] != failures):
        raise ValueError('reported terminal/native-world/draw/failure counts differ')
    if require_complete and not complete:
        raise ValueError('eight complete native worlds required; --allow-incomplete preserves truthful partial evidence')
    caches, partial = [], []
    for path in sorted((root / 'worlds').glob('*/replies/responses.sqlite')):
        cell = path.parent.parent
        if cell.name not in declared:
            raise ValueError('physical inference directory has no declared logical draw')
        if cell.name not in physical_ids:
            partial.append(partial_physical_proof(cell, declared[cell.name], plan['world'], classification))
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True) as db:
            counts = dict(db.execute('SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
        caches.append({'path': str(path.resolve()), 'sha256': file_sha256(path), 'outcomes': counts})
    replies = sum(c['outcomes'].get('response', 0) for c in caches)
    if caches != raw['physical_response_caches'] or replies != raw['physical_reply_count']:
        raise ValueError('physical response-cache inventory/count/hash differs')
    logical = sum(p['response_proof']['cumulative_responses_per_year'][-1] for p in proofs)
    if complete and (len(caches) != 8 or logical != replies
            or replies != sum(p['response_proof']['researcher_responses'] for p in proofs)):
        raise ValueError('completed pilot has unassigned/reused physical inference or logical reply mismatch')
    claims = raw['claims']
    if (claims['live_fixed_Qwen_researchers'] != (replies > 0) or claims['scripted_researcher_HTTP'] is not False
            or any(claims[k] is not False for k in ('held_out', 'causal_institutional_benefit', 'scientific_value',
                'designer_improvement_established', 'full_native_world_pathwise_autograd',
                'variance_reduction_established', 'external_authorship_authenticated'))):
        raise ValueError('raw claims exceed audited developmental evidence')
    result = {'schema': SCHEMA, 'classification': classification, 'status': status,
        'source_commit': expected_source, 'loss_spec': loss, 'arms': arms,
        'matched_initial_definitions': initial_match, 'physical_native_worlds': len(physical_ids),
        'logical_completed_draws': len(proofs), 'physical_researcher_responses': replies,
        'logical_completed_researcher_responses': logical, 'reused_responses_in_completed_worlds': 0,
        'completed_wire_requests': sum(p['response_proof']['wire_requests'] for p in proofs),
        'completed_code_executions': sum(p['code_proof']['recorded_executions'] for p in proofs),
        'completed_committed_code_events': sum(p['code_proof']['committed_events'] for p in proofs),
        'native_run_proofs': proofs, 'partial_physical_run_proofs': partial,
        'claims': deepcopy(claims),
        'audit': {'raw_root': str(root), 'raw_evidence_sha256': inventory['evidence.json'],
            'raw_inventory_sha256': digest(inventory), 'raw_input_sha256s': inventory,
            'raw_files_verified_unchanged': len(inventory), 'new_model_calls': 0,
            'new_container_executions': 0, 'campaign_updates_and_prior_refits_replayed': True,
            'checkpoint_loss_reextracted': True, 'all_observations_and_exact_ties_retained': True,
            'analysis_source_sha256s': {name: file_sha256(ROOT / name) for name in (
                'scripts/analyze_native_open_estimators_v11.py', 'scripts/analyze_native_open_v7.py',
                'scripts/analyze_native_society_v6.py', 'scripts/audit_native_objective_v5.py',
                'utopia/optimization/native_adaptive_search.py', 'utopia/optimization/native_expectation_estimators.py')},
            'limits': ['Two batches of two designs per method and one development seed do not establish superiority.',
                'A two-point prior fit need not reduce variance; estimated standard errors are diagnostic only.',
                'Gradients concern conditional design distributions, not arbitrary source-generation likelihoods or exact world derivatives.',
                'Model/provider authorship is self-reported, not authenticated.',
                'Equal losses and all ties are retained, never rerolled; useful invention or designer improvement is not implied.']}}
    if classification == FIXTURE:
        result['claims'].update(live_fixed_Qwen_researchers=False, scripted_researcher_HTTP=True)
    result['content_sha256'] = digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.run.resolve()):
        raise ValueError('audit output must be outside immutable raw evidence')
    report = analyze(args.run, expected_source=args.expected_source, require_complete=not args.allow_incomplete)
    write_json_atomic(args.output, report, sort_keys=True, allow_nan=False)
    print(json.dumps({k: report[k] for k in ('status', 'physical_native_worlds',
        'physical_researcher_responses', 'content_sha256')}, sort_keys=True))


if __name__ == '__main__':
    main()
