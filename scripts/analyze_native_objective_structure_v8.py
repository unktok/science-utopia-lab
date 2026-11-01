#!/usr/bin/env python3
"""Read-only audit of the two-objective native structural pilot (v8).

This module never executes a simulator, generated source, or a model.  It
replays the saved campaign/authoring contracts and independently reads the
original native checkpoints.  Optimization loss, technical validity, held-out
metrics, and promotion policy remain separate; this report contains only the
first two and explicitly defines neither of the latter two.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_native_open_v7 import (
    FIXTURE,
    ReadOnlyCampaign,
    _inventory,
    audit_native_run,
    authoring_proofs,
    partial_physical_proof,
    read,
)
from utopia.optimization.loss import evaluate_loss, load_loss_spec
from utopia.optimization.native_manifest_inbox import audit_manifest_inbox
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_migration import native_execution_nodes
from utopia.utils.data_utils import write_json_atomic
from utopia.utils.data_utils import file_sha256

RAW_SCHEMA = 'scienceutopia.native-objective-structure-pilot.v8'
SCHEMA = 'scienceutopia.native-objective-structure-audit.v8'
FIGURE_DATA_SCHEMA = 'scienceutopia.native-objective-structure-figure-data.v8'
ACTUAL = 'actual-native-qwen-objective-structure-development-v8'
PROTOCOL = 'native-objective-structure-v8'
EXPERIMENT = {'protocol': PROTOCOL, 'role': 'development-engineering'}
ARM_IDS = ('native-joint-v5-throughput', 'native-joint-v5-net-reviewed-utility')
INSTRUCTIONS_SHA256 = '7302a51f594b20f489ba3bc27871a765e68f5648321877138e3b6ee7c484bc49'


def objective_specs():
    return {identity: load_loss_spec(ROOT / 'research/objectives/losses' / f'{identity}.json')
            for identity in ARM_IDS}


def _edge(value):
    return (value['source_mechanism'], value['source_port'], value['target_mechanism'],
            value['target_port'], value['channel'], value.get('latency', 0))


def _sources(spec):
    result = {}
    for node in native_execution_nodes(spec):
        if node.implementation == 'code.python.v1':
            result[node.mechanism_id] = digest(node.parameters['code_artifact']['source'])
    return result


def _protocol(node):
    return {key: node[key] for key in ('family', 'implementation', 'version', 'inputs', 'outputs')}


def _renamed_sources(old_sources, new_sources, removed_nodes, added_nodes):
    pairs = []
    for source_sha256 in sorted(set(old_sources.values()) & set(new_sources.values())):
        old_ids = sorted(identity for identity in removed_nodes if old_sources.get(identity) == source_sha256)
        new_ids = sorted(identity for identity in added_nodes if new_sources.get(identity) == source_sha256)
        pairs.extend({'source_sha256': source_sha256, 'before_mechanism_id': old,
                      'after_mechanism_id': new} for old, new in zip(old_ids, new_ids))
    return pairs


def graph_change(before, after):
    """Exact graph/source set changes; no semantic-effect inference."""
    before, after = SystemSpec.from_dict(before), SystemSpec.from_dict(after)
    old_node_values = {node['mechanism_id']: node for node in before.to_dict()['mechanisms']}
    new_node_values = {node['mechanism_id']: node for node in after.to_dict()['mechanisms']}
    old_nodes, new_nodes = set(old_node_values), set(new_node_values)
    old_edges = {_edge(value) for value in before.to_dict()['connections']}
    new_edges = {_edge(value) for value in after.to_dict()['connections']}
    removed, added = old_edges - new_edges, new_edges - old_edges
    # A rewire is an exact endpoint-pair whose ports/channel/latency changed.
    # Added/removed edge sets remain authoritative and are never reduced by it.
    old_by_pair = {(e[0], e[2]): e for e in removed}
    new_by_pair = {(e[0], e[2]): e for e in added}
    rewired_pairs = sorted(set(old_by_pair) & set(new_by_pair))
    old_sources, new_sources = _sources(before), _sources(after)
    source_changed = sorted(identity for identity in old_sources.keys() & new_sources.keys()
                            if old_sources[identity] != new_sources[identity])
    protocol_changed = sorted(identity for identity in old_nodes & new_nodes
        if _protocol(old_node_values[identity]) != _protocol(new_node_values[identity]))
    configuration_changed = sorted(identity for identity in old_nodes & new_nodes
        if old_node_values[identity]['parameters'] != new_node_values[identity]['parameters'])
    old_source_counts, new_source_counts = Counter(old_sources.values()), Counter(new_sources.values())
    source_bodies_added = list((new_source_counts-old_source_counts).elements())
    source_bodies_removed = list((old_source_counts-new_source_counts).elements())
    renamed_sources = _renamed_sources(old_sources, new_sources, old_nodes-new_nodes, new_nodes-old_nodes)
    old_schedules = {digest(value): value for value in before.to_dict()['schedules']}
    new_schedules = {digest(value): value for value in after.to_dict()['schedules']}
    initial_state_changed = before.initial_state != after.initial_state
    return {'from_fingerprint': before.fingerprint, 'to_fingerprint': after.fingerprint,
        'nodes_added': sorted(new_nodes-old_nodes), 'nodes_removed': sorted(old_nodes-new_nodes),
        'edges_added': [list(e) for e in sorted(added)],
        'edges_removed': [list(e) for e in sorted(removed)],
        'rewired_endpoint_pairs': [list(e) for e in rewired_pairs],
        'source_changes': [{'mechanism_id': identity, 'before_sha256': old_sources[identity],
                            'after_sha256': new_sources[identity]} for identity in source_changed],
        'source_bodies_added': sorted(source_bodies_added),
        'source_bodies_removed': sorted(source_bodies_removed),
        'same_source_body_renamed_ids': renamed_sources,
        'protocol_changes': [{'mechanism_id': identity, 'before': _protocol(old_node_values[identity]),
                              'after': _protocol(new_node_values[identity])}
                             for identity in protocol_changed],
        'mechanism_configuration_changes': configuration_changed,
        'schedules_added': [new_schedules[key] for key in sorted(new_schedules.keys()-old_schedules.keys())],
        'schedules_removed': [old_schedules[key] for key in sorted(old_schedules.keys()-new_schedules.keys())],
        'initial_state_change': {'changed': initial_state_changed,
            'before_sha256': digest(before.initial_state), 'after_sha256': digest(after.initial_state),
            'counts_as_new_algorithm': False},
        'counts': {'nodes_added': len(new_nodes-old_nodes), 'nodes_removed': len(old_nodes-new_nodes),
            'edges_added': len(added), 'edges_removed': len(removed),
            'rewired_endpoint_pairs': len(rewired_pairs), 'source_changes': len(source_changed),
            'source_bodies_added': len(source_bodies_added), 'source_bodies_removed': len(source_bodies_removed),
            'same_source_body_renamed_ids': len(renamed_sources),
            'protocol_changes': len(protocol_changed),
            'mechanism_configuration_changes': len(configuration_changed),
            'schedules_added': len(new_schedules.keys()-old_schedules.keys()),
            'schedules_removed': len(old_schedules.keys()-new_schedules.keys()),
            'initial_state_changes': int(initial_state_changed)}}


def _validate_binding(identity, binding, source_commit, losses):
    world = binding['world']
    if (binding['loss_spec'] != losses[identity] or binding['seeds'] != [42]
            or binding['mode'] != 'hybrid' or binding['seed'] != 42
            or world['source_commit'] != source_commit):
        raise ValueError('objective arm loss/source/seed/adaptive binding differs')
    if world.get('experiment') not in (None, EXPERIMENT):
        raise ValueError('world experiment binding differs')
    return world


def _validate_plan(plan, losses):
    if (plan.get('schema') != RAW_SCHEMA or plan.get('experiment') != EXPERIMENT
            or plan.get('classification') not in {ACTUAL, FIXTURE}
            or plan.get('arm_ids') != list(ARM_IDS)
            or plan.get('losses') != [losses[key] for key in ARM_IDS]
            or plan.get('seed') != 42 or plan.get('generations') != 2
            or plan.get('draws_per_generation') != 2 or plan.get('mode') != 'hybrid'
            or plan.get('population') != {'authors': 5, 'conference_setting': 1}
            or plan.get('scientific_benefit_required') is not False
            or plan.get('structural_novelty_reward') is not False
            or plan.get('shared_physical_trajectories') is not False):
        raise ValueError('frozen objective/structure plan differs')
    if (digest(plan.get('instructions')) != INSTRUCTIONS_SHA256
            or plan.get('external_designer_provider') != 'self-reported Codex specialist'):
        raise ValueError('frozen external authoring contract differs')
    world = plan.get('world', {})
    if (world.get('years') != 2 or world.get('corpus_years') != 4
            or world.get('experiment') != EXPERIMENT
            or world.get('classification') != plan.get('classification')):
        raise ValueError('frozen original-native world plan differs')
    SystemSpec.from_dict(plan['initial_system'])


def _row_base(identity, record, draw_index, draw, observation):
    return {'arm': identity, 'generation': record['request']['generation'],
        'draw_index': draw_index, 'version_sha256': record['version_sha256'],
        'strategy': record['request']['strategy_id'], 'draw': deepcopy(draw),
        'observation': deepcopy(observation)}


def _finite_complete(observation):
    return (isinstance(observation, dict) and observation.get('status') == 'complete'
            and type(observation.get('loss')) in (int, float) and math.isfinite(observation['loss']))


def _bind_authoring_instructions(directory, records, instructions):
    requests = [read(path) for path in sorted((Path(directory) / 'requests').glob('*.json'))]
    for record in records:
        matches = [item for item in requests
            if item.get('request', {}).get('authoring_input') == record['request']]
        if (len(matches) != 1 or not isinstance(matches[0]['request'].get('prompt'), str)
                or not matches[0]['request']['prompt'].endswith('\n' + instructions)):
            raise ValueError('external request does not bind frozen v8 authoring instructions')


def analyze(run, *, expected_source, require_complete=True):
    root = Path(run).resolve()
    before = _inventory(root)
    try:
        return _analyze(root, expected_source=expected_source, require_complete=require_complete,
                        inventory=before)
    finally:
        if _inventory(root) != before:
            raise ValueError('raw evidence changed during read-only audit; no stable result')


def _analyze(root, *, expected_source, require_complete, inventory):
    plan, raw = read(root / 'plan.json'), read(root / 'evidence.json')
    if (raw.get('schema') != RAW_SCHEMA or raw.get('source_commit') != expected_source
            or raw.get('classification') != plan.get('classification')):
        raise ValueError('raw evidence schema/source differs')
    if 'content_sha256' in raw and digest({k: v for k, v in raw.items() if k != 'content_sha256'}) != raw['content_sha256']:
        raise ValueError('raw evidence content hash differs')
    if raw.get('plan') != plan:
        raise ValueError('evidence does not bind the immutable plan')
    losses = objective_specs()
    _validate_plan(plan, losses)
    if set(raw.get('arms', {})) != set(ARM_IDS):
        raise ValueError('raw evidence objective arms differ')
    source_commit = raw['source_commit']
    if source_commit != expected_source or len(source_commit) != 40:
        raise ValueError('explicit clean source commit required')

    arms, physical_ids, candidate_by_run, all_rows = {}, set(), {}, []
    classification = None
    for identity in ARM_IDS:
        directory = root / 'arms' / identity
        state = read(directory / 'campaign/native-adaptive-state.json')
        binding = state['binding']
        world = _validate_binding(identity, binding, source_commit, losses)
        arm_classification = world.get('classification', raw.get('classification', ACTUAL))
        if arm_classification not in {ACTUAL, FIXTURE}:
            raise ValueError('unknown evidence classification')
        classification = classification or arm_classification
        if classification != arm_classification:
            raise ValueError('objective arms use different evidence classifications')
        if arm_classification == ACTUAL and world.get('corpus_years') != 4:
            raise ValueError('actual fixed Qwen/corpus world binding differs')
        if world != plan['world'] or binding['initial_system'] != plan['initial_system']:
            raise ValueError('arm world/initial system differs from frozen plan')
        summary = raw['arms'][identity]
        for key in ('binding', 'records', 'pending', 'authoring'):
            if summary.get(key) != (binding if key == 'binding' else state[key] if key in state
                                    else audit_manifest_inbox(directory / 'authoring')):
                raise ValueError(f'raw arm {key} differs from replay input')
        controller = ReadOnlyCampaign(directory / 'campaign',
            initial_system=SystemSpec.from_dict(binding['initial_system']), loss_spec=binding['loss_spec'],
            seeds=binding['seeds'], world_binding=binding['world'], strategies=binding['strategies'],
            **{k: binding[k] for k in ('mode', 'seed', 'learning_rate', 'strategy_learning_rate',
                                       'strategy_baseline', 'exploration')})
        records, pending = controller.state['records'], controller.state['pending']
        if len(records) > 2 or any(r['request']['count'] != 2 for r in records):
            raise ValueError('two-generation/two-IID-draw budget exceeded')
        if pending is not None and pending['request']['generation'] >= 2:
            raise ValueError('pending generation exceeds declared budget')
        if require_complete and (len(records) != 2 or pending is not None):
            raise ValueError('objective structural pilot is not complete')
        authors = authoring_proofs(directory / 'authoring', records + ([pending] if pending else []))
        _bind_authoring_instructions(directory / 'authoring', records + ([pending] if pending else []),
                                     plan['instructions'])

        initial = binding['initial_system']
        rows = []
        for record in records:
            parent = record['request']['parent_system']
            if len(record['draws']) != 2 or len(record['observations']) != 2:
                raise ValueError('completed generation lacks exactly two IID draw outcomes')
            for draw_index, (draw, observation) in enumerate(zip(record['draws'], record['observations'])):
                row = _row_base(identity, record, draw_index, draw, observation)
                row.update(status='technical-failure', independent_metrics=None,
                           cross_objective_losses={key: None for key in ARM_IDS}, physical_proof=None)
                if draw['suggestion'] is not None:
                    candidate = draw['suggestion']['candidate']
                    row['graph_changes'] = {'vs_initial': graph_change(initial, candidate),
                                            'vs_parent': graph_change(parent, candidate)}
                else:
                    row['graph_changes'] = None
                if _finite_complete(observation):
                    runs = observation['metadata'].get('runs', [])
                    if len(runs) != 1 or observation['metadata'].get('technical_failures'):
                        raise ValueError('complete draw lacks exactly one successful native world')
                    evidence = runs[0]
                    if evidence['run_id'] in physical_ids:
                        raise ValueError('physical native world reused as independent draw')
                    proof = audit_native_run(root, draw, observation, evidence, world, classification,
                        expected_experiment=EXPERIMENT, expected_loss=losses[identity])
                    scores = {key: evaluate_loss(loss, [proof['measurement']]) for key, loss in losses.items()}
                    if any(value['status'] != 'complete' for value in scores.values()):
                        raise ValueError('complete native checkpoint lacks a cross-objective loss input')
                    if not math.isclose(scores[identity]['loss'], observation['loss'], rel_tol=1e-12, abs_tol=1e-12):
                        raise ValueError('saved optimization loss differs from independent checkpoint measurement')
                    row.update(status='complete', independent_metrics=proof['measurement']['metrics'],
                        cross_objective_losses={key: value['loss'] for key, value in scores.items()},
                        loss_evaluations=scores, physical_proof=proof)
                    physical_ids.add(evidence['run_id'])
                    candidate_by_run[evidence['run_id']] = candidate
                elif observation is not None and observation.get('loss') is not None:
                    raise ValueError('technical failure was converted into a numerical loss')
                rows.append(row)
                all_rows.append(row)
        eligible = [row for row in rows if row['status'] == 'complete']
        best_value = min((row['cross_objective_losses'][identity] for row in eligible), default=None)
        tied = [row for row in eligible
                if row['cross_objective_losses'][identity] == best_value] if best_value is not None else []
        fingerprints = [SystemSpec.from_dict(row['draw']['suggestion']['candidate']).fingerprint
                        for row in tied]
        arms[identity] = {'loss_spec': losses[identity], 'binding': binding,
            'records': records, 'pending': pending, 'authoring_proofs': authors, 'rows': rows,
            'loss_path': [row['cross_objective_losses'][identity] for row in rows],
            'selection': {'criterion': 'minimum observed bound development loss; earliest row is display representative',
                'best_loss': best_value, 'tie_count': len(tied),
                'tied_system_fingerprints': fingerprints,
                'representative_system_fingerprint': (fingerprints[0] if fingerprints else None)}}

    physical_directories = {p.name for p in (root / 'worlds').iterdir() if p.is_dir()} if (root / 'worlds').exists() else set()
    journal_directories = {path.parent.parent.name
        for path in (root / 'worlds').glob('*/replies/responses.sqlite')}
    caches = raw.get('physical_response_caches')
    cache_ids, reply_count = set(), 0
    if not isinstance(caches, list):
        raise ValueError('raw physical response cache inventory is absent')
    for row in caches:
        path = Path(row['path']).resolve()
        if (path.name != 'responses.sqlite' or path.parent.name != 'replies'
                or not path.is_relative_to((root / 'worlds').resolve()) or file_sha256(path) != row['sha256']):
            raise ValueError('raw physical response cache path/hash differs')
        cache_ids.add(path.parent.parent.name)
        with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as db:
            outcomes = dict(db.execute('SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
        if outcomes != row['outcomes']:
            raise ValueError('raw physical response outcome counts differ')
        reply_count += outcomes.get('response', 0)
    if (len(caches) != len(journal_directories) or cache_ids != journal_directories
            or raw.get('physical_reply_count') != reply_count):
        raise ValueError('raw physical cache count differs from immutable world inventory')
    if not physical_ids <= physical_directories:
        raise ValueError('completed physical world is absent from shared world directory')
    partial = []
    for run_id in sorted(physical_directories - physical_ids):
        candidate = candidate_by_run.get(run_id)
        if candidate is None:
            # Locate only a declared, saved suggestion ID. Undeclared cache is contamination.
            matches = [row['draw']['suggestion']['candidate'] for row in all_rows
                if row['draw'].get('suggestion') and run_id.startswith(row['draw']['suggestion']['suggestion_id'])]
            if len(matches) != 1:
                raise ValueError('shared world cache is undeclared or ambiguous')
            candidate = matches[0]
        cell, system = root / 'worlds' / run_id, SystemSpec.from_dict(candidate)
        if (cell / 'replies/responses.sqlite').exists():
            partial.append(partial_physical_proof(cell, system,
                arms[all_rows[0]['arm']]['binding']['world'], classification))
        else:
            if not (cell / 'system.json').exists() or read(cell / 'system.json') != system.to_dict():
                raise ValueError('partial world without response journal lacks its declared system')
            partial.append({'run_id': run_id, 'status': 'partial-before-response-journal', 'loss': None,
                'files': {str(path.relative_to(cell)): file_sha256(path)
                          for path in sorted(cell.rglob('*')) if path.is_file()},
                'scope': 'Declared physical world directory exists, but no response journal or completed objective observation exists.'})
    completed = len(physical_ids)
    if completed > 8:
        raise ValueError('physical world budget exceeds eight draws')
    committed_draws = sum(len(record['draws']) for arm in arms.values() for record in arm['records'])
    failures = sum(bool(record['generation_error']) for arm in arms.values() for record in arm['records'])
    failures += sum(row['status'] != 'complete' for row in all_rows)
    terminal = all(len(arms[key]['records']) == 2 and arms[key]['pending'] is None for key in ARM_IDS)
    expected_status = ('complete' if terminal and completed == 8 and not failures else
                       'budget-complete-with-failures' if terminal else 'in-progress')
    if (raw.get('planned_native_world_budget') != 8 or raw.get('committed_draws') != committed_draws
            or raw.get('complete_native_worlds') != completed or raw.get('technical_failures') != failures
            or raw.get('budget_terminal') is not terminal or raw.get('status') != expected_status
            or raw.get('configured_researcher_provider') != 'qwen3:8b'):
        raise ValueError('raw terminal draw/failure/status summary differs')
    claims = raw.get('claims', {})
    if (claims.get('held_out') is not False or claims.get('causal_institutional_benefit') is not False
            or claims.get('scientific_value') is not False
            or claims.get('designer_improvement_established') is not False
            or claims.get('full_native_world_pathwise_autograd') is not False):
        raise ValueError('raw evidence overclaims development engineering results')

    representatives = {identity: next((row for row in arms[identity]['rows']
        if row['draw'].get('suggestion') and SystemSpec.from_dict(row['draw']['suggestion']['candidate']).fingerprint ==
        arms[identity]['selection']['representative_system_fingerprint']), None) for identity in ARM_IDS}
    selected_matrix = {source: ({target: representatives[source]['cross_objective_losses'][target]
                                 for target in ARM_IDS} if representatives[source] else None)
                       for source in ARM_IDS}
    result = {'schema': SCHEMA, 'classification': classification,
        'status': expected_status,
        'source_commit': source_commit, 'raw_output_root': str(root),
        'raw_inventory_sha256': digest(inventory), 'raw_file_count': len(inventory),
        'raw_file_hashes': inventory, 'new_model_calls': 0, 'generated_source_executions': 0,
        'physical_cache_count': len(journal_directories),
        'physical_world_directory_count': len(physical_directories), 'completed_physical_worlds': completed,
        'partial_physical_worlds': partial, 'arms': arms, 'selected_cross_objective_matrix': selected_matrix,
        'held_out_metrics': {'status': 'not-defined-or-measured'},
        'promotion_policy': {'status': 'not-defined-or-applied'},
        'claims': ['Development engineering evidence only; no held-out, causal, scientific-value, or improvement claim.',
            'Loss paths are objective-conditioned observations, not optimizer convergence evidence.',
            'Graph changes are exact set/source diffs, not inferred institutional effects.',
            'Technical failures remain null and are excluded from numerical selection.']}
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
        parser.error('audit output must be outside immutable raw evidence')
    report = analyze(args.run, expected_source=args.expected_source,
                     require_complete=not args.allow_incomplete)
    write_json_atomic(args.output, report, sort_keys=True, ensure_ascii=False, allow_nan=False)
    print(json.dumps({'status': report['status'], 'physical_worlds': report['completed_physical_worlds'],
                      'report_sha256': report['content_sha256']}, sort_keys=True))


if __name__ == '__main__':
    main()
