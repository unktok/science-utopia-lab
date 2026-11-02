#!/usr/bin/env python3
"""Read-only objective-conditioned, open-code native redesign audit.

No simulator, model, generated source, or container is executed. Native loss
measurements and source/protocol/wiring/process receipts are independently
reconstructed. Cross-scores reuse development checkpoints, never held-out data.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_native_open_v7 import (
    FIXTURE, _inventory, authoring_proofs,
    partial_physical_proof, read,
)
from scripts.analyze_native_open_estimators_v11 import incumbent_path
from scripts.native_activity_effect_audit_v12 import activity_effect_proof
from scripts.native_capability_effect_audit_v13 import capability_effect_proof
from scripts.analyze_native_objective_structure_v8 import (
    _bind_authoring_instructions, cross_score_measurement, graph_change,
)
from utopia.optimization.native_manifest_inbox import audit_manifest_inbox
from utopia.optimization.native_nested_search import NativeNestedDesignCampaign, STAGES, COUNTS
from utopia.optimization.loss import load_loss_spec
from scripts.native_nested_estimator_audit_v13 import conditional_update_proof
from scripts.native_physical_evidence_v13 import audit_native_run_v13
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_migration import native_execution_nodes
from utopia.utils.data_utils import file_sha256, write_json_atomic

RAW_SCHEMA = 'scienceutopia.native-nested-search-pilot.v13'
SCHEMA = 'scienceutopia.native-nested-search-independent-audit.v13'
ACTUAL = 'actual-native-qwen-nested-search-development-v13'
EXPERIMENT = {'protocol': 'native-nested-search-v13', 'role': 'development-engineering'}
ARM_IDS = ('native-joint-v5-throughput', 'native-reviewed-production-efficiency-v13')
GENERATIONS, SEED = 3, 42


def objective_specs():
    return {identity: load_loss_spec(ROOT / 'research/objectives/losses' / (identity + '.json'))
        for identity in ARM_IDS}


class ReadOnlyNestedCampaign(NativeNestedDesignCampaign):
    def _save(self):
        raise AssertionError('audit must never persist a nested campaign')


def executable_contracts(system):
    """Exact declared bodies/ABIs, separate from claims of actual execution."""
    spec = SystemSpec.from_dict(system)
    sources = {node.mechanism_id: {
        'source': node.parameters['code_artifact']['source'],
        'source_sha256': hashlib.sha256(node.parameters['code_artifact']['source'].encode()).hexdigest(),
        'source_value_sha256': digest(node.parameters['code_artifact']['source']),
        'artifact': deepcopy(node.parameters['code_artifact']),
        'runtime_image_id': node.parameters['runtime_image_id'],
    } for node in native_execution_nodes(spec) if node.implementation == 'code.python.v1'}
    protocols = {node['mechanism_id']: {key: deepcopy(node[key]) for key in
        ('family', 'implementation', 'version', 'inputs', 'outputs')}
        for node in spec.to_dict()['mechanisms']}
    processes = {node.mechanism_id: deepcopy(node.parameters) for node in spec.mechanisms
        if node.implementation == 'native.process.activity.v1'}
    return {'executable_sources': sources, 'protocols': protocols, 'processes': processes,
        'schedules': spec.to_dict()['schedules']}


def design_change(before, after):
    result = graph_change(before, after)
    old, new = executable_contracts(before), executable_contracts(after)
    old_processes, new_processes = old['processes'], new['processes']
    keys = sorted(set(old_processes) | set(new_processes))
    result['process_contract_changes'] = [
        {'mechanism_id': key, 'before': old_processes.get(key), 'after': new_processes.get(key)}
        for key in keys if old_processes.get(key) != new_processes.get(key)]
    result['counts']['process_contract_changes'] = len(result['process_contract_changes'])
    result['scope'] = ('Literal executable/source/protocol/wiring/process changes; '
        'renaming, comments and changed source text do not by themselves establish a new useful algorithm.')
    return result


def _source_proofs(expected_source, classification):
    if classification == FIXTURE:
        return {'status': 'scripted-fixture-no-actual-source-claim', 'files': {}}
    names = subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', expected_source, '--', 'utopia'], cwd=ROOT, text=True).splitlines()
    names = [name for name in names if name.endswith('.py')]
    names += ['scripts/run_native_nested_search_v13.py', 'scripts/analyze_native_open_v7.py',
        'scripts/analyze_native_society_v6.py', 'scripts/audit_native_objective_v5.py',
        'scripts/analyze_native_open_estimators_v11.py',
        'scripts/analyze_native_objective_structure_v8.py',
        'scripts/analyze_native_objective_redesign_v12.py',
        'scripts/native_activity_effect_audit_v12.py',
        'research/protocols/campaigns/native-nested-search-v13.md',
        *['research/objectives/losses/' + identity + '.json' for identity in ARM_IDS]]
    if not names:
        raise ValueError('actual native runtime source pin unavailable')
    proofs = {}
    for name in names:
        original = subprocess.check_output(['git', 'show', f'{expected_source}:{name}'], cwd=ROOT)
        actual, local = hashlib.sha256(original).hexdigest(), file_sha256(ROOT / name)
        if actual != local:
            raise ValueError('replay-critical native runtime/driver/audit helper differs from actual pin: ' + name)
        proofs[name] = {'actual_source_sha256': actual, 'analysis_source_sha256': local}
    return {'status': 'verified-exact-replay-source-blobs', 'files': proofs}

def _validate_plan(raw, plan, expected_source):
    losses = objective_specs()
    if (raw.get('schema') != RAW_SCHEMA or plan.get('schema') != RAW_SCHEMA
            or raw.get('content_sha256') != digest({k:v for k,v in raw.items() if k != 'content_sha256'})
            or raw.get('plan') != plan or raw.get('source_commit') != expected_source
            or plan.get('arm_ids') != list(ARM_IDS) or plan.get('losses') != [losses[k] for k in ARM_IDS]
            or plan.get('seed') != SEED
            or plan.get('mode') != 'free-vocabulary-LOO-update-forward-free-redesign-forward'
            or plan.get('stages') != list(STAGES) or plan.get('stage_counts') != list(COUNTS)
            or plan.get('learning_rate') != .1 or plan.get('experiment') != EXPERIMENT
            or plan.get('population') != {'authors': 5, 'conference_setting': 1}
            or any(plan.get(k) is not False for k in ('shared_physical_trajectories',
                'scientific_benefit_required', 'structural_novelty_reward'))
            or plan.get('external_designer_provider') != 'self-reported Codex specialist'
            or not isinstance(plan.get('instructions'), str) or not plan['instructions']):
        raise ValueError('v13 exact loss/source/nested budget/open redesign plan differs')
    classification, world = raw.get('classification'), plan.get('world', {})
    if (classification not in (ACTUAL, FIXTURE) or world.get('classification') != classification
            or plan.get('classification') != classification or world.get('source_commit') != expected_source
            or world.get('years') != 2 or world.get('corpus_years') != 4
            or world.get('experiment') != EXPERIMENT):
        raise ValueError('v13 original-world/source/classification binding differs')
    if classification == ACTUAL:
        from scripts.run_native_nested_search_v13 import INSTRUCTIONS
        if (len(expected_source) != 40 or any(c not in '0123456789abcdef' for c in expected_source)
                or raw.get('configured_researcher_provider') != 'qwen3:8b'
                or plan['instructions'] != INSTRUCTIONS
                or any(not isinstance(world.get(key), str) or len(world[key]) != 64
                    or any(c not in '0123456789abcdef' for c in world[key])
                    for key in ('model_digest', 'corpus_sha256'))
                or world.get('runtime_seed_binding', {}).get('python_hash_seed_environment') != '42'
                or type(world.get('runtime_seed_binding', {}).get('python_hash_probe')) is not int):
            raise ValueError('actual v13 requires exact fixed-Qwen/source/authoring contract')
    SystemSpec.from_dict(plan['initial_system'])
    return losses, classification

def _read_arm(root, identity, raw, plan, loss):
    directory = root / 'arms' / identity
    state = read(directory / 'campaign/native-nested-state.json')
    binding = state['binding']
    if (binding['world'] != plan['world'] or binding['loss_spec'] != loss
            or binding['initial_system'] != plan['initial_system'] or binding['seeds'] != [SEED]
            or binding['seed'] != SEED or binding['learning_rate'] != .1):
        raise ValueError('nested objective arm world/initial/loss/seed/update-rate binding differs')
    controller = ReadOnlyNestedCampaign(directory / 'campaign',
        initial_system=SystemSpec.from_dict(binding['initial_system']), loss_spec=loss,
        seeds=binding['seeds'], world_binding=binding['world'], seed=SEED, learning_rate=.1)
    records, pending = controller.state['records'], controller.state['pending']
    all_records = records + ([pending] if pending else [])
    summary = raw['arms'][identity]
    if any(summary.get(key) != value for key, value in (
            ('binding', binding), ('records', records), ('pending', pending),
            ('authoring', audit_manifest_inbox(directory / 'authoring')))):
        raise ValueError('raw nested objective arm differs from actual replay input')
    for index, record in enumerate(all_records):
        if record['request']['history'] != records[:index]:
            raise ValueError('authoring uses other-arm/future/changed own history')
    external = [record for record in all_records if record['request']['external_authoring']]
    authors = authoring_proofs(directory / 'authoring', external)
    _bind_authoring_instructions(directory / 'authoring', external, plan['instructions'])
    return controller, authors

def _row(identity, record, draw=None, observation=None, draw_index=None):
    candidate = draw['suggestion']['candidate'] if draw and draw.get('suggestion') else None
    parent = record['request']['parent_system']
    return {'arm': identity, 'stage': record['stage'], 'generation': record['request']['generation'], 'draw_index': draw_index,
        'scheduled_native_slots': record['request']['count'] if draw is None else 1,
        'version_sha256': record['version_sha256'], 'observation_id': observation['observation_id'] if observation else None,
        'suggestion_id': draw['suggestion']['suggestion_id'] if candidate else None,
        'system_fingerprint': SystemSpec.from_dict(candidate).fingerprint if candidate else None,
        'parent_system_fingerprint': SystemSpec.from_dict(parent).fingerprint,
        'system': candidate, 'contracts': executable_contracts(candidate) if candidate else None,
        'draw': deepcopy(draw), 'observation': deepcopy(observation),
        'generation_error': deepcopy(record['generation_error']), 'status': 'technical-failure',
        'own_loss': None, 'loss': None, 'cross_scores': {key:None for key in ARM_IDS},
        'loss_evaluations': None, 'metrics': None, 'checkpoint_sha256': None,
        'physical_proof': None, 'lineage': None}


def analyze(run, *, expected_source, require_complete=True):
    root = Path(run).resolve()
    before = _inventory(root)
    try:
        return _analyze(root, expected_source=expected_source,
            require_complete=require_complete, inventory=before)
    finally:
        if _inventory(root) != before:
            raise ValueError('raw evidence changed during read-only audit')


def _analyze(root, *, expected_source, require_complete, inventory):
    raw, plan = read(root / 'evidence.json'), read(root / 'plan.json')
    losses, classification = _validate_plan(raw, plan, expected_source)
    source_proof = _source_proofs(expected_source, classification)
    if set(raw['arms']) != set(ARM_IDS):
        raise ValueError('missing or extra objective arm')
    arms, native_proofs, declared, physical_ids, observation_ids = {}, [], {}, set(), set()
    failures = committed = slots = 0
    for identity in ARM_IDS:
        controller, authors = _read_arm(root, identity, raw, plan, losses[identity])
        rows = []
        for record in controller.state['records'] + ([controller.state['pending']] if controller.state['pending'] else []):
            for draw in record['draws']:
                if draw.get('suggestion'):
                    run_id = draw['suggestion']['suggestion_id'] + '-s42'
                    if run_id in declared:
                        raise ValueError('physical run reused by logical draws')
                    declared[run_id] = SystemSpec.from_dict(draw['suggestion']['candidate'])
        for record in controller.state['records']:
            slots += record['request']['count']
            if record['generation_error'] is not None:
                row = _row(identity, record)
                row['status'] = 'generation-failure'
                rows.append(row)
                failures += record['request']['count']
                continue
            if (len(record['draws']) != record['request']['count']
                    or len(record['observations']) != record['request']['count']):
                raise ValueError('completed nested stage lacks its exact scheduled draws')
            for draw_index, (draw, observation) in enumerate(zip(record['draws'], record['observations'])):
                if observation is not None:
                    if observation['observation_id'] in observation_ids:
                        raise ValueError('observation identity reused across distinct attempts')
                    observation_ids.add(observation['observation_id'])
                committed += 1
                row = _row(identity, record, draw, observation, draw_index)
                if row['system'] is not None:
                    row['lineage'] = {'vs_initial': design_change(plan['initial_system'], row['system']),
                        'vs_parent': design_change(record['request']['parent_system'], row['system'])}
                valid = observation and observation['status'] == 'complete' and not observation['metadata'].get('technical_failures')
                if valid:
                    runs = observation['metadata'].get('runs', [])
                    if len(runs) != 1 or runs[0]['run_id'] in physical_ids or runs[0]['run_id'] not in declared:
                        raise ValueError('completed draw lacks one unique declared physical world')
                    evidence = runs[0]
                    proof = audit_native_run_v13(root, draw, observation, evidence, plan['world'], classification,
                        expected_experiment=EXPERIMENT, expected_loss=losses[identity])
                    proof['activity_effect_proof'] = activity_effect_proof(
                        root / 'worlds' / evidence['run_id'], declared[evidence['run_id']], evidence['checkpoint_path'])
                    proof['capability_effect_proof'] = capability_effect_proof(
                        root / 'worlds' / evidence['run_id'], declared[evidence['run_id']], evidence['checkpoint_path'])
                    measurement = proof['measurement']
                    evaluations, cross_scores = cross_score_measurement(measurement, losses, identity, observation['loss'])
                    if ([measurement] != observation['metadata']['measurements']
                            or evaluations[identity] != observation['metadata']['loss_evaluation']
                            or proof['native_loss'] != observation['loss']):
                        raise ValueError('saved loss differs from independently read checkpoint')
                    row.update(status='complete', own_loss=observation['loss'], loss=observation['loss'],
                        cross_scores=cross_scores, loss_evaluations=evaluations, metrics=measurement['metrics'],
                        checkpoint_sha256=proof['checkpoint_sha256'], physical_proof=proof, run_id=evidence['run_id'])
                    physical_ids.add(evidence['run_id'])
                    native_proofs.append({'arm': identity, 'stage': row['stage'],
                        'generation': row['generation'], 'draw_index': draw_index,
                        'run_id': evidence['run_id'], **proof})
                else:
                    failures += 1
                    if observation is not None and observation.get('loss') is not None:
                        raise ValueError('technical failure converted to numerical loss')
                rows.append(row)
        estimator_proof = conditional_update_proof(controller.state['records'])
        incumbents = incumbent_path(rows)
        by_observation = {row['observation_id']: row['stage'] for row in rows if row['observation_id']}
        for path, row in zip(incumbents['path'], rows):
            path['stage'] = row['stage']
            for tie in path['best_observation_ties']:
                tie['stage'] = by_observation[tie['observation_id']]
        for tie in incumbents['best_observation_ties']:
            tie['stage'] = by_observation[tie['observation_id']]
        ties = incumbents['best_observation_ties']
        representative = ties[0]['observation_id'] if ties else None
        arms[identity] = {'objective_id': identity, 'loss_spec': losses[identity],
            'records': controller.state['records'], 'pending': controller.state['pending'],
            'authoring_proofs': authors, 'observations': rows, 'incumbents': incumbents,
            'conditional_update_proof': estimator_proof,
            'loss_path': [row['loss'] for row in rows],
            'selection': {'best_loss': incumbents['best_loss'], 'tie_count': len(ties),
                'representative_observation_id': representative,
                'criterion': 'minimum own development loss; earliest exact row only for display; all ties retained'}}
    terminal = all(len(arm['records']) == GENERATIONS and arm['pending'] is None for arm in arms.values())
    complete = terminal and len(physical_ids) == 8 and failures == 0
    status = 'complete' if complete else 'budget-complete-with-failures' if terminal else 'in-progress'
    expected_summary = {'status': status, 'budget_terminal': terminal,
        'planned_native_world_budget': 8, 'consumed_native_slots': slots, 'committed_draws': committed,
        'complete_native_worlds': len(physical_ids), 'technical_failures': failures}
    if any(raw.get(k) != value for k,value in expected_summary.items()):
        raise ValueError(f'raw native draw/status/failure summary differs: {expected_summary}')
    if require_complete and not terminal:
        raise ValueError('three fixed stages per objective must be terminal; incomplete audit requires explicit flag')
    caches, partial = [], []
    physical_directories = {path.name for path in (root / 'worlds').iterdir() if path.is_dir()} if (root / 'worlds').exists() else set()
    if not physical_directories <= declared.keys() or not physical_ids <= physical_directories:
        raise ValueError('undeclared/missing physical world directory')
    for path in sorted((root / 'worlds').glob('*/replies/responses.sqlite')):
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True) as db:
            counts = dict(db.execute('SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
        caches.append({'path': str(path.resolve()), 'sha256': file_sha256(path), 'outcomes': counts})
        if path.parent.parent.name not in physical_ids:
            partial.append(partial_physical_proof(path.parent.parent, declared[path.parent.parent.name], plan['world'], classification))
    cache_ids = {Path(cache['path']).parent.parent.name for cache in caches}
    for run_id in sorted(physical_directories - physical_ids - cache_ids):
        cell = root / 'worlds' / run_id
        if not (cell / 'system.json').exists() or read(cell / 'system.json') != declared[run_id].to_dict():
            raise ValueError('partial world without journal lacks its declared source SystemSpec')
        partial.append({'run_id': run_id, 'status': 'partial-before-response-journal', 'loss': None,
            'files': {str(path.relative_to(cell)): file_sha256(path)
                for path in sorted(cell.rglob('*')) if path.is_file()},
            'scope': 'Declared native attempt exists, but no response journal or completed loss observation exists.'})
    replies = sum(cache['outcomes'].get('response', 0) for cache in caches)
    if caches != raw.get('physical_response_caches') or replies != raw.get('physical_reply_count'):
        raise ValueError('physical response cache/count/hash differs')
    logical = sum(proof['response_proof']['cumulative_responses_per_year'][-1] for proof in native_proofs)
    if complete and (len(caches) != 8 or logical != replies
            or replies != sum(proof['response_proof']['researcher_responses'] for proof in native_proofs)):
        raise ValueError('physical/logical native reply counts differ or responses reused')
    claims = deepcopy(raw.get('claims', {}))
    forbidden = ('held_out', 'causal_institutional_benefit', 'scientific_value',
        'designer_improvement_established', 'full_native_world_pathwise_autograd',
        'external_authorship_authenticated', 'variance_reduction_established')
    if any(claims.get(key) is not False for key in forbidden):
        raise ValueError('raw claims exceed objective-conditioned development evidence')
    if classification == ACTUAL and (claims.get('live_fixed_Qwen_researchers') != (replies > 0)
            or claims.get('scripted_researcher_HTTP') is not False):
        raise ValueError('actual researcher attribution differs')
    if classification == FIXTURE:
        claims.update(live_fixed_Qwen_researchers=False, scripted_researcher_HTTP=True)
    selected = {}
    for identity, arm in arms.items():
        chosen = arm['selection']['representative_observation_id']
        selected[identity] = next((row['cross_scores'] for row in arm['observations']
            if chosen is not None and row['observation_id'] == chosen), None)
    result = {'schema': SCHEMA, 'classification': classification, 'status': status,
        'source_commit': expected_source, 'objective_order': list(ARM_IDS), 'loss_specs': losses,
        'arms': arms, 'selected_cross_objective_matrix': selected,
        'planned_native_world_budget': 8, 'consumed_native_slots': slots,
        'physical_world_directory_count': len(physical_directories), 'physical_cache_count': len(caches),
        'physical_native_worlds': len(physical_ids), 'logical_completed_draws': len(native_proofs),
        'physical_researcher_responses': replies, 'logical_completed_researcher_responses': logical,
        'reused_responses_in_completed_worlds': 0,
        'completed_wire_requests': sum(p['response_proof']['wire_requests'] for p in native_proofs),
        'completed_code_executions': sum(p['code_proof']['recorded_executions'] for p in native_proofs),
        'completed_committed_code_events': sum(p['code_proof']['committed_events'] for p in native_proofs),
        'native_run_proofs': native_proofs, 'partial_physical_run_proofs': partial, 'claims': claims,
        'held_out_metrics': {'status': 'not-defined-or-measured'},
        'promotion_policy': {'status': 'not-defined-or-applied'},
        'audit': {'raw_root': str(root), 'raw_evidence_sha256': inventory['evidence.json'],
            'raw_inventory_sha256': digest(inventory), 'raw_input_sha256s': inventory,
            'raw_files_verified_unchanged': len(inventory), 'new_model_calls': 0,
            'new_container_executions': 0, 'campaign_updates_replayed': True, 'sole_conditional_LR_update_analytically_rederived': True,
            'campaign_and_lineage_replayed': True,
            'checkpoint_loss_reextracted': True, 'own_history_only_verified': True,
            'all_observations_and_exact_ties_retained': True, 'replay_source_proofs': source_proof,
            'analysis_source_sha256': file_sha256(Path(__file__)),
            'analysis_helper_source_sha256s': {name: file_sha256(ROOT/'scripts'/name) for name in (
                'native_nested_estimator_audit_v13.py', 'native_capability_effect_audit_v13.py',
                'native_physical_evidence_v13.py')},
            'limits': ['Same-checkpoint cross-scores are development diagnostics, not held-out metrics.',
                'One development seed and eight slots do not establish superiority or causal science-policy benefits.',
                'Source text changes and actual execution are distinct from useful algorithm invention.',
                'Designer identity is self-reported, not provider authenticated.',
                'Failed attempts are retained with null losses; no hidden fairness/quality/novelty veto applies.']}}
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
    print(json.dumps({key: report[key] for key in ('status', 'physical_native_worlds',
        'physical_researcher_responses', 'content_sha256')}, sort_keys=True))


if __name__ == '__main__':
    main()
