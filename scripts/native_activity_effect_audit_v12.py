"""Read-only native research-plan/amendment evidence, not a simulator replay.

The original native activity capability is distinct from domain native.project
commands. Preserve its actual event/command/source IDs and annual actor states.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from utopia.optimization.native_code_trace import validate_record
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import digest
from utopia.system.native_activity_contracts import AMENDMENT, EFFECT, PLAN
from utopia.system.native_migration import native_execution_nodes
from utopia.utils.data_utils import file_sha256


def _annual_actor_state(actor):
    return {key: deepcopy(actor.get(key)) for key in ('id', 'project_start_year',
        'project_end_year', 'newest_direction', 'is_active')}


def _assignment_matches_state(assignment, actor):
    actual = actor.get('newest_direction')
    if not isinstance(actual, dict):
        return False
    direction = actual.get('direction')
    topic = direction.get('topic') if isinstance(direction, dict) else direction
    return (actor.get('project_start_year') == assignment['project_start_year']
        and actor.get('project_end_year') == assignment['project_end_year']
        and topic == assignment['direction']['topic']
        and actual.get('detailed_focus') == assignment['detailed_focus']
        and actual.get('reason') == assignment['reason'])


def _plan_candidates(system, effect, code_rows):
    """Recorded tee inputs from the actual declared upstream plan connection."""
    target = effect['provenance']['mechanism_id']
    sources = {(edge.source_mechanism, edge.source_port): edge for edge in system.connections
        if edge.target_mechanism == target and edge.target_port == 'plans'}
    candidates = []
    for index, row in enumerate(code_rows):
        for port, values in row['context']['inputs'].items():
            for value in values:
                payload = value.get('payload', {})
                edge = sources.get((value.get('source_mechanism'), value.get('source_port')))
                ids = value.get('lineage_event_ids', [])
                if (edge is None or payload.get('schema') != PLAN or payload.get('year') != effect['year']
                        or value.get('emitted_period') != effect['year']
                        or value.get('emitted_period') + edge.latency > effect['year']
                        or not ids or not set(ids) <= set(effect['provenance']['input_event_ids'])):
                    continue
                candidates.append({'code_record_index': index, 'code_input_port': port,
                    'bundle_sha256': row['bundle_sha256'], 'upstream_value': deepcopy(value),
                    'base_plan': deepcopy(payload)})
    return candidates


def _applied_plan_proof(system, effect, code_rows):
    matching = []
    for candidate in _plan_candidates(system, effect, code_rows):
        payload = deepcopy(candidate['base_plan'])
        if not isinstance(payload.get('assignments'), list) or not isinstance(payload.get('submit_actor_ids'), list):
            continue
        items = {item['actor_id']: item for item in payload['assignments']}
        if len(items) != len(payload['assignments']):
            continue
        valid = True
        for origin in effect['payload']['amendments']:
            command = origin['command']
            aid = command['assignment']['actor_id']
            if aid not in items:
                valid = False
                break
            items[aid].clear()
            items[aid].update(deepcopy(command['assignment']))
            if command['submit'] and aid not in payload['submit_actor_ids']:
                payload['submit_actor_ids'].append(aid)
            elif not command['submit'] and aid in payload['submit_actor_ids']:
                payload['submit_actor_ids'].remove(aid)
        if valid and sha(payload) == effect['payload']['plan_sha256']:
            if (payload['submit_actor_ids'] != effect['payload']['submit_actor_ids']
                    or [item['actor_id'] for item in payload['assignments']] != effect['actor_ids']):
                raise ValueError('activity applied-plan hash matches but submitter/actor receipt differs')
            matching.append({**candidate, 'applied_plan': payload})
    return {'status': 'verified-hash-consistent-recorded-upstream-plan' if matching else 'unavailable-recorded-upstream-plan',
        'plan_sha256': effect['payload']['plan_sha256'],
        'plan': matching[0]['applied_plan'] if matching else None,
        'matching_base_contexts': matching,
        'scope': 'Exact recorded upstream plan plus exact amendments reconstructs the committed plan hash where available; no generated source or native activity is rerun.'}


def annual_activity_proof(saved, system, code_rows):
    """Pure-data annual evidence helper. Caller validates physical checkpoints."""
    year = saved['year']
    events = {event['event_id']: event for event in saved['native_system']['events']}
    actors = {actor['id']: actor for actor in saved['ecosystem_data']['agents']}
    nodes = {node.mechanism_id: node for node in native_execution_nodes(system)}
    effects, total_matches = [], 0
    for event in saved['native_system']['events']:
        if event['event_type'] != EFFECT or event['year'] != year:
            continue
        payload = event['payload']
        if (payload['year'] != year or len(payload['submit_actor_ids']) != len(set(payload['submit_actor_ids']))
                or not set(payload['submit_actor_ids']) <= set(event['actor_ids'])
                or not set(event['actor_ids']) <= actors.keys()):
            raise ValueError('activity effect year/submitter/actual actor identities differ')
        amendments, touched = [], set()
        for origin in payload['amendments']:
            command = origin['command']
            assignment = command['assignment']
            aid = assignment['actor_id']
            if (command.get('schema') != AMENDMENT or command.get('target_year') != year
                    or origin['command_sha256'] != sha(command) or type(command.get('submit')) is not bool
                    or aid not in event['actor_ids'] or aid in touched
                    or (aid in payload['submit_actor_ids']) != command['submit']):
                raise ValueError('activity amendment exact command/hash/submitter identities differ')
            touched.add(aid)
            ids = origin['input_event_ids']
            if (not ids or not set(ids) <= set(event['provenance']['input_event_ids'])
                    or any(identity not in events or events[identity]['sequence'] >= event['sequence'] for identity in ids)):
                raise ValueError('activity amendment lineage is missing, future or outside effect inputs')
            edges = [edge for edge in system.connections if edge.source_mechanism == origin['source_mechanism']
                and edge.source_port == origin['source_port'] and edge.target_port == 'amendments'
                and edge.target_mechanism == event['provenance']['mechanism_id']
                and origin['emitted_period'] + edge.latency <= year]
            if not edges:
                raise ValueError('activity amendment lacks its actual explicit available input wire')
            source = nodes.get(origin['source_mechanism'])
            if source is None:
                raise ValueError('activity amendment source was not declared in the executed system')
            code_outputs = []
            if source.implementation == 'code.python.v1':
                for index, row in enumerate(code_rows):
                    if (row['artifact'] != source.parameters['code_artifact']
                            or row['context']['period'] != origin['emitted_period']
                            or not any(value['payload'] == command for value in
                                row['result']['outputs'].get(origin['source_port'], []))):
                        continue
                    matching_events = [identity for identity in ids
                        if events[identity]['event_type'] == 'generated.code_executed'
                        and events[identity]['provenance']['mechanism_id'] == origin['source_mechanism']
                        and events[identity]['year'] == origin['emitted_period']
                        and all(events[identity]['payload'][key] == row['receipt'][key]
                            for key in ('artifact_sha256', 'context_sha256', 'result_sha256', 'image_id'))]
                    if matching_events:
                        code_outputs.append({'code_record_index': index, 'bundle_sha256': row['bundle_sha256'],
                            'source_value_sha256': sha(row['artifact']['source']),
                            'receipt': deepcopy(row['receipt']), 'generated_event_ids': matching_events,
                            'generated_event_sha256s': {identity:digest(events[identity]) for identity in matching_events}})
                if not code_outputs:
                    raise ValueError('activity amendment not emitted by its actual recorded generated source')
            total_matches += len(code_outputs)
            later = [other['event_id'] for other in events.values() if other['year'] == year
                and other['sequence'] > event['sequence'] and (
                    other['event_type'] == EFFECT and aid in other['actor_ids']
                    or other['event_type'] == 'native.domain.project_applied'
                        and other['payload'].get('assignment', {}).get('actor_id') == aid
                    or other['event_type'] == 'native.system.phase_executed' and other['payload'].get('stage') == 'research')]
            amendments.append({'command': deepcopy(command), 'command_sha256': sha(command),
                'origin': deepcopy(origin), 'input_event_sha256s': {identity:digest(events[identity]) for identity in ids},
                'declared_available_wires': [{
                    'source_mechanism': edge.source_mechanism, 'source_port': edge.source_port,
                    'target_mechanism': edge.target_mechanism, 'target_port': edge.target_port,
                    'channel': edge.channel.value, 'latency': edge.latency} for edge in edges],
                'source_implementation': source.implementation, 'code_output_proofs': code_outputs,
                'code_output_attribution': 'not-a-python-source' if source.implementation != 'code.python.v1'
                    else 'unique-recorded-output-match' if len(code_outputs) == 1 else 'multiple-recorded-output-matches-retained',
                'annual_actor_state': _annual_actor_state(actors[aid]),
                'annual_actor_state_matches_assignment': _assignment_matches_state(assignment, actors[aid]),
                'later_same_year_activity_or_project_effect_ids': later})
        effects.append({'event_id': event['event_id'], 'event_sha256': digest(event), 'event': deepcopy(event),
            'submit_actor_ids': deepcopy(payload['submit_actor_ids']), 'amendments': amendments,
            'applied_plan_proof': _applied_plan_proof(system, event, code_rows)})
    return {'year': year, 'effects': effects, 'generated_amendment_output_matches': total_matches}


def activity_effect_proof(cell, system, checkpoint):
    cell, checkpoint = Path(cell), Path(checkpoint)
    final = read_portable_checkpoint(checkpoint)
    path = cell / 'code-contexts.jsonl'
    code_rows = [validate_record(json.loads(line)) for line in path.read_text().splitlines()] if path.exists() else []
    annual = []
    for year in range(1, final['year'] + 1):
        annual_path = checkpoint.parent / f'portable_checkpoint_year_{year}.json.gz'
        saved = read_portable_checkpoint(annual_path)
        if saved['year'] != year or saved['native_system']['spec'] != system.to_dict():
            raise ValueError('annual activity checkpoint/source/period differs')
        annual.append({**annual_activity_proof(saved, system, code_rows),
            'checkpoint_sha256': file_sha256(annual_path)})
    return {'effect_event_count': sum(len(item['effects']) for item in annual),
        'amendment_count': sum(len(effect['amendments']) for item in annual for effect in item['effects']),
        'generated_amendment_output_matches': sum(item['generated_amendment_output_matches'] for item in annual),
        'annual': annual, 'scope': 'Committed native activity-plan receipts and recorded generated amendment outputs, separate from domain native.project commands. Annual state is a later snapshot and may contain legal subsequent mutations; no causal or beneficial effect is inferred.'}
