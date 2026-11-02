#!/usr/bin/env python3
"""Independent read-only audit of the final-v11-control forward-only followup.

Reaudit the immutable parent using its clean historical source, reconstruct the
two saved proposal draws, then reextract original-native checkpoint outcomes.
No model, simulator, institution source or container execution occurs here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_native_open_v7 import FIXTURE, _inventory, audit_native_run, partial_physical_proof, read
from scripts.run_native_control_followup_v12 import (
    ACTUAL, DRAWS, DRAW_SEED, EXPERIMENT, FINAL_WEIGHTS, SCHEMA as RAW_SCHEMA,
    WORLD_SEED, check_observation, compile_draws, guard_parent, load_parent,
    make_plan, valid_observation,
)
from scripts.run_native_open_estimators_v11 import load_preregistered_loss
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-control-followup-independent-audit.v12'


def _validate_plan(raw, plan, expected_source, *, parent_audit, parent_audit_source):
    classification = plan.get('classification')
    if (raw.get('schema') != RAW_SCHEMA or plan.get('schema') != RAW_SCHEMA
            or raw.get('content_sha256') != digest({k:v for k,v in raw.items() if k != 'content_sha256'})
            or raw.get('plan') != plan or raw.get('classification') != classification
            or raw.get('source_commit') != expected_source or plan['world'].get('source_commit') != expected_source
            or classification not in (ACTUAL, FIXTURE) or plan.get('world_seed') != WORLD_SEED
            or plan.get('draw_seed') != DRAW_SEED or plan.get('planned_native_world_budget') != DRAWS
            or plan.get('population') != {'authors': 5, 'conference_setting': 1}
            or plan.get('experiment') != EXPERIMENT
            or any(plan.get(key) is not False for key in ('optimizer_update',
                'new_source_or_topology_invention', 'causal_comparison'))):
        raise ValueError('followup immutable source/budget/forward-only plan differs')
    source_proofs = {}
    if classification == ACTUAL:
        if (len(expected_source) != 40 or any(c not in '0123456789abcdef' for c in expected_source)
                or parent_audit is None or parent_audit_source is None):
            raise ValueError('actual followup requires exact source and explicit immutable parent audit/source')
        # This function independently reruns the historical read-only parent
        # checkpoint/update audit. It does not call the driver's mutating run,
        # advance, summarize, factory or generated-code executor.
        parent_run = Path(plan['parent']['raw_root'])
        receipt, parent, definition, loss = load_parent(parent_run, parent_audit, parent_audit_source)
        if make_plan(receipt, parent, definition, loss, plan['world']) != plan:
            raise ValueError('followup differs from independently reaudited final v11 proposal')
        if plan['loss_spec'] != load_preregistered_loss(ROOT / 'research/objectives/losses/native-joint-v5-net-reviewed-utility.json'):
            raise ValueError('followup full canonical utility loss differs')
        mixed = GeneratedMixedDesign(parent, definition, loss_spec=loss, seed=DRAW_SEED)
        if mixed.weights() != FINAL_WEIGHTS:
            raise ValueError('followup sampling is not the final corrected-control policy')
        for name in ('scripts/run_native_control_followup_v12.py',
                'scripts/analyze_native_open_v7.py', 'scripts/analyze_native_society_v6.py',
                'scripts/audit_native_objective_v5.py'):
            original = subprocess.check_output(['git', 'show', f'{expected_source}:{name}'], cwd=ROOT)
            actual_sha, local_sha = hashlib.sha256(original).hexdigest(), file_sha256(ROOT / name)
            if actual_sha != local_sha:
                raise ValueError('followup replay-critical source differs from actual pin')
            source_proofs[name] = {'actual_source_sha256': actual_sha, 'analysis_source_sha256': local_sha}
    return classification, source_proofs


def analyze(run, *, expected_source, parent_audit=None, parent_audit_source=None, require_complete=True):
    root = Path(run).resolve()
    before = _inventory(root)
    plan, raw = read(root / 'plan.json'), read(root / 'evidence.json')
    parent_guard = None
    try:
        classification, source_proofs = _validate_plan(raw, plan, expected_source,
            parent_audit=parent_audit, parent_audit_source=parent_audit_source)
        if classification == ACTUAL:
            parent_guard = lambda: guard_parent(Path(plan['parent']['raw_root']), Path(parent_audit), plan['parent'])
            parent_guard()
        return _analyze(root, raw, plan, classification, source_proofs, before,
            require_complete=require_complete)
    finally:
        if _inventory(root) != before:
            raise ValueError('followup raw evidence changed during read-only audit')
        if parent_guard:
            parent_guard()


def _analyze(root, raw, plan, classification, source_proofs, inventory, *, require_complete):
    state = read(root / 'state.json')
    draws, version = compile_draws(plan)
    if (raw.get('state') != state or state.get('schema') != RAW_SCHEMA
            or state.get('plan_sha256') != digest(plan) or state.get('version_sha256') != version
            or state.get('draws') != draws or not isinstance(state.get('observations'), list)
            or len(state['observations']) > DRAWS):
        raise ValueError('followup batch/likelihood/latent/assignment/version differs')
    rows, proofs, physical_ids, declared, observation_ids = [], [], set(), {}, set()
    for draw in draws:
        if draw.get('suggestion'):
            run_id = draw['suggestion']['suggestion_id'] + '-s42'
            if run_id in declared:
                raise ValueError('followup physical identity reused')
            declared[run_id] = SystemSpec.from_dict(draw['suggestion']['candidate'])
    stopped = False
    for index, observation in enumerate(state['observations']):
        if stopped:
            raise ValueError('followup continued after a failed attempt')
        draw = draws[index]
        check_observation(observation, draw, plan)
        if observation is not None:
            if observation['observation_id'] in observation_ids:
                raise ValueError('followup exact observation identity reused')
            observation_ids.add(observation['observation_id'])
        valid = valid_observation(observation)
        row = {'draw_index': index, 'draw': draw, 'observation': observation,
            'loss': None, 'status': 'complete' if valid else 'technical-failure', 'physical_proof': None}
        if valid:
            runs = observation['metadata'].get('runs', [])
            if len(runs) != 1 or runs[0]['run_id'] in physical_ids or runs[0]['run_id'] not in declared:
                raise ValueError('followup draw lacks exactly one unique declared physical world')
            evidence = runs[0]
            proof = audit_native_run(root, draw, observation, evidence, plan['world'], classification,
                expected_experiment=EXPERIMENT, expected_loss=plan['loss_spec'])
            measurement = proof['measurement']
            evaluated = evaluate_loss(plan['loss_spec'], [measurement])
            if ([measurement] != observation['metadata']['measurements']
                    or evaluated != observation['metadata']['loss_evaluation']
                    or evaluated['loss'] != observation['loss'] or proof['native_loss'] != observation['loss']):
                raise ValueError('followup actual checkpoint loss differs from saved observation')
            row.update(loss=evaluated['loss'], physical_proof=proof, run_id=evidence['run_id'])
            proofs.append({'draw_index': index, 'run_id': evidence['run_id'], **proof})
            physical_ids.add(evidence['run_id'])
        else:
            stopped = True
            if observation is not None and observation.get('loss') is not None:
                raise ValueError('followup failed attempt has a numerical penalty')
        rows.append(row)
    status = 'technically-stopped' if stopped else 'complete' if len(proofs) == DRAWS else 'in-progress'
    summary = {'status': status, 'planned_native_world_budget': DRAWS,
        'committed_draws': len(rows), 'complete_native_worlds': len(proofs), 'technical_failures': int(stopped)}
    if any(raw.get(key) != value for key,value in summary.items()):
        raise ValueError('followup terminal/attempt/failure summary differs')
    if require_complete and status != 'complete':
        raise ValueError('two completed followup worlds required; use explicit incomplete flag for preserved failures')
    caches, partial = [], []
    directories = {path.name for path in (root / 'worlds').iterdir() if path.is_dir()} if (root / 'worlds').exists() else set()
    if not directories <= declared.keys() or not physical_ids <= directories:
        raise ValueError('followup undeclared/missing physical world directory')
    for path in sorted((root / 'worlds').glob('*/replies/responses.sqlite')):
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True) as db:
            counts = dict(db.execute('SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
        caches.append({'path': str(path.resolve()), 'sha256': file_sha256(path), 'outcomes': counts})
        if path.parent.parent.name not in physical_ids:
            partial.append(partial_physical_proof(path.parent.parent, declared[path.parent.parent.name], plan['world'], classification))
    cache_ids = {Path(cache['path']).parent.parent.name for cache in caches}
    for run_id in sorted(directories - cache_ids - physical_ids):
        cell = root / 'worlds' / run_id
        if not (cell / 'system.json').exists() or read(cell / 'system.json') != declared[run_id].to_dict():
            raise ValueError('followup partial world lacks declared SystemSpec')
        partial.append({'run_id': run_id, 'status': 'partial-before-response-journal', 'loss': None,
            'files': {str(path.relative_to(cell)): file_sha256(path) for path in sorted(cell.rglob('*')) if path.is_file()}})
    replies = sum(cache['outcomes'].get('response', 0) for cache in caches)
    logical = sum(proof['response_proof']['cumulative_responses_per_year'][-1] for proof in proofs)
    if caches != raw.get('physical_response_caches') or replies != raw.get('physical_reply_count'):
        raise ValueError('followup physical response journal count/hash differs')
    if status == 'complete' and (len(caches) != 2 or logical != replies
            or replies != sum(proof['response_proof']['researcher_responses'] for proof in proofs)):
        raise ValueError('followup logical/physical replies differ or reused')
    claims = raw.get('claims', {})
    if (claims.get('post_final_cv_proposal_native_evaluated') != bool(proofs)
            or claims.get('live_fixed_Qwen_researchers') != (classification == ACTUAL and replies > 0)
            or any(claims.get(key) is not False for key in ('held_out', 'gradient_update_after_followup',
                'causal_institutional_benefit', 'variance_reduction_established',
                'designer_improvement_established', 'full_native_world_pathwise_autograd'))):
        raise ValueError('followup claims exceed two forward-only development outcomes')
    result = {'schema': SCHEMA, 'classification': classification, 'status': status,
        'source_commit': plan['world']['source_commit'], 'loss_spec': plan['loss_spec'],
        'parent': plan['parent'], 'proposal': {'final_weights': FINAL_WEIGHTS if classification == ACTUAL else None,
            'definition': plan['definition'], 'world_seed': WORLD_SEED, 'draw_seed': DRAW_SEED,
            'version_sha256': version, 'new_optimizer_update': False},
        'observations': rows, 'loss_path': [row['loss'] for row in rows],
        'physical_native_worlds': len(proofs), 'physical_world_directory_count': len(directories),
        'physical_researcher_responses': replies, 'logical_completed_researcher_responses': logical,
        'reused_responses_in_completed_worlds': 0, 'native_run_proofs': proofs,
        'partial_physical_run_proofs': partial, 'claims': claims,
        'audit': {'raw_root': str(root), 'raw_inventory_sha256': digest(inventory),
            'raw_input_sha256s': inventory, 'raw_files_verified_unchanged': len(inventory),
            'new_model_calls': 0, 'new_container_executions': 0, 'checkpoint_loss_reextracted': True,
            'final_policy_draws_and_likelihoods_replayed': True, 'parent_historical_audit_repeated': classification == ACTUAL,
            'replay_source_proofs': source_proofs, 'analysis_source_sha256': file_sha256(Path(__file__)),
            'limits': ['Two fresh draws from the final saved corrected-control proposal, not another optimizer update.',
                'Historical v11 outcomes are provenance/calibration, not a causal concurrent comparison group.',
                'No expected-loss improvement, variance reduction, held-out or useful-invention claim follows.']}}
    result['content_sha256'] = digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--parent-audit', type=Path, required=True)
    parser.add_argument('--parent-audit-source', type=Path, required=True)
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args()
    plan = read(args.run / 'plan.json')
    parent_run = Path(plan['parent']['raw_root']).resolve()
    if (args.output.resolve() == args.parent_audit.resolve()
            or any(args.output.resolve().is_relative_to(path.resolve()) for path in (args.run, parent_run, args.parent_audit_source))):
        raise ValueError('audit output must be outside both immutable raw/source evidence roots')
    report = analyze(args.run, expected_source=args.expected_source, parent_audit=args.parent_audit,
        parent_audit_source=args.parent_audit_source, require_complete=not args.allow_incomplete)
    write_json_atomic(args.output, report, sort_keys=True, allow_nan=False)
    print(json.dumps({key: report[key] for key in ('status', 'physical_native_worlds',
        'physical_researcher_responses', 'content_sha256')}, sort_keys=True))


if __name__ == '__main__':
    main()
