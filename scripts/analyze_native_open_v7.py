#!/usr/bin/env python3
"""Read-only v7 external vocabulary -> mixed draws -> original-native evidence audit.

No factories, models, generated source or containers are executed. Tensor replay
is conditional numerical analysis, not a derivative of the full native LossSpec.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_native_society_v6 import response_proofs, ACTUAL as RESPONSE_ACTUAL
from scripts.audit_native_objective_v5 import checkpoint_measurements
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign, InboxVocabularyGenerator
from utopia.optimization.native_code_trace import validate_record
from utopia.optimization.native_hybrid import boundary_coverage, conditional_backward
from utopia.optimization.native_transition_data import physical_initial_identity
from utopia.optimization.native_manifest_inbox import ManifestInbox, audit_manifest_inbox
from utopia.optimization.native_relaxation import native_tensor_trace
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import digest
from utopia.system.native_kernel import NativeScienceKernel
from utopia.system.native_migration import native_execution_nodes
from utopia.system.native_open_examples import joint_engineering_loss
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-open-integrated-pilot.v7'
ACTUAL = 'actual-native-qwen-open-design-engineering-pilot'
FIXTURE = 'scripted-fixture-not-native-results'


def _inventory(root):
    result = {}
    for path in sorted(Path(root).rglob('*')):
        if path.is_symlink():
            raise ValueError('raw evidence cannot contain symlinks')
        if path.is_file():
            result[str(path.relative_to(root))] = file_sha256(path)
    return result


def read(path):
    value = json.loads(Path(path).read_text())
    digest(value)
    return value


class ReadOnlyCampaign(NativeAdaptiveDesignCampaign):
    def _save(self):
        raise AssertionError('audit must never persist a campaign')


class RequestCapture:
    def generate(self, **kwargs):
        self.request = json.loads(json.dumps({'schema': 'scienceutopia.external-manifest-request.v5',
            'request': kwargs}, ensure_ascii=False, allow_nan=False))
        return {}, []


def authoring_proofs(directory, records):
    """Exact request reconstruction, including history, weights, loss and source."""
    directory = Path(directory)
    inbox = ManifestInbox(directory)  # Constructor only verifies existing files.
    sets = {s: {p.stem for p in (directory / s).glob('*.json')}
            for s in ('requests', 'responses', 'consumed')}
    if not sets['consumed'] <= sets['responses'] <= sets['requests']:
        raise ValueError('orphaned external response/consumption')
    if len(sets['requests']) != len(records):
        raise ValueError('external requests lack one-to-one campaign request provenance')
    proofs, used = [], set()
    for record in records:
        matches = [(identity, inbox._verify_request(identity)) for identity in sets['requests']
            if inbox._verify_request(identity)['request'].get('authoring_input') == record['request']]
        if len(matches) != 1:
            raise ValueError('exact campaign authoring request absent or ambiguous')
        identity, request = matches[0]
        if identity in used:
            raise ValueError('one external request reused by distinct generations')
        used.add(identity)
        prompt = request['request'].get('prompt', '')
        if '\n' not in prompt:
            raise ValueError('external vocabulary instructions missing')
        capture = RequestCapture()
        InboxVocabularyGenerator(capture, instructions=prompt.split('\n', 1)[1])(deepcopy(record['request']))
        if capture.request != request:
            raise ValueError('external exact prompt/schema/seed/settings/history reconstruction differs')
        generated = record['generated']
        if generated != (identity in sets['consumed']):
            raise ValueError('generated vocabulary lacks exact external consumed response')
        if generated and inbox._response(identity)['manifest'] != record['definition']:
            raise ValueError('external manifest is not the immutable generated vocabulary')
        proofs.append({'generation': record['request']['generation'], 'request_sha256': identity,
            'request_file_sha256': file_sha256(directory / 'requests' / (identity + '.json')),
            'campaign_request_sha256': record['request_sha256'], 'version_sha256': record['version_sha256'],
            'status': 'consumed' if generated else 'awaiting-external-consumption',
            'receipt': inbox._read(directory / 'consumed' / (identity + '.json')) if generated else None,
            'self_reported_authoring': inbox._response(identity)['authoring'] if identity in sets['responses'] else None})
    return proofs


def code_proofs(cell, system, native, world, run_id, *, complete):
    """Bind every recorded sandbox call to its exact active (possibly wrapped) source.

    Many-to-one matches are retained as ambiguous physical attempts, never
    arbitrarily deduplicated into independent effects.
    """
    path = Path(cell) / 'code-contexts.jsonl'
    rows = [validate_record(json.loads(line)) for line in path.read_text().splitlines()] if path.exists() else []
    nodes = {n.mechanism_id: n for n in native_execution_nodes(system) if n.implementation == 'code.python.v1'}
    events = {e['event_id']: e for e in native['events'] if e['event_type'] == 'generated.code_executed'}
    matches = {identity: [] for identity in events}
    physical = []
    for index, row in enumerate(rows):
        if row['binding'] != {'source_commit': world['source_commit'], 'system_fingerprint': system.fingerprint, 'run_id': run_id}:
            raise ValueError('code context source/design/run binding differs')
        active = [n for n in nodes.values() if n.parameters['code_artifact'] == row['artifact']
            and n.parameters['runtime_image_id'] == row['receipt']['image_id']
            and {k: v for k, v in n.parameters.items() if k not in {'code_artifact', 'runtime_image_id'}} == row['context']['parameters']]
        if not active:
            raise ValueError('recorded source/image/parameters were not active in the executed design')
        ids = [identity for identity, event in events.items()
            if event['provenance']['mechanism_id'] in {n.mechanism_id for n in active}
            and event['year'] == row['context']['period'] and all(event['payload'][key] == row['receipt'][key]
                for key in ('image_id', 'artifact_sha256', 'context_sha256', 'result_sha256'))]
        for identity in ids:
            matches[identity].append(index)
        physical.append({'index': index, 'bundle_sha256': row['bundle_sha256'],
            'year': row['context']['period'], 'matching_event_ids': ids})
    if any(not indices for indices in matches.values()):
        raise ValueError('native generated-code event lacks its actual source/context/result receipt')
    ambiguous = [identity for identity, indices in matches.items()
        if len(indices) != 1 or any(len(physical[i]['matching_event_ids']) != 1 for i in indices)]
    extras = [p for p in physical if not p['matching_event_ids']]
    for p in physical:
        p['attribution'] = ('uncommitted-attempt-candidate' if not p['matching_event_ids'] else
            'ambiguous-physical-attempt' if any(identity in ambiguous for identity in p['matching_event_ids']) else 'unique-event-match')
    state_chains = []
    if not ambiguous and not extras and native.get('graph_checkpoint') is not None:
        outer = {n.mechanism_id: n for n in system.mechanisms}
        previous, execution_counts = {}, Counter()
        for identity, event in events.items():
            node_id = event['provenance']['mechanism_id']
            node = outer[node_id]
            if node_id not in previous:
                initial = system.initial_state.get('mechanism_states', {}).get(node_id, {})
                previous[node_id] = (initial.get('delegate_state', node.parameters['initial_delegate_state'])
                    if node.implementation == 'native.process.activity.v1' else initial)
            row = rows[matches[identity][0]]
            if row['context']['state'] != previous[node_id]:
                raise ValueError('actual code input memory does not continue the preceding committed execution')
            previous[node_id] = row['result']['state']
            execution_counts[node_id] += 1
        for node_id, final in previous.items():
            node = outer[node_id]
            stored = native['graph_checkpoint']['mechanism_states'][node_id]
            if node.implementation == 'native.process.activity.v1':
                if stored['total_invocations'] != execution_counts[node_id]:
                    raise ValueError('wrapped process invocation memory differs from actual committed code calls')
                stored = stored['delegate_state']
            if stored != final:
                raise ValueError('last actual generated-code memory is not the durable kernel memory')
            state_chains.append({'mechanism': node_id, 'committed_calls': execution_counts[node_id],
                'final_state_sha256': digest(final)})
    return {'recorded_executions': len(rows), 'committed_events': len(events),
        'one_to_one_physical_execution_proven': not ambiguous and not extras,
        'ambiguous_native_event_count': len(ambiguous), 'uncommitted_attempt_candidates': len(extras),
        'physical_records': physical, 'code_contexts_sha256': file_sha256(path) if path.exists() else None,
        'committed_memory_chains': state_chains,
        'sources': [{'mechanism': n.mechanism_id, 'source_sha256': sha(n.parameters['code_artifact']['source']),
            'artifact_sha256': sha(n.parameters['code_artifact']), 'runtime_image_id': n.parameters['runtime_image_id']}
            for n in nodes.values()], 'complete_native_world': complete}


def domain_proofs(saved, kernel, code_rows=None):
    """Check command receipts against actual actor state and lineage without execution."""
    native, agents = saved['native_system'], {a['id']: a for a in saved['ecosystem_data']['agents']}
    domain = native.get('open_domain', {})
    receipts = sorted(domain.get('receipts', {}).values(), key=lambda r: r['index'])
    context_proofs, projects = [], []
    native_ids = set(agents)
    artifacts = domain.get('artifacts', {})
    paper_ids = {p['id'] for p in saved['paper_tracker']['papers']}
    declared = {identity for state in kernel.graph_checkpoint['mechanism_states'].values()
        for identity in state.get('declared_artifacts', {})}
    all_actor_ids = native_ids | set(domain.get('actors', {}))
    for artifact in artifacts.values():
        if (artifact['owner_actor'] not in all_actor_ids or not set(artifact['actor_ids']) <= all_actor_ids
                or not set(artifact['artifact_ids']) <= set(artifacts) | paper_ids | declared
                or not set(artifact['native_paper_ids']) <= paper_ids):
            raise ValueError('open artifact contains dangling native/domain lineage')
    for receipt in receipts:
        command = receipt['command']
        if code_rows is not None:
            origin = receipt['origin']
            outputs = [r for r in code_rows if r['context']['period'] == origin['emitted_period']
                and any(value['payload'] == command for value in r['result']['outputs'].get(origin['source_port'], []))]
            source = next((n for n in native_execution_nodes(kernel.spec) if n.mechanism_id == origin['source_mechanism']), None)
            if (source is not None and source.implementation == 'code.python.v1'
                    and not any(r['artifact'] == source.parameters['code_artifact'] for r in outputs)):
                raise ValueError('committed domain command not produced by the actual active generated source')
        if command['action'] == 'native.context':
            payload = command['payload']
            for actor in payload['actor_ids']:
                exact = [m for m in agents[actor].get('institutional_context', [])
                    if m.get('message_id') == 'native-domain-' + receipt['command_key']]
                if len(exact) != 1 or exact[0]['payload'] != payload['content'] or exact[0]['input_event_ids'] != receipt['input_event_ids']:
                    raise ValueError('domain context command did not persist in the actual researcher state')
                context_proofs.append({'command_key': receipt['command_key'], 'actor_id': actor,
                    'received_year': receipt['received_year'], 'message_sha256': digest(exact[0])})
        elif command['action'] == 'native.project':
            assignment = command['payload']['assignment']
            effects = [e for e in native['events'] if e['event_type'] == 'native.domain.project_applied'
                and e['year'] == receipt['received_year'] and e['payload'].get('command_key') == receipt['command_key']]
            # The receipt is an executed assignment, not a claim that a later
            # research phase cannot deliberately replace that assignment.
            if (len(effects) != 1 or assignment['actor_id'] not in native_ids
                    or effects[0]['payload']['assignment'] != assignment):
                raise ValueError('domain project lacks its actual native effect event')
            projects.append({'command_key': receipt['command_key'], 'actor_id': assignment['actor_id'],
                'year': receipt['received_year'], 'assignment_sha256': digest(assignment), 'event_id': effects[0]['event_id']})
    processes = [e for e in native['events'] if e['event_type'] in {'native.process.completed', 'native.process.skipped'}]
    for event in processes:
        node = next(n for n in kernel.spec.mechanisms if n.mechanism_id == event['provenance']['mechanism_id'])
        if (event['payload']['delegate_contract_sha256'] != sha(node.parameters['delegate'])
                or not 0 <= event['payload']['executed'] <= event['payload']['requested'] <= event['payload']['limit']):
            raise ValueError('process completion does not bind its actual declared delegate/budget')
        iterations = [e for e in native['events'] if e['event_type'] == 'native.process.iteration'
            and e['year'] == event['year'] and e['provenance']['mechanism_id'] == node.mechanism_id]
        if len(iterations) != event['payload']['executed']:
            raise ValueError('process invocation count differs from committed iteration events')
    return {'custom_actors': len(domain.get('actors', {})), 'custom_artifacts': len(artifacts),
        'domain_commands': len(receipts), 'actions': dict(Counter(r['command']['action'] for r in receipts)),
        'context_messages_verified': len(context_proofs), 'context_state_proofs': context_proofs,
        'project_assignments_verified': projects, 'process_completions': len(processes),
        'process_invocations': sum(e['payload']['executed'] for e in processes),
        'process_receipt_sha256s': [digest(e) for e in processes],
        'migration_receipts': len(kernel.design_history),
        'domain_state_sha256': digest(domain), 'kernel_restored_without_execution': True}


def context_input_proofs(cell, saved):
    """Separate delivered/stored messages from messages actually seen in HTTP inputs."""
    with sqlite3.connect((cell / 'replies/responses.sqlite').resolve().as_uri()+'?mode=ro', uri=True) as db:
        completed = {r[0] for r in db.execute("SELECT payload_sha FROM replies WHERE outcome='response'")}
    wires = [json.loads(line) for line in (cell / 'wire-requests.jsonl').read_text().splitlines()]
    agents = {a['id']: a for a in saved['ecosystem_data']['agents']}
    rows = []
    for event in saved['native_system']['events']:
        if event['event_type'] != 'native.system.context_delivered':
            continue
        message = event['payload']['message']
        rendered = json.dumps(message, ensure_ascii=False, sort_keys=True, allow_nan=False)
        for actor in event['actor_ids']:
            stored = [m for m in agents[actor].get('institutional_context', []) if m['message_id'] == message['message_id']]
            if stored != [message]:
                raise ValueError('delivered native message is not retained exactly in its actual recipient state')
            matching = [w['payload_sha256'] for w in wires if w['year'] >= message['received_year']
                and w['payload_sha256'] in completed and any(isinstance(m.get('content'), str)
                    and rendered in m['content'] for m in w['payload'].get('messages', []))]
            rows.append({'event_id': event['event_id'], 'actor_id': actor, 'message_sha256': digest(message),
                'received_year': message['received_year'], 'completed_http_payload_sha256s': matching,
                'observed_in_completed_model_input': bool(matching)})
    return {'delivered_recipient_messages': len(rows),
        'messages_observed_in_completed_model_inputs': sum(r['observed_in_completed_model_input'] for r in rows),
        'proofs': rows, 'scope': 'Exact persisted delivered message occurs in actual completed HTTP input; not evidence of beneficial interpretation or scientific utility.'}


def derivative_diagnostics(system, events):
    """Recompute diagnostic failures without erasing an independently measured cost.

    Connected historical reports retain their exact old JSON. This does not
    convert an unavailable opaque/native derivative into a zero gradient.
    """
    def failed(error):
        return {'status': 'failed-diagnostic', 'error_type': type(error).__name__, 'error': str(error),
            'native_loss_gradient_verified': False, 'full_native_world_autograd': False}
    try:
        coverage = boundary_coverage(system, events)
    except Exception as error:
        coverage = failed(error)
    try:
        programs = {n.mechanism_id: n.parameters['program'] for n in system.mechanisms if n.implementation == 'program.tensor.v1'}
        backward = conditional_backward(native_tensor_trace(events), programs,
            trainable={'addressed-selection': ['bias']},
            terms=[{'mechanism': 'open-memory-router', 'output': 'actions', 'coefficient': -1.}])
    except Exception as error:
        backward = failed(error)
    return coverage, backward


def audit_native_run(root, draw, observation, evidence, world, classification, *,
        expected_experiment=None, expected_loss=None):
    """Audit one immutable native draw without executing it.

    The optional bindings let later protocols reuse the physical-evidence audit.
    Defaults deliberately preserve the exact v7 receipt and loss contract.
    """
    expected_experiment = (expected_experiment if expected_experiment is not None else
        {'protocol': 'native-open-integrated-v7', 'role': 'development-engineering'})
    loss_spec = expected_loss if expected_loss is not None else joint_engineering_loss()
    system = SystemSpec.from_dict(draw['suggestion']['candidate'])
    checkpoint = Path(evidence['checkpoint_path']).resolve()
    cell = Path(root) / 'worlds' / evidence['run_id']
    if not checkpoint.is_relative_to(cell.resolve()) or file_sha256(checkpoint) != evidence['checkpoint_sha256']:
        raise ValueError('native checkpoint escapes physical run or file hash changed')
    saved = read_portable_checkpoint(checkpoint)
    binding = saved['portable']['contract']['binding']
    if (saved['portable']['contract']['native_system']['system_fingerprint'] != system.fingerprint
            or binding['cell'] != system.fingerprint or binding['seed'] != 42
            or binding['science_config']['source_commit'] != world['source_commit']
            or binding['model_revision'] != world['model_digest'] or binding['corpus_sha256'] != world['corpus_sha256']
            or saved['portable']['contract']['model'] != binding['model']
            or saved['portable']['contract']['model_revision'] != binding['model_revision']
            or binding['science_config']['years'] != saved['year']
            or (classification != FIXTURE and saved['year'] != 2)):
        raise ValueError('actual source/model/corpus/seed/design/native horizon differs')
    if classification != FIXTURE and (binding['model'] != 'qwen3:8b'
            or binding['science_config']['experiment'] != expected_experiment
            or binding['science_config']['population'] != {'institutions': 5, 'per_institution': 1, 'strategy': 'balanced'}
            or binding['science_config']['corpus_years'] != 4
            or binding['science_config']['thinking_override'] is not False
            or binding['science_config']['max_tokens'] != 768
            or saved['rag']['ordered_documents_sha256'] != world['corpus_sha256']):
        raise ValueError('actual fixed-Qwen / original five-researcher corpus protocol differs')
    if read(cell / 'system.json') != system.to_dict():
        raise ValueError('physical source SystemSpec is not the evaluated generated candidate')
    kernel = NativeScienceKernel(system, checkpoint=saved['native_system'])
    if kernel.design_history:
        raise ValueError('fresh-world draw unexpectedly contains same-society migrations')
    measurement = checkpoint_measurements(checkpoint, evidence['run_id'], system.fingerprint)
    if evidence['event_stream_hash'] != kernel.to_dict()['event_stream_hash']:
        raise ValueError('observation event stream differs from restored actual native kernel')
    years = saved['year']
    counts, annual, previous_events, previous_elapsed = [], [], [], 0.
    for year in range(1, years + 1):
        annual_path = checkpoint.parent / f'portable_checkpoint_year_{year}.json.gz'
        state = read_portable_checkpoint(annual_path)
        if (state['year'] != year or state['phase'] != 5 or state['portable']['contract']['binding'] != binding
                or state['native_system']['spec'] != system.to_dict()):
            raise ValueError('annual checkpoint source/physical lineage differs')
        annual_kernel = NativeScienceKernel(system, checkpoint=state['native_system'])
        events = state['native_system']['events']
        if (events[:len(previous_events)] != previous_events or saved['native_system']['events'][:len(events)] != events):
            raise ValueError('native event lineage was reset or changed across annual checkpoints')
        elapsed = state['portable']['llm_call_stats'].get('elapsed_seconds', 0.)
        if elapsed < previous_elapsed:
            raise ValueError('annual native LLM elapsed counter rewound')
        annual.append({'year': year, 'checkpoint_sha256': file_sha256(annual_path),
            'accepted_decisions': sum(d.get('decision') == 'accept' for p in state['paper_tracker']['papers'] for d in p['review_history']),
            'context_deliveries': sum(e.event_type == 'native.system.context_delivered' for e in annual_kernel.events),
            'cumulative_responses': state['portable']['response_cache_count'],
            'llm_call_stats': state['portable']['llm_call_stats'], 'interval_llm_elapsed_seconds': elapsed-previous_elapsed,
            'native_event_stream_hash': state['native_system']['event_stream_hash']})
        previous_events, previous_elapsed = events, elapsed
        counts.append(state['portable']['response_cache_count'])
    response = response_proofs(cell, binding, counts, complete=True, protocol={},
        classification=RESPONSE_ACTUAL if classification != FIXTURE else FIXTURE)
    if any(int(y) > years for y in response['responses_by_physical_year']):
        raise ValueError('physical HTTP year exceeds actual native horizon')
    code = code_proofs(cell, system, saved['native_system'], world, evidence['run_id'], complete=True)
    code_rows = [validate_record(json.loads(line)) for line in (cell / 'code-contexts.jsonl').read_text().splitlines()]
    initial = read_portable_checkpoint(checkpoint.parent / 'portable_checkpoint_year_0.json.gz')
    if (initial['year'] != 0 or initial['phase'] != 0 or initial['portable']['response_cache_count'] != 0
            or initial['native_system']['events'] or initial['native_system']['last_year'] != 0
            or initial['native_system']['spec'] != system.to_dict()
            or initial['portable']['contract']['binding'] != binding):
        raise ValueError('native draw lacks its original initialized candidate world')
    initial_authors = [a for a in initial['ecosystem_data']['agents'] if a['can_author']]
    NativeScienceKernel(system, checkpoint=initial['native_system'])
    if classification != FIXTURE and len(initial_authors) != 5:
        raise ValueError('actual original initialized population is not five researchers')
    coverage, backward = derivative_diagnostics(system, kernel.events)
    conditional_scope = ('Minus represented router actions, conditioned on recorded numeric inputs; '
        'NOT joint LossSpec -A-0.1C or full native/LLM pathwise derivative.' if loss_spec == joint_engineering_loss()
        else 'Minus represented router actions, conditioned on recorded numeric inputs; '
            'NOT the bound native LossSpec or full native/LLM pathwise derivative.')
    return {'measurement': measurement, 'native_loss': evaluate_loss(loss_spec, [measurement])['loss'],
        'physical_initial_identity': physical_initial_identity(initial),
        'response_proof': response, 'code_proof': code, 'native_counts': domain_proofs(saved, kernel, code_rows),
        'context_input_proof': context_input_proofs(cell, saved),
        'annual_checkpoints': annual,
        'boundary_coverage': coverage, 'conditional_backward': backward,
        'checkpoint_sha256': file_sha256(checkpoint), 'actual_author_count': len([a for a in saved['ecosystem_data']['agents'] if a['can_author']]),
        'initial_roster': {'author_count': len(initial_authors), 'total_actor_count': len(initial['ecosystem_data']['agents']),
            'actor_ids_sha256': digest(sorted(a['id'] for a in initial['ecosystem_data']['agents'])),
            'actual_conference_count': len(initial['conference_system']['conferences']),
            'configured_num_conferences': 1 if classification != FIXTURE else None,
            'note': 'Configured count and actual per-category conference instances are separate facts.'},
        'conditional_backward_scope': conditional_scope}


def partial_physical_proof(cell, system, world, classification):
    """Account for actual partial inference without inventing a completed world."""
    with sqlite3.connect((cell / 'replies/responses.sqlite').resolve().as_uri()+'?mode=ro', uri=True) as db:
        bindings = db.execute('SELECT binding FROM metadata').fetchall()
    if len(bindings) != 1:
        raise ValueError('partial native response journal has no unique binding')
    binding = json.loads(bindings[0][0])
    if (binding['cell'] != system.fingerprint or binding['seed'] != 42
            or binding['science_config']['source_commit'] != world['source_commit']
            or binding['model_revision'] != world['model_digest'] or binding['corpus_sha256'] != world['corpus_sha256']
            or read(cell / 'system.json') != system.to_dict()):
        raise ValueError('partial inference source/model/corpus/design/seed differs')
    checkpoints = sorted(cell.rglob('portable_checkpoint_year_*.json.gz'),
        key=lambda p: int(p.name.split('_year_')[1].split('.')[0]))
    counts, last = [], None
    for path in checkpoints:
        saved = read_portable_checkpoint(path)
        if saved['portable']['contract']['binding'] != binding or saved['native_system']['spec'] != system.to_dict():
            raise ValueError('partial committed checkpoint differs from its inference journal')
        NativeScienceKernel(system, checkpoint=saved['native_system'])
        if saved['year'] > 0:
            if saved['phase'] != 5 or saved['year'] != len(counts)+1:
                raise ValueError('partial committed native year prefix is not contiguous')
            counts.append(saved['portable']['response_cache_count'])
        last = saved
    response = response_proofs(cell, binding, counts, complete=False, protocol={},
        classification=RESPONSE_ACTUAL if classification != FIXTURE else FIXTURE)
    horizon = binding['science_config']['years']
    if classification != FIXTURE and (binding['model'] != 'qwen3:8b' or horizon != 2):
        raise ValueError('partial actual native protocol/model/horizon differs')
    if any(int(y) > horizon for y in response['responses_by_physical_year']):
        raise ValueError('partial physical HTTP chronology exceeds native horizon')
    return {'run_id': cell.name, 'status': 'partial-or-unobserved-physical-run', 'loss': None,
        'through_committed_year': last['year'] if last else None, 'response_proof': response,
        'code_proof': code_proofs(cell, system, last['native_system'] if last else {'events': []},
            world, cell.name, complete=False),
        'scope': 'A partial or not-yet-observed physical run is not a completed native objective observation.'}


def analyze(run, *, expected_source, require_complete=True):
    root = Path(run).resolve()
    before = _inventory(root)
    try:
        return _analyze(root, expected_source=expected_source, require_complete=require_complete, inventory=before)
    finally:
        if _inventory(root) != before:
            raise ValueError('raw evidence changed during read-only audit; no stable result')


def _analyze(root, *, expected_source, require_complete, inventory):
    raw = read(root / 'evidence.json')
    if raw.get('schema') != SCHEMA or digest({k: v for k, v in raw.items() if k != 'content_sha256'}) != raw['content_sha256']:
        raise ValueError('raw evidence schema/content hash differs')
    state = read(root / 'campaign/native-adaptive-state.json')
    b = state['binding']
    if (b['world']['source_commit'] != expected_source or raw['source_commit'] != expected_source
            or b['loss_spec'] != joint_engineering_loss() or b['seeds'] != [42]
            or b['mode'] != 'hybrid' or b['seed'] != 42 or raw['campaign_binding'] != b
            or raw['world_binding'] != b['world']):
        raise ValueError('explicit source / actual loss / fixed seed / campaign binding differs')
    classification = b['world'].get('classification', ACTUAL)
    if classification not in {ACTUAL, FIXTURE}:
        raise ValueError('unknown evidence classification')
    if classification == ACTUAL and (len(expected_source) != 40 or raw['configured_researcher_provider'] != 'qwen3:8b'):
        raise ValueError('actual pilot needs explicit clean commit and Qwen provider')
    controller = ReadOnlyCampaign(root / 'campaign', initial_system=SystemSpec.from_dict(b['initial_system']),
        loss_spec=b['loss_spec'], seeds=b['seeds'], world_binding=b['world'], strategies=b['strategies'],
        **{k: b[k] for k in ('mode', 'seed', 'learning_rate', 'strategy_learning_rate', 'strategy_baseline', 'exploration')})
    records = controller.state['records']
    if raw['records'] != records or len(records) > 2 or any(r['request']['count'] != 2 for r in records):
        raise ValueError('reported history or declared two-round/two-draw budget differs')
    all_records = records + ([controller.state['pending']] if controller.state['pending'] else [])
    if len(all_records) > 2:
        raise ValueError('pending generation exceeds declared budget')
    authoring = authoring_proofs(root / 'authoring', all_records)
    if raw['authoring'] != audit_manifest_inbox(root / 'authoring'):
        raise ValueError('raw authoring summary differs from existing inbox')
    rows, physical, proof_rows, expected_rows = [], set(), [], []
    for record in records:
        for draw, obs in zip(record['draws'], record['observations']):
            base = {'generation': record['request']['generation'], 'version_sha256': record['version_sha256'],
                'strategy': record['request']['strategy_id'], 'draw': draw, 'observation': obs}
            matching = raw['observations'][len(expected_rows)] if len(raw['observations']) > len(expected_rows) else None
            if matching is None or any(matching.get(k) != v for k, v in base.items()):
                raise ValueError('raw observation rows omit or change an actual draw')
            row = deepcopy(matching)
            measurements = []
            if obs and obs['status'] == 'complete':
                if len(obs['metadata']['runs']) != 1 or obs['metadata']['technical_failures']:
                    raise ValueError('completed native draw does not contain exactly one physical development run')
                for evidence in obs['metadata']['runs']:
                    if evidence['run_id'] in physical:
                        raise ValueError('physical native run reused as an independent draw')
                    physical.add(evidence['run_id'])
                    proof = audit_native_run(root, draw, obs, evidence, b['world'], classification)
                    measurements.append(proof['measurement'])
                    if (matching['checkpoint_sha256'] != proof['checkpoint_sha256']
                            or matching['boundary_coverage'] != proof['boundary_coverage']
                            or matching['conditional_backward'] != proof['conditional_backward']):
                        raise ValueError('raw conditional numerical replay or checkpoint hash differs')
                    checkpoint = read_portable_checkpoint(evidence['checkpoint_path'])
                    if (matching['events'] != checkpoint['native_system']['events']
                            or matching['open_domain'] != checkpoint['native_system'].get('open_domain', {})
                            or matching['system'] != draw['suggestion']['candidate']
                            or matching['year'] != checkpoint['year']
                            or matching['checkpoint_path'] != str(Path(evidence['checkpoint_path']))
                            or matching['process_receipts'] != [e for e in checkpoint['native_system']['events']
                                if e['event_type'].startswith('native.process.')]):
                        raise ValueError('raw visual domain/event/system summary differs from actual checkpoint')
                    row.update(independent_metrics=proof['measurement']['metrics'], native_counts=proof['native_counts'])
                    proof_rows.append(proof)
            if obs is not None:
                derived = evaluate_loss(b['loss_spec'], measurements)
                if (measurements != obs['metadata']['measurements'] or derived != obs['metadata']['loss_evaluation']
                        or derived['loss'] != obs['loss']):
                    raise ValueError('independent actual checkpoint measurements/loss differ from saved observation')
            elif draw['suggestion'] is not None:
                raise ValueError('valid native draw lacks any terminal observation')
            if (not obs or obs['status'] != 'complete') and any(k in matching for k in ('native_counts', 'events', 'conditional_backward')):
                raise ValueError('failed/null draw falsely includes completed-world evidence')
            expected_rows.append(base)
            rows.append(row)
    if len(rows) != len(raw['observations']):
        raise ValueError('extra reported native observation')
    complete = len(records) == 2 and controller.state['pending'] is None and len(physical) == 4
    terminal = len(records) == 2 and controller.state['pending'] is None
    status = 'complete' if complete else 'budget-complete-with-failures' if terminal else 'in-progress'
    if raw['status'] != status or raw['complete_native_worlds'] != len(physical):
        raise ValueError('budget/complete native world reporting differs')
    if require_complete and not complete:
        raise ValueError('four complete native worlds required; use --allow-incomplete for truthful partial audit')
    caches, partial_proofs = [], []
    declared = {d['suggestion']['suggestion_id']+'-s42': SystemSpec.from_dict(d['suggestion']['candidate'])
        for record in all_records for d in record['draws'] if d['suggestion'] is not None}
    for path in sorted((root / 'worlds').glob('*/replies/responses.sqlite')):
        cell = path.parent.parent
        if cell.name not in declared:
            raise ValueError('physical inference directory was never declared by a generated native draw')
        if cell.name not in physical:
            partial_proofs.append(partial_physical_proof(cell, declared[cell.name], b['world'], classification))
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
            counts = dict(db.execute('SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
        caches.append({'path': str(path), 'sha256': file_sha256(path), 'outcomes': counts})
    replies = sum(c['outcomes'].get('response', 0) for c in caches)
    recorded_caches = raw['physical_response_caches']
    cache_paths_valid = len(recorded_caches) == len(caches)
    for recorded, actual in zip(recorded_caches, caches):
        path = Path(recorded['path'])
        actual_path = Path(actual['path'])
        matching_path = (path.resolve() == actual_path.resolve() if path.is_absolute() else
            '..' not in path.parts and tuple(actual_path.parts[-len(path.parts):]) == path.parts)
        cache_paths_valid = cache_paths_valid and matching_path and (
            {k: v for k, v in recorded.items() if k != 'path'} == {k: v for k, v in actual.items() if k != 'path'})
    if not cache_paths_valid or raw['physical_reply_count'] != replies:
        raise ValueError('actual physical reply cache counts/hash differ from summary')
    if complete and (replies != sum(p['response_proof']['researcher_responses'] for p in proof_rows)
            or len(caches) != 4):
        raise ValueError('completed pilot has unassigned physical inference caches')
    claims = raw['claims']
    if (claims['live_fixed_Qwen_researchers'] != (replies > 0) or claims['scripted_researcher_HTTP'] is not False
            or claims['engineering_count_loss'] is not True or any(claims[k] is not False for k in (
                'held_out', 'causal_institutional_benefit', 'scientific_value', 'full_native_world_pathwise_autograd',
                'designer_improvement_established', 'external_authorship_authenticated'))):
        raise ValueError('raw interpretive claims exceed actual pilot evidence')
    result = deepcopy(raw)
    result.update(classification=classification, observations=rows)
    if classification == FIXTURE:
        result['claims'].update(live_fixed_Qwen_researchers=False, scripted_researcher_HTTP=True)
    result['audit'] = {'schema': 'scienceutopia.native-open-independent-audit.v7',
        'status': 'complete' if complete else 'incomplete', 'budget_terminal': terminal,
        'raw_root': str(root), 'raw_evidence_sha256': inventory['evidence.json'],
        'raw_files_verified_unchanged': len(inventory), 'raw_inventory_sha256': digest(inventory),
        'raw_input_sha256s': inventory, 'new_model_calls': 0, 'new_container_executions': 0,
        'campaign_semantics_replayed': True, 'external_authoring_proofs': authoring,
        'analysis_source_sha256s': {path: file_sha256(ROOT / path) for path in (
            'scripts/analyze_native_open_v7.py', 'scripts/audit_native_objective_v5.py',
            'scripts/analyze_native_society_v6.py', 'utopia/optimization/native_adaptive_search.py',
            'utopia/optimization/native_hybrid.py', 'utopia/system/native_kernel.py',
            'utopia/system/native_open_domain.py', 'utopia/system/native_migration.py')},
        'native_run_proofs': proof_rows, 'physical_native_worlds': len(physical), 'researcher_responses': replies,
        'partial_physical_run_proofs': partial_proofs,
        'loss_path': [r['observation']['loss'] if r['observation'] else None for r in rows],
        'pending': deepcopy(controller.state['pending']),
        'limits': ['One development seed and four fresh worlds, not independent seed replication or a causal comparison.',
            'Loss -accepted decisions -0.1*delivered contexts is a deliberately gameable engineering count proxy, not scientific quality.',
            'Conditional tensor replay/backward is not the joint LossSpec or the full native/LLM derivative.',
            'Score gradients concern the declared design distribution; designer history/strategy changes are not proof of improving designer capability.',
            'External author identity is self-reported and not provider-authenticated.',
            'Physical code contexts with ambiguous matches are retained; only committed native events count as effects.']}
    result.pop('content_sha256')
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
    print(json.dumps({'status': report['audit']['status'], 'native_worlds': report['audit']['physical_native_worlds'],
        'loss_path': report['audit']['loss_path'], 'report_sha256': report['content_sha256']}))


if __name__ == '__main__':
    main()
