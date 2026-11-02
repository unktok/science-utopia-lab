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
    FIXTURE, ReadOnlyCampaign, _inventory, audit_native_run, authoring_proofs,
    partial_physical_proof, read,
)
from scripts.analyze_native_open_estimators_v11 import incumbent_path, replay_source_proofs
from scripts.analyze_native_objective_structure_v8 import (
    _bind_authoring_instructions, cross_score_measurement, graph_change, objective_specs,
)
from utopia.optimization.native_manifest_inbox import audit_manifest_inbox
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_migration import native_execution_nodes
from utopia.utils.data_utils import file_sha256, write_json_atomic

RAW_SCHEMA = 'scienceutopia.native-objective-redesign-pilot.v12'
SCHEMA = 'scienceutopia.native-objective-redesign-independent-audit.v12'
ACTUAL = 'actual-native-qwen-objective-redesign-development-v12'
EXPERIMENT = {'protocol': 'native-objective-redesign-v12', 'role': 'development-engineering'}
ARM_IDS = ('native-joint-v5-throughput', 'native-joint-v5-net-reviewed-utility')
GENERATIONS, DRAWS, SEED = 3, 1, 42


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
    result = replay_source_proofs(expected_source, classification)
    if classification != FIXTURE:
        for name in ('scripts/run_native_objective_redesign_v12.py',
                'scripts/analyze_native_objective_structure_v8.py'):
            original = subprocess.check_output(['git', 'show', f'{expected_source}:{name}'], cwd=ROOT)
            actual, local = hashlib.sha256(original).hexdigest(), file_sha256(ROOT / name)
            if actual != local:
                raise ValueError('replay-critical v12 driver/structural audit source differs from actual pin')
            result['files'][name] = {'actual_source_sha256': actual, 'analysis_source_sha256': local}
    return result


def _validate_plan(raw, plan, expected_source):
    losses = objective_specs()
    if (raw.get('schema') != RAW_SCHEMA or plan.get('schema') != RAW_SCHEMA
            or raw.get('content_sha256') != digest({k:v for k,v in raw.items() if k != 'content_sha256'})
            or raw.get('plan') != plan or raw.get('source_commit') != expected_source
            or plan.get('arm_ids') != list(ARM_IDS) or plan.get('losses') != [losses[k] for k in ARM_IDS]
            or plan.get('seed') != SEED or plan.get('mode') != 'blackbox'
            or plan.get('generations') != GENERATIONS or plan.get('draws_per_generation') != DRAWS
            or plan.get('experiment') != EXPERIMENT
            or plan.get('population') != {'authors': 5, 'conference_setting': 1}
            or any(plan.get(k) is not False for k in ('shared_physical_trajectories',
                'scientific_benefit_required', 'structural_novelty_reward'))
            or plan.get('external_designer_provider') != 'self-reported Codex specialist'
            or not isinstance(plan.get('instructions'), str) or not plan['instructions']):
        raise ValueError('v12 fixed loss/source/budget/open redesign plan differs')
    classification, world = raw.get('classification'), plan.get('world', {})
    if (classification not in (ACTUAL, FIXTURE) or world.get('classification') != classification
            or plan.get('classification') != classification or world.get('source_commit') != expected_source
            or world.get('years') != 2 or world.get('corpus_years') != 4
            or world.get('experiment') != EXPERIMENT):
        raise ValueError('v12 original-world/source/classification binding differs')
    if classification == ACTUAL and (len(expected_source) != 40
            or any(c not in '0123456789abcdef' for c in expected_source)
            or raw.get('configured_researcher_provider') != 'qwen3:8b'):
        raise ValueError('actual v12 requires fixed Qwen and exact source pin')
    if classification == ACTUAL:
        from scripts.run_native_objective_redesign_v12 import INSTRUCTIONS
        if plan['instructions'] != INSTRUCTIONS:
            raise ValueError('actual authoring instructions differ from the source-pinned contract')
    SystemSpec.from_dict(plan['initial_system'])
    return losses, classification


def _read_arm(root, identity, raw, plan, loss):
    directory = root / 'arms' / identity
    state = read(directory / 'campaign/native-adaptive-state.json')
    binding = state['binding']
    if (binding['world'] != plan['world'] or binding['loss_spec'] != loss
            or binding['initial_system'] != plan['initial_system'] or binding['seeds'] != [SEED]
            or binding['seed'] != SEED or binding['mode'] != 'blackbox'
            or binding.get('expectation_estimator') is not None):
        raise ValueError('objective arm world/initial/loss/blackbox binding differs')
    controller = ReadOnlyCampaign(directory / 'campaign',
        initial_system=SystemSpec.from_dict(binding['initial_system']), loss_spec=loss,
        seeds=binding['seeds'], world_binding=binding['world'], strategies=binding['strategies'],
        **{key: binding[key] for key in ('mode', 'seed', 'learning_rate',
            'strategy_learning_rate', 'strategy_baseline', 'exploration')})
    records, pending = controller.state['records'], controller.state['pending']
    all_records = records + ([pending] if pending else [])
    if (len(all_records) > GENERATIONS or any(record['request']['count'] != DRAWS for record in all_records)
            or any(record['request']['generation'] != i for i, record in enumerate(all_records))):
        raise ValueError('three-generation/one-draw budget or order differs')
    summary = raw['arms'][identity]
    if any(summary.get(key) != value for key, value in (
            ('binding', binding), ('records', records), ('pending', pending),
            ('authoring', audit_manifest_inbox(directory / 'authoring')))):
        raise ValueError('raw objective arm differs from actual replay input')
    for index, record in enumerate(all_records):
        if record['request']['history'] != controller._history(records[:index]):
            raise ValueError('authoring uses other-arm/future/changed history')
    authors = authoring_proofs(directory / 'authoring', all_records)
    _bind_authoring_instructions(directory / 'authoring', all_records, plan['instructions'])
    return controller, authors


def _row(identity, record, draw=None, observation=None):
    candidate = draw['suggestion']['candidate'] if draw and draw.get('suggestion') else None
    parent = record['request']['parent_system']
    return {'arm': identity, 'generation': record['request']['generation'], 'draw_index': 0,
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
    failures = committed = 0
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
            if record['generation_error'] is not None:
                if record['draws'] or record['observations']:
                    raise ValueError('generation failure claims executed draws')
                row = _row(identity, record)
                row['status'] = 'generation-failure'
                rows.append(row)
                failures += 1
                continue
            if len(record['draws']) != DRAWS or len(record['observations']) != DRAWS:
                raise ValueError('completed generation lacks its exact single draw')
            draw, observation = record['draws'][0], record['observations'][0]
            if observation is not None:
                if observation['observation_id'] in observation_ids:
                    raise ValueError('exact observation identity reused across distinct attempts')
                observation_ids.add(observation['observation_id'])
            committed += 1
            row = _row(identity, record, draw, observation)
            if row['system'] is not None:
                row['lineage'] = {'vs_initial': design_change(plan['initial_system'], row['system']),
                    'vs_parent': design_change(record['request']['parent_system'], row['system'])}
            valid = observation and observation['status'] == 'complete' and not observation['metadata'].get('technical_failures')
            if valid:
                runs = observation['metadata'].get('runs', [])
                if len(runs) != 1 or runs[0]['run_id'] in physical_ids or runs[0]['run_id'] not in declared:
                    raise ValueError('completed draw lacks one unique declared physical world')
                evidence = runs[0]
                proof = audit_native_run(root, draw, observation, evidence, plan['world'], classification,
                    expected_experiment=EXPERIMENT, expected_loss=losses[identity])
                measurement = proof['measurement']
                evaluations, cross_scores = cross_score_measurement(measurement, losses, identity, observation['loss'])
                if ([measurement] != observation['metadata']['measurements']
                        or evaluations[identity] != observation['metadata']['loss_evaluation']
                        or proof['native_loss'] != observation['loss']):
                    raise ValueError('saved loss/measurements differ from independently read checkpoint')
                row.update(status='complete', own_loss=observation['loss'], loss=observation['loss'],
                    cross_scores=cross_scores, loss_evaluations=evaluations, metrics=measurement['metrics'],
                    checkpoint_sha256=proof['checkpoint_sha256'], physical_proof=proof, run_id=evidence['run_id'])
                physical_ids.add(evidence['run_id'])
                native_proofs.append({'arm': identity, 'generation': row['generation'], 'draw_index': 0,
                    'run_id': evidence['run_id'], **proof})
            else:
                failures += 1
                if observation is not None and observation.get('loss') is not None:
                    raise ValueError('technical failure converted to numerical loss')
            rows.append(row)
        incumbents = incumbent_path(rows)
        ties = incumbents['best_observation_ties']
        representative = ties[0]['observation_id'] if ties else None
        arms[identity] = {'objective_id': identity, 'loss_spec': losses[identity],
            'records': controller.state['records'], 'pending': controller.state['pending'],
            'authoring_proofs': authors, 'observations': rows, 'incumbents': incumbents,
            'loss_path': [row['loss'] for row in rows],
            'selection': {'best_loss': incumbents['best_loss'], 'tie_count': len(ties),
                'representative_observation_id': representative,
                'criterion': 'minimum own development loss; earliest exact row only for display; all ties retained'}}
    terminal = all(len(arm['records']) == GENERATIONS and arm['pending'] is None for arm in arms.values())
    complete = terminal and len(physical_ids) == 6 and failures == 0
    status = 'complete' if complete else 'budget-complete-with-failures' if terminal else 'in-progress'
    expected_summary = {'status': status, 'budget_terminal': terminal,
        'planned_native_world_budget': 6, 'committed_draws': committed,
        'complete_native_worlds': len(physical_ids), 'technical_failures': failures}
    if any(raw.get(k) != value for k,value in expected_summary.items()):
        raise ValueError(f'raw native draw/status/failure summary differs: {expected_summary}')
    if require_complete and not terminal:
        raise ValueError('three generations per objective must be terminal; incomplete audit requires explicit flag')
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
    if complete and (len(caches) != 6 or logical != replies
            or replies != sum(proof['response_proof']['researcher_responses'] for proof in native_proofs)):
        raise ValueError('physical/logical native reply counts differ or responses reused')
    claims = deepcopy(raw.get('claims', {}))
    forbidden = ('held_out', 'causal_institutional_benefit', 'scientific_value',
        'designer_improvement_established', 'full_native_world_pathwise_autograd',
        'external_authorship_authenticated')
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
            'new_container_executions': 0, 'campaign_updates_replayed': True,
            'campaign_and_lineage_replayed': True,
            'checkpoint_loss_reextracted': True, 'own_history_only_verified': True,
            'all_observations_and_exact_ties_retained': True, 'replay_source_proofs': source_proof,
            'analysis_source_sha256': file_sha256(Path(__file__)),
            'limits': ['Same-checkpoint cross-scores are development diagnostics, not held-out metrics.',
                'One development seed and six worlds do not establish superiority or causal science-policy benefits.',
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
