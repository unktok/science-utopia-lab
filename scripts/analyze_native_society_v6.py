#!/usr/bin/env python3
"""Read-only same-society audit: archived facts, not a new forward experiment.

Generated Python, model clients, factories and containers are never invoked.
An incomplete run can be inspected explicitly, but is never labelled complete.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_native_society_pilot_v6 import (
    INTERPRETATION, SCHEMA as PILOT_SCHEMA,
    ExternalSocietyProposer, SocietyPatchInbox, audit_society_pilot, interval_from_checkpoint,
)
from utopia.optimization.loss import loss_spec_sha256
from utopia.optimization.native_code_trace import validate_record
from utopia.optimization.native_society_design import NativeSocietyDesignSession
from utopia.runtime.checkpointing import canonical_json, pack_state, read_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_kernel import NativeScienceKernel, _hash
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-society-v6-audit.v1'
SOURCE_COMMIT = 'f7e3ae454ce53282d5ef75bb7a00f2f7c7b73619'
ACTUAL = 'actual-native-qwen-online-design-pilot'
FIXTURE = 'scripted-fixture-not-native-results'


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('raw evidence must not contain symbolic links')
        if path.is_file():
            result[str(path.relative_to(root))] = file_sha256(path)
    return result


def read(path):
    return SocietyPatchInbox._read(Path(path))


class ReadOnlySession(NativeSocietyDesignSession):
    """Reuse journal semantics without creating directories, locks or a journal."""
    def __init__(self, directory, *, plan):
        self.directory = Path(directory).resolve()
        self.path = self.directory / 'society-design.json'
        if not self.path.is_file():
            raise ValueError('existing society journal required')
        self.founding = SystemSpec.from_dict(plan['founding_system'])
        self.loss_spec = deepcopy(plan['protocol']['loss'])
        self.binding = {'founding_fingerprint': self.founding.fingerprint,
            'loss_spec_sha256': loss_spec_sha256(self.loss_spec), 'world': deepcopy(plan['world'])}
        self._read()

    @contextmanager
    def _lock(self):
        yield


def protocol_classification(plan, expected_source):
    protocol, world = plan['protocol'], plan['world']
    fixture = protocol.get('kind') == 'scripted-same-society-audit-fixture-v6'
    if (protocol.get('schema') != PILOT_SCHEMA or protocol.get('years') != 3
            or protocol.get('adoptions') != 2 or protocol.get('technical_drafts_per_boundary') != 1
            or protocol.get('interpretation') != INTERPRETATION
            or world.get('source_commit') != expected_source or world.get('protocol') != protocol
            or world.get('years') != 3):
        raise ValueError('pinned source / one-society three-year two-draft protocol differs')
    if fixture:
        if protocol.get('evidence') != FIXTURE:
            raise ValueError('scripted QA requires explicit non-live classification')
        return FIXTURE
    if (protocol.get('kind') != 'external-native-same-society-v6'
            or protocol.get('researcher_model') != 'qwen3:8b' or world.get('model') != 'qwen3:8b'
            or protocol.get('thinking') is not False or protocol.get('max_tokens') != 768
            or protocol.get('seed') != 1301 or world.get('seed') != 1301
            or protocol.get('population') != 'five-independent-balanced-researchers'
            or protocol.get('corpus_years') != 4 or world.get('corpus_years') != 4
            or protocol.get('no_hidden_merit_or_promotion_veto') is not True):
        raise ValueError('actual fixed-Qwen preregistration differs; not a live result')
    return ACTUAL


def _without_design(saved):
    result = deepcopy(saved)
    result.pop('native_system')
    result['portable']['contract'].pop('native_system')
    return result


def _domain(saved):
    result = {key: saved[key] for key in ('ecosystem_data', 'paper_tracker', 'funding_tracker',
        'conference_system', 'citation_tracker', 'submitted_paper_ids', 'yearly_results')}
    result['submitted_paper_ids'] = sorted(result['submitted_paper_ids'])
    return result


def checkpoint_proofs(session, checkpoints):
    """Compare actual saved worlds to immutable observations AND pre-adoption bytes."""
    view = session.projection()
    initial = read_portable_checkpoint(checkpoints / 'portable_checkpoint_year_0.json.gz')
    initial_contract = deepcopy(initial['portable']['contract'])
    initial_contract.pop('native_system')
    if (initial.get('year') != 0 or initial.get('phase') != 0
            or initial['native_system']['spec'] != session.founding.to_dict()
            or initial['native_system']['last_year'] != 0 or initial['native_system']['events']
            or initial['portable']['response_cache_count'] != 0
            or initial_contract != view['actual_society_binding']['portable_contract']):
        raise ValueError('original initialized society / portable binding was replaced')
    roster = sorted(a['id'] for a in initial['ecosystem_data']['agents'])
    proofs, previous, event_prefix, last_timing = [], {}, [], 0.0
    for obs in view['observations']:
        archive = session.directory / 'observed-societies' / (obs['checkpoint_sha256'] + '.json.gz')
        saved, kernel, cumulative = interval_from_checkpoint(archive, after_year=0,
            fingerprint=obs['system_fingerprint'])
        world = session.binding['world']
        contract = saved['portable']['contract']
        fixture = world['protocol']['kind'] == 'scripted-same-society-audit-fixture-v6'
        corpus_digest = saved['rag']['ordered_documents_sha256']
        if (((corpus_digest is not None or not fixture) and corpus_digest != world['corpus_sha256'])
                or contract['model'] != world['model'] or contract['model_revision'] != world['model_digest']
                or ('dataset_identity' in world and saved['rag']['dataset_identity'] != world['dataset_identity'])):
            raise ValueError('actual archived RAG corpus / dataset / model identity differs')
        if (digest(_domain(saved)) != obs['domain_sha256'] or _hash(saved['native_system']) != obs['kernel_sha256']
                or kernel.spec.to_dict() != obs['system']):
            raise ValueError('immutable observed native domain / kernel / system differs')
        actual_path = checkpoints / f"portable_checkpoint_year_{obs['through_year']}.json.gz"
        actual = read_portable_checkpoint(actual_path)
        actual_spec = SystemSpec.from_dict(actual['native_system']['spec'])
        actual_kernel = NativeScienceKernel(actual_spec, checkpoint=actual['native_system'])
        if (actual['year'] != obs['through_year'] or actual['phase'] != 5
                or actual['portable']['contract']['native_system'] != {'system_fingerprint': actual_spec.fingerprint}
                or digest(pack_state(_without_design(actual))) != digest(pack_state(_without_design(saved)))):
            raise ValueError('same-boundary adoption changed non-design scientific/portable state')
        adoptions = [a for a in view['adoptions'] if a['after_year'] == obs['through_year']]
        if len(adoptions) > 1:
            raise ValueError('multiple adoptions at one native boundary')
        expected = deepcopy(saved['native_system'])
        migration_archive_sha = None
        if adoptions:
            adoption, = adoptions
            migration = adoption['migration']
            old_path = checkpoints / 'design-migration-archives' / archive.name
            if old_path.read_bytes() != archive.read_bytes():
                raise ValueError('pre-adoption whole-society bytes differ from observed archive')
            migration_archive_sha = file_sha256(old_path)
            if (migration['parent_kernel_sha256'] != obs['kernel_sha256']
                    or migration['source_spec'] != kernel.spec.to_dict()
                    or migration['source_graph'] != kernel.graph_checkpoint):
                raise ValueError('migration source does not match the inspected native kernel')
            expected.update(spec=migration['target_spec'],
                system_fingerprint=SystemSpec.from_dict(migration['target_spec']).fingerprint,
                graph_checkpoint=migration['target_graph'],
                design_history=[*expected.get('design_history', []), migration])
        if actual['native_system'] != expected:
            raise ValueError('actual saved post-adoption kernel differs from the exact migration')
        if [a['migration'] for a in view['adoptions'] if a['after_year'] <= obs['through_year']] != actual_kernel.design_history:
            raise ValueError('actual checkpoint omits or forges an adopted migration')
        ids = sorted(a['id'] for a in saved['ecosystem_data']['agents'])
        if ids != roster:
            raise ValueError('actor lineage/population changed across the persistent society')
        roster = ids
        if kernel.to_dict()['events'][:len(event_prefix)] != event_prefix:
            raise ValueError('native history was reset or rewound across observed intervals')
        event_prefix = kernel.to_dict()['events']
        differences = {}
        for key, value in cumulative['metrics'].items():
            # Stocks are reported at the interval endpoint; never subtract them.
            if key.startswith('native.final_'):
                continue
            if value['status'] == 'measured' and previous.get(key, {'status': 'measured'})['status'] == 'measured':
                difference = value['value'] - previous.get(key, {}).get('value', 0)
                interval = obs['measurement']['metrics'][key]
                if interval['status'] != 'measured' or not math.isclose(difference, interval['value'], abs_tol=1e-10, rel_tol=1e-12):
                    raise ValueError('cumulative native counters do not reproduce interval measurements')
                differences[key] = difference
        previous = cumulative['metrics']
        timing = saved['portable']['llm_call_stats'].get('elapsed_seconds', 0.0)
        if (isinstance(timing, bool) or not isinstance(timing, (int, float))
                or not math.isfinite(timing) or timing < last_timing):
            raise ValueError('cumulative saved LLM timing is nonfinite or rewound')
        proofs.append({'actual_checkpoint_sha256': file_sha256(actual_path),
            'observed_checkpoint_sha256': file_sha256(archive),
            'pre_adoption_society_sha256': migration_archive_sha,
            'actual_saved_system_fingerprint': actual_spec.fingerprint,
            'archived_ordered_corpus_sha256': corpus_digest,
            'cumulative_response_count': saved['portable']['response_cache_count'],
            'response_cache_prefix': obs.get('response_cache_prefix'),
            'cumulative_flow_metrics': cumulative['metrics'], 'interval_counter_differences': differences,
            'same_actor_ids_sha256': digest(ids), 'actor_count': len(ids),
            'llm_call_stats': saved['portable']['llm_call_stats'],
            'interval_llm_elapsed_seconds': timing - last_timing,
            'native_event_count': len(kernel.events)})
        last_timing = timing
    return proofs


def response_proofs(cell, binding, counts, *, complete, protocol, classification, expected_prefixes=None,
        maximum_year=3):
    """Read SQLite in ro mode; join physical HTTP payloads to committed replies."""
    path = cell / 'replies/responses.sqlite'
    database = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        if database.execute('SELECT binding FROM metadata').fetchall() != [(canonical_json(binding),)]:
            raise ValueError('actual response SQL binding differs from the observed society')
        replies = database.execute('SELECT identity,payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
    finally:
        database.close()
    wires = [json.loads(line) for line in (cell / 'wire-requests.jsonl').read_text().splitlines()]
    reply_years, offset = [], 0
    for identity, payload_sha, outcome, data, data_sha in replies:
        if outcome != 'response' or hashlib.sha256(data.encode()).hexdigest() != data_sha or len(identity) != 64:
            raise ValueError('actual completed response identity/content hash differs')
        parsed = json.loads(data)
        canonical_json(parsed)
        if parsed.get('model') != binding['model']:
            raise ValueError('completed researcher response declares another model')
        while offset < len(wires) and wires[offset]['payload_sha256'] != payload_sha:
            offset += 1  # Failed transports may leave an unmatched physical input.
        if offset == len(wires):
            raise ValueError('completed response has no ordered actual HTTP input')
        reply_years.append(wires[offset]['year'])
        offset += 1
    for row in wires:
        payload = row['payload']
        if (hashlib.sha256(canonical_json(payload).encode()).hexdigest() != row['payload_sha256']
                or payload['model'] != binding['model'] or type(row['year']) is not int or not 1 <= row['year'] <= maximum_year):
            raise ValueError('actual HTTP payload hash/model/year differs')
        if classification == ACTUAL and (payload.get('max_tokens') != 768 or payload.get('reasoning_effort') != 'none'):
            raise ValueError('actual researcher inference settings changed')
    if reply_years != sorted(reply_years) or any(n > len(replies) for n in counts):
        raise ValueError('native response chronology/count differs')
    for year, count in enumerate(counts, 1):
        if count != sum(y <= year for y in reply_years):
            raise ValueError('portable response count does not equal committed physical-year prefix')
    prefixes = []
    for count, expected in zip(counts, expected_prefixes or [None] * len(counts)):
        actual = {'schema': 'scienceutopia.completed-response-prefix.v1', 'response_count': count,
            'binding_sha256': digest(binding),
            'rows_sha256': digest([[r[0], r[1], r[2], r[4]] for r in replies[:count]])}
        if expected is not None and expected != actual:
            raise ValueError('observed committed response prefix differs from actual ordered SQL replies')
        prefixes.append({'response_count': count, 'pinned_by_observation': expected is not None,
            'actual_prefix_identity': actual})
    extras = len(replies) - (counts[-1] if counts else 0)
    if complete and extras:
        raise ValueError('completed pilot contains uncheckpointed inference')
    return {'researcher_responses': len(replies), 'uncheckpointed_responses': extras,
        'cumulative_responses_per_year': counts, 'responses_by_physical_year': dict(Counter(reply_years)),
        'wire_requests': len(wires), 'wire_sha256': file_sha256(cell / 'wire-requests.jsonl'),
        'response_sql_sha256': file_sha256(path), 'response_content_chain_sha256': digest(replies),
        'response_binding': binding, 'response_prefix_proofs': prefixes,
        'unmatched_http_inputs': len(wires) - len(replies)}


def code_proofs(cell, session, world):
    rows = [validate_record(json.loads(line)) for line in (cell / 'code-contexts.jsonl').read_text().splitlines()] if (cell / 'code-contexts.jsonl').exists() else []
    view, events = session.projection(), {}
    for obs in view['observations']:
        saved = read_portable_checkpoint(session.directory / 'observed-societies' / (obs['checkpoint_sha256'] + '.json.gz'))
        for event in saved['native_system']['events']:
            if event['event_type'] == 'generated.code_executed':
                events[event['event_id']] = event
    matches_by_event = {key: [] for key in events}
    physical = []
    last_year = view['observations'][-1]['through_year'] if view['observations'] else 0
    for index, row in enumerate(rows):
        if row['binding'] != {'source_commit': world['source_commit'], 'system_fingerprint': session.founding.fingerprint, 'run_id': 'persistent-society'}:
            raise ValueError('code context founding-run/source binding differs')
        if row['receipt'].get('image_id') != world['image_id']:
            raise ValueError('code context container image differs')
        if type(row['context'].get('period')) is not int or not 1 <= row['context']['period'] <= 3:
            raise ValueError('code context is outside the declared native horizon')
        preceding = [a for a in view['adoptions'] if a['after_year'] < row['context']['period']]
        current = preceding[-1]['migration']['target_spec'] if preceding else session.founding.to_dict()
        if not any(node['implementation'] == 'code.python.v1'
                and node['parameters']['code_artifact'] == row['artifact'] for node in current['mechanisms']):
            raise ValueError('physical code context is not an actually active source in its year')
        matches = [key for key, event in events.items() if event['year'] == row['context']['period']
            and all(event['payload'][k] == row['receipt'][k] for k in ('image_id', 'artifact_sha256', 'context_sha256', 'result_sha256'))]
        for key in matches:
            matches_by_event[key].append(index)
        physical.append({'record_index': index, 'bundle_sha256': row['bundle_sha256'],
            'year': row['context']['period'], 'matching_native_event_ids': matches})
    if any(not indices for indices in matches_by_event.values()):
        raise ValueError('actual native code execution lacks its exact context/result receipt')
    ambiguous = [key for key, indices in matches_by_event.items() if len(indices) != 1
        or any(len(physical[i]['matching_native_event_ids']) != 1 for i in indices)]
    unattributed = [p for p in physical if not p['matching_native_event_ids'] and p['year'] <= last_year]
    partial = [p for p in physical if p['year'] > last_year]
    one_to_one = not ambiguous and not unattributed and not partial
    for item in physical:
        item['attribution'] = ('uncheckpointed-year-context' if item['year'] > last_year else
            'unattributed-completed-year-context-possible-uncommitted-attempt' if not item['matching_native_event_ids'] else
            'ambiguous-physical-attempt-no-unique-commit-attribution' if any(k in ambiguous for k in item['matching_native_event_ids']) else
            'unique-exact-committed-event-match')
    return {'recorded_executions': len(rows), 'checkpointed_executions': len(events),
        'checkpointed_native_event_count': len(events),
        'status': 'one-to-one-receipt-matches' if one_to_one else 'physical-attempt-attribution-incomplete',
        'one_to_one_physical_execution_proven': one_to_one,
        'uncheckpointed_execution_contexts': len(partial),
        'unattributed_completed_year_contexts': len(unattributed),
        'ambiguous_native_event_count': len(ambiguous),
        'physical_records': physical,
        'native_event_context_candidates': [{'event_id': key, 'year': events[key]['year'],
            'mechanism_id': events[key]['provenance']['mechanism_id'],
            'physical_record_indices': indices, 'unique_attribution': key not in ambiguous}
            for key, indices in matches_by_event.items()],
        'bundle_sha256s': [r['bundle_sha256'] for r in rows],
        'scope': 'Checkpointed native events are counted once from authoritative epochs, never once per physical context. '
            'All physical rows are retained; no attempt is arbitrarily selected or deduplicated. '
            'Unmatched and many-to-one rows do not independently prove a committed effect. '
            'binding.system_fingerprint is the fixed founding invocation; exact artifacts and epochs bind migrated source.'}


def authoring_proofs(directory, session):
    """Reconstruct exact external requests without calling a file-writing inbox."""
    inbox = SocietyPatchInbox(directory)  # Constructor only verifies existing consumed files.
    sections = {key: {p.stem for p in (directory / key).glob('*.json')}
        for key in ('requests', 'responses', 'consumed')}
    if (not sections['consumed'] <= sections['responses'] <= sections['requests']
            or len(sections['requests']) > 2):
        raise ValueError('external request/response sets or total two-draft budget differs')
    journal = session._read()['events']
    indices, proofs = set(), []

    class Captured(BaseException):
        pass

    class Capture:
        def generate(self, **kwargs):
            self.request = json.loads(json.dumps({'schema': 'scienceutopia.external-manifest-request.v5',
                'request': kwargs}, ensure_ascii=False, allow_nan=False))
            raise Captured

    for identity in sorted(sections['requests']):
        raw = inbox._verify_request(identity)
        authored = raw['request']['authoring_input']
        feedback_hash = authored['feedback']['journal_sha256']
        matches = [e['index'] for e in journal if e['sha256'] == feedback_hash]
        if len(matches) != 1:
            raise ValueError('external request feedback is not a real journal prefix')
        prefix = journal[:matches[0] + 1]
        feedback = {'observations': [e['payload'] for e in prefix if e['kind'] == 'observed'],
            'requests': [e['payload'] for e in prefix if e['kind'] == 'staged'],
            'adoptions': [e['payload'] for e in prefix if e['kind'] == 'adopted'],
            'journal_sha256': feedback_hash}
        obs = feedback['observations'][-1]
        index = len(feedback['requests'])
        if index in indices or obs['through_year'] != index + 1:
            raise ValueError('more than one technical draft at the same society boundary')
        indices.add(index)
        saved = read_portable_checkpoint(session.directory / 'observed-societies' / (obs['checkpoint_sha256'] + '.json.gz'))
        capture = Capture()
        proposer = object.__new__(ExternalSocietyProposer)
        proposer.inbox, proposer.world_binding = capture, session.binding['world']
        proposer.image_id = session.binding['world']['image_id']
        proposer.domain_provider = lambda: _domain(saved)
        try:
            proposer(SystemSpec.from_dict(obs['system']), feedback, index, session.loss_spec)
        except Captured:
            pass
        if capture.request != raw or digest(raw) != identity:
            raise ValueError('exact external prompt / domain / feedback / loss / schema request differs')
        proof = {'proposal_index': index, 'request_sha256': identity,
            'request_file_sha256': file_sha256(inbox._path('requests', identity)),
            'status': 'awaiting-response', 'parent_observation_id': obs['observation_id']}
        if identity in sections['responses']:
            response = inbox._response(identity)
            proof.update(response_file_sha256=file_sha256(inbox._path('responses', identity)),
                response_sha256=digest(response), manifest_sha256=digest(response['manifest']),
                author_claim=response['authoring'], status='awaiting-consumption')
        if identity in sections['consumed']:
            proof['status'] = 'consumed'
        proofs.append(proof)
    return sorted(proofs, key=lambda p: p['proposal_index'])


def primary_plan_proof(saved, effect, code_rows):
    """Exact full-plan code output -> effect hash -> real actor/paper facts.

    This covers primary plans, not merely optional amendment batches. Physical
    duplicate candidates stay explicit; no source is executed or chosen by rank.
    """
    spec = saved['native_system']['spec']
    events = {e['event_id']: e for e in saved['native_system']['events']}
    primary_edges = [edge for edge in spec['connections'] if edge['target_mechanism'] == effect['provenance']['mechanism_id']
        and edge['target_port'] == 'plans' and edge['channel'] == 'artifact']
    candidates = []
    for edge in primary_edges:
        for identity in effect['provenance']['input_event_ids']:
            event = events[identity]
            if (event['event_type'] != 'generated.code_executed'
                    or event['provenance']['mechanism_id'] != edge['source_mechanism']):
                continue
            for index, record in enumerate(code_rows):
                if record['context']['period'] != effect['year'] or not all(event['payload'][key] == record['receipt'][key]
                        for key in ('image_id', 'artifact_sha256', 'context_sha256', 'result_sha256')):
                    continue
                for envelope in record['result']['outputs'].get(edge['source_port'], []):
                    plan = deepcopy(envelope['payload'])
                    if plan.get('schema') != 'native-research-plan-v1' or plan.get('year') != effect['year']:
                        raise ValueError('primary code output is not an actual current-year plan')
                    # Pure data reconstruction of the saved, already verified
                    # amendment commands; never invoke a native capability.
                    for amendment in effect['payload']['amendments']:
                        command = amendment['command']
                        aid = command['assignment']['actor_id']
                        matching = [i for i in plan['assignments'] if i['actor_id'] == aid]
                        if len(matching) != 1:
                            raise ValueError('primary plan amendment has no unique actual assignment')
                        matching[0].clear()
                        matching[0].update(deepcopy(command['assignment']))
                        if command['submit'] and aid not in plan['submit_actor_ids']:
                            plan['submit_actor_ids'].append(aid)
                        elif not command['submit'] and aid in plan['submit_actor_ids']:
                            plan['submit_actor_ids'].remove(aid)
                    if digest(plan) != effect['payload']['plan_sha256']:
                        raise ValueError('primary code plan differs from actual applied plan hash')
                    candidates.append((index, identity, edge, plan))
    if not candidates:
        return None  # Native primary producer is not falsely called a code-authored plan.
    hashes = {digest(item[3]) for item in candidates}
    if len(hashes) != 1:
        raise ValueError('primary plan candidates disagree; no arbitrary source selection')
    plan = candidates[0][3]  # Equal-by-hash logical content, not a selected physical attempt.
    actor_states = saved['portable']['agent_states']
    for assignment in plan['assignments']:
        state = actor_states[assignment['actor_id']]['state']
        direction = state['newest_direction']['direction']
        direction = direction.to_dict() if hasattr(direction, 'to_dict') else direction
        if (direction != assignment['direction']
                or any(state[key] != assignment[key] for key in ('project_start_year', 'project_end_year'))
                or any(state['newest_direction'][key] != assignment[key] for key in ('detailed_focus', 'reason'))):
            raise ValueError('applied primary code plan differs from actual saved actor state')
    actual_submissions = {aid: sorted(p['id'] for p in saved['paper_tracker']['papers']
        if p['year'] == effect['year'] and aid in (p['author_id'] if isinstance(p['author_id'], list) else [p['author_id']]))
        for aid in plan['submit_actor_ids']}
    return {'effect_event_id': effect['event_id'], 'plan_sha256': effect['payload']['plan_sha256'],
        'year': effect['year'], 'source_native_event_ids': sorted({c[1] for c in candidates}),
        'physical_record_candidates': sorted({c[0] for c in candidates}),
        'primary_connections': [edge for edge in primary_edges if any(c[2] == edge for c in candidates)],
        'verified_actor_assignment_ids': [item['actor_id'] for item in plan['assignments']],
        'requested_submit_actor_ids': plan['submit_actor_ids'],
        'actual_submission_ids_by_requested_actor': actual_submissions,
        'actual_unique_submission_ids': sorted({pid for ids in actual_submissions.values() for pid in ids}),
        'scope': 'Recorded primary-plan content, applied hash, saved actor state and actual paper identities; not a counterfactual effect or unique physical-attempt attribution.'}


def activity_plan_proofs(session, cell):
    code_rows = [validate_record(json.loads(line)) for line in (cell / 'code-contexts.jsonl').read_text().splitlines()] if (cell / 'code-contexts.jsonl').exists() else []
    reports = []
    for obs in session.projection()['observations']:
        saved = read_portable_checkpoint(session.directory / 'observed-societies' / (obs['checkpoint_sha256'] + '.json.gz'))
        effects = [e for e in saved['native_system']['events'] if e['event_type'] == 'native.system.research_plan_applied'
            and obs['after_year'] < e['year'] <= obs['through_year']]
        proofs = [proof for e in effects if (proof := primary_plan_proof(saved, e, code_rows)) is not None]
        reports.append({'applied_plan_batches': len(effects),
            'amendment_batches': sum(bool(e['payload']['amendments']) for e in effects),
            'code_authored_primary_plan_batches': len(proofs), 'primary_plan_lineage': proofs,
            'scope': 'Amendment batches are not all activity effects; a complete authored primary plan can apply with zero amendments.'})
    return reports


def analyze(run, *, require_complete=True, expected_source=SOURCE_COMMIT):
    run = Path(run).resolve()
    before = inventory(run)
    plan = read(run / 'plan.json')
    classification = protocol_classification(plan, expected_source)
    session = ReadOnlySession(run / 'session', plan=plan)
    view = session.projection()
    progress = read(run / 'progress.json')
    complete = (run / 'completion.json').is_file()
    years = [o['through_year'] for o in view['observations']]
    if (years != list(range(1, len(years) + 1)) or len(years) > 3
            or len(view['adoptions']) > 2 or len(view['requests']) > 2 or view['cancellations']):
        raise ValueError('declared boundary/draft budget or chronological society path differs')
    if complete:
        from scripts.run_native_society_pilot_v6 import progress as make_progress
        expected = make_progress(session, status='complete')
        if (read(run / 'completion.json') != expected or progress != expected or years != [1, 2, 3]
                or len(view['adoptions']) != 2 or view['pending'] is not None):
            raise ValueError('terminal complete receipt differs from actual three-year society')
    elif require_complete:
        raise ValueError('society pilot is incomplete; explicitly allow pending/failure inspection')
    elif (progress.get('status') == 'complete' or progress.get('through_year') != (years[-1] if years else 0)
            or progress.get('loss_path') != [o['loss'] for o in view['observations']]
            or progress.get('adoptions') != len(view['adoptions'])):
        raise ValueError('incomplete progress misrepresents the actual saved boundaries')
    if not view['actual_society_binding']:
        raise ValueError('actual bound society observation required')
    config = read(run / 'society-session-config.json')
    checkpoints = Path(config['checkpoint_directory']).resolve()
    if not checkpoints.is_relative_to(run):
        raise ValueError('operator checkpoint directory must be inside the audited raw tree')
    if (config['directory'] != str(session.directory) or config['founding_system'] != plan['founding_system']
            or config['loss_spec'] != session.loss_spec or config['world_binding'] != plan['world']
            or read(run / 'runs/persistent-society/system.json') != plan['founding_system']):
        raise ValueError('frozen server/run configuration belongs to another society')
    base = audit_society_pilot(session, inbox_directory=run / 'authoring-inbox')
    authoring_requests = authoring_proofs(run / 'authoring-inbox', session)
    proofs = checkpoint_proofs(session, checkpoints)
    for row, proof in zip(base['rows'], proofs):
        row.update(proof)
    binding = view['actual_society_binding']['response_cache_binding']
    if binding != view['actual_society_binding']['portable_contract']['binding']:
        raise ValueError('physical response-cache and native portable bindings differ')
    if classification == ACTUAL:
        science = binding['science_config']
        if (science.get('experiment') != plan['protocol'] or science.get('thinking_override') is not False
                or science.get('max_tokens') != 768 or binding.get('cell') != session.founding.fingerprint
                or sum(a['can_author'] for a in read_portable_checkpoint(checkpoints / 'portable_checkpoint_year_0.json.gz')['ecosystem_data']['agents']) != 5):
            raise ValueError('actual native researcher/source/protocol/founding population differs')
    physical = response_proofs(run / 'runs/persistent-society', binding,
        [p['cumulative_response_count'] for p in proofs], complete=complete,
        protocol=plan['protocol'], classification=classification,
        expected_prefixes=[o.get('response_cache_prefix') for o in view['observations']])
    code = code_proofs(run / 'runs/persistent-society', session, plan['world'])
    for row, activity in zip(base['rows'], activity_plan_proofs(session, run / 'runs/persistent-society')):
        row['activity_plans'] = activity
    confirmations = {c['request_sha256'] for c in view['confirmations']}
    if any(a['request_sha256'] not in confirmations for a in view['adoptions']):
        raise ValueError('actual adoption lacks durable explicit consent')
    if complete and len(base['authoring']['requests']) != 2:
        raise ValueError('completed pilot does not have exactly two external authoring requests')
    actual_years = sorted(int(p.name.removeprefix('portable_checkpoint_year_').removesuffix('.json.gz'))
        for p in checkpoints.glob('portable_checkpoint_year_*.json.gz'))
    if any(y not in (0, 1, 2, 3) for y in actual_years) or (complete and actual_years != [0, 1, 2, 3]):
        raise ValueError('actual checkpoint horizon differs from declared three-year society')
    after = inventory(run)
    if before != after:
        raise ValueError('raw evidence changed during read-only audit; retry from a quiescent snapshot')
    return {'schema': SCHEMA, 'classification': classification, 'status': 'complete' if complete else 'incomplete',
        'native_status': progress['status'], 'source_commit': expected_source, 'physical_societies': 1,
        'auditor_source_sha256': file_sha256(Path(__file__)),
        'measurement_extractor_source_sha256': file_sha256(ROOT / 'scripts/run_native_society_pilot_v6.py'),
        'actual_world_binding': {key: plan['world'][key] for key in ('source_commit', 'model', 'model_digest',
            'corpus_sha256', 'dataset_identity', 'runtime_seed_binding', 'seed', 'years', 'corpus_years', 'image_id')
            if key in plan['world']},
        'loss_path': base['loss_path'], 'rows': base['rows'], 'adoptions': view['adoptions'],
        'authoring': base['authoring'], 'authoring_requests': authoring_requests,
        'author_claims': [r['authoring'] for r in view['requests']],
        'author_identity_authenticated': False, 'designer_transport': 'hash-bound-external-manifest',
        'code_contexts': code, **physical, 'audit_new_model_calls': 0,
        'actual_checkpoint_years': actual_years,
        'unobserved_checkpoint_years': [y for y in actual_years if y and y not in years],
        'raw_files_verified_unchanged': len(before), 'raw_inventory_sha256': digest(before),
        'input_file_sha256s': before, 'population_reset': False, 'model_weights_trained': False,
        'interpretation': INTERPRETATION, 'causal_benefit_established': False,
        'technical_failure': {k: progress[k] for k in ('error_type', 'error', 'failed_candidate_loss') if k in progress},
        'limits': ['Online before/after losses are nonstationary, not causal improvement or held-out evidence.',
            'Fixed model/digest, serialized replies and researcher identity are archived provenance, not remote attestation.',
            'Codex/external author identity is self-reported and not authenticated; researcher weights are not trained.',
            'No new inference, generated-source execution, container invocation or scientific world is used by this audit.',
            'Partial-year replies/code contexts are counted physically but never scored as a completed observation.',
            'The recorder has no attempt/commit identifier: replayed or unmatched physical contexts may lack unique commit attribution; see code_contexts, not an arbitrary deduplication.',
            'LLM elapsed_seconds is a saved cumulative call statistic, not total experiment wall time.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-incomplete', action='store_true')
    parser.add_argument('--expected-source', '--source-commit', dest='source_commit', default=SOURCE_COMMIT,
        help='explicit expected pin; never inferred from mutable raw labels')
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.run.resolve()):
        parser.error('audit output must be outside immutable raw evidence')
    result = analyze(args.run, require_complete=not args.allow_incomplete, expected_source=args.source_commit)
    write_json_atomic(args.output, result, sort_keys=True, allow_nan=False)
    print(json.dumps({k: result[k] for k in ('schema', 'classification', 'status', 'loss_path', 'researcher_responses', 'raw_files_verified_unchanged')}, sort_keys=True))


if __name__ == '__main__':
    main()
