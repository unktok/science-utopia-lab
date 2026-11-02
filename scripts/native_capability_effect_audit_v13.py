"""Read-only full-plan and actual-review routing joins for prospective v13."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

from utopia.optimization.native_code_trace import validate_record
from utopia.runtime.checkpointing import canonical_json, read_portable_checkpoint
from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import digest
from utopia.system.native_activity_contracts import EFFECT, reconstruct_applied_plan
from utopia.system.native_migration import native_execution_nodes
from utopia.system.native_review_routing import EVENT, validate_routing_receipt
from utopia.utils.data_utils import file_sha256
from utopia.utils.seeding import derive_seed


def origin_proof(system, event, origin, payload, events, code_rows, target_port):
    """Join captured input values to declared wires and earlier source receipts."""
    ids = origin['input_event_ids']
    if (not ids or not set(ids) <= set(event['provenance']['input_event_ids'])
            or any(identity not in events or events[identity]['sequence'] >= event['sequence'] for identity in ids)):
        raise ValueError('capability input origin is missing, future or outside actual consumer inputs')
    edges = [e for e in system.connections if e.source_mechanism == origin['source_mechanism']
        and e.source_port == origin['source_port'] and e.target_port == target_port
        and e.target_mechanism == event['provenance']['mechanism_id']
        and origin['emitted_period'] + e.latency <= event['year']]
    if not edges:
        raise ValueError('capability origin lacks its explicitly declared available source wire')
    source_events = [events[identity] for identity in ids
        if events[identity]['provenance']['mechanism_id'] == origin['source_mechanism']
        and events[identity]['year'] == origin['emitted_period']]
    if not source_events:
        raise ValueError('capability input lacks an actual earlier declared source event')
    nodes = {n.mechanism_id: n for n in native_execution_nodes(system)}
    source = nodes.get(origin['source_mechanism'])
    if source is None:
        raise ValueError('capability origin source absent from actual executed graph')
    matches = []
    if source.implementation == 'code.python.v1':
        for index, row in enumerate(code_rows):
            if (row['artifact'] != source.parameters['code_artifact']
                    or row['context']['period'] != origin['emitted_period']
                    or not any(value['payload'] == payload for value in
                        row['result']['outputs'].get(origin['source_port'], []))):
                continue
            matched = [e['event_id'] for e in source_events if e['event_type'] == 'generated.code_executed'
                and all(e['payload'][key] == row['receipt'][key] for key in
                    ('artifact_sha256', 'context_sha256', 'result_sha256', 'image_id'))]
            if matched:
                matches.append({'code_record_index': index, 'bundle_sha256': row['bundle_sha256'],
                    'source_value_sha256': sha(row['artifact']['source']), 'generated_event_ids': matched})
        if not matches:
            raise ValueError('capability payload absent from actual bound generated-code output')
    return {'origin': deepcopy(origin), 'payload_sha256': sha(payload),
        'source_implementation': source.implementation,
        'source_event_sha256s': {e['event_id']: digest(e) for e in source_events},
        'available_wire_count': len(edges), 'generated_output_matches': matches,
        'scope': 'Explicit input value, graph wire and source-event receipt join; native source outputs are captured by the source-pinned handler, not rerun.'}


def _review_transport(cell, binding, tasks):
    """Exact item/attempt/seed cache IDs plus original prompt and parsed body."""
    from utopia.constants import IMPORTANT_NOTES
    from utopia.models.models import parse_json_response
    from utopia.agents.base_agent import PaperReview
    wire = [json.loads(line) for line in (Path(cell)/'wire-requests.jsonl').read_text().splitlines()]
    by_payload = {}
    for index, row in enumerate(wire):
        if row['payload_sha256'] != hashlib.sha256(canonical_json(row['payload']).encode()).hexdigest():
            raise ValueError('actual review transport payload hash differs')
        by_payload.setdefault(row['payload_sha256'], []).append((index+1, row))
    journal = Path(cell)/'replies/responses.sqlite'
    with sqlite3.connect(journal.resolve().as_uri()+'?mode=ro', uri=True) as db:
        if db.execute('SELECT binding FROM metadata').fetchall() != [(canonical_json(binding),)]:
            raise ValueError('review transport journal binding differs')
        replies = {row[0]: row[1:] for row in db.execute(
            'SELECT identity,payload_sha,outcome,data,data_sha FROM replies')}
    proofs = []
    for task in tasks:
        matches = []
        for attempt in range(3):
            ctx = ('phase3_reviews', task['year'])
            seed = derive_seed(binding['seed'], *ctx, task['item_index'], attempt)
            identity = hashlib.sha256(canonical_json({'binding': binding, 'seed_ctx': ctx,
                'item_index': task['item_index'], 'attempt': attempt, 'seed': seed}).encode()).hexdigest()
            row = replies.get(identity)
            if row is None:
                continue
            payload_sha, outcome, data, data_sha = row
            if hashlib.sha256(data.encode()).hexdigest() != data_sha:
                raise ValueError('review reply bytes differ from native response journal hash')
            if outcome != 'response':
                continue
            response = json.loads(data)
            try:
                body = parse_json_response(response['choices'][0]['message']['content'])
            except (ValueError, TypeError, KeyError, IndexError):
                continue
            if digest(body) != task['parsed_response_sha256']:
                continue
            if (not isinstance(body, dict) or int(body['overall_score']) != task['native_score']
                    or response['model'] != binding['model']):
                raise ValueError('actual review parsed body or original int score differs')
            for line, entry in by_payload.get(payload_sha, []):
                payload = entry['payload']
                users = [m.get('content') for m in payload.get('messages', []) if m.get('role') == 'user']
                prefix = IMPORTANT_NOTES+'\n\n'
                schema = (payload.get('extra_body', {}).get('structured_outputs', {}).get('json')
                    or payload.get('response_format', {}).get('json_schema', {}).get('schema'))
                if (entry['year'] != task['year'] or payload['model'] != binding['model']
                        or payload.get('seed', payload.get('extra_body', {}).get('seed')) != seed
                        or schema != PaperReview.model_json_schema()
                        or len(users) != 1 or not isinstance(users[0], str) or not users[0].startswith(prefix)
                        or hashlib.sha256(users[0][len(prefix):].encode()).hexdigest() != task['prompt_sha256']):
                    raise ValueError('review task prompt/schema/year/model/seed differs from actual native request')
                matches.append({'cache_identity': identity, 'attempt': attempt, 'seed': seed,
                    'wire_line': line, 'payload_sha256': payload_sha, 'response_sha256': data_sha})
        if not matches:
            raise ValueError('actual review task lacks matching original response-cache/wire proof')
        proofs.append({'task': deepcopy(task), 'transport_matches': matches})
    return proofs


def annual_capability_proof(saved, system, code_rows, *, transport=None):
    """Pure data join; transport callback validates actual journal/wire pairs."""
    year = saved['year']
    events = {e['event_id']: e for e in saved['native_system']['events']}
    plans, routings = [], []
    for event in events.values():
        if event['year'] != year:
            continue
        payload = event['payload']
        if event['event_type'] == EFFECT:
            applied = reconstruct_applied_plan(payload)
            base = payload['base_plan']
            base_proof = origin_proof(system, event, base, base['plan'], events, code_rows, 'plans')
            amendments = [origin_proof(system, event, origin, origin['command'], events, code_rows, 'amendments')
                for origin in payload['amendments']]
            if [a['actor_id'] for a in applied['assignments']] != event['actor_ids']:
                raise ValueError('complete applied plan actors differ from native effect receipt')
            plans.append({'event_id': event['event_id'], 'event_sha256': digest(event), 'event': deepcopy(event),
                'base_plan_sha256': base['plan_sha256'], 'applied_plan_sha256': payload['plan_sha256'],
                'base_plan': deepcopy(base['plan']), 'applied_plan': applied,
                'base_origin_proof': base_proof, 'amendment_origin_proofs': amendments})
        elif event['event_type'] == EVENT:
            validate_routing_receipt(payload)
            if payload['year'] != year or payload['batch']['year'] != year or payload['command']['year'] != year:
                raise ValueError('native routing year differs')
            batch = payload['batch']
            batch_proof = origin_proof(system, event, payload['batch_origin'], batch, events, code_rows, 'batch')
            command_proof = origin_proof(system, event, payload['command_origin'], payload['command'],
                events, code_rows, 'routing')
            snapshots = [events[identity] for identity in payload['batch_origin']['input_event_ids']
                if events[identity]['event_type'] == 'native.system.review_inputs_bound'
                and events[identity]['payload'] == {'batch': batch, 'batch_sha256': sha(batch)}]
            bound = [e for e in events.values() if e['event_type'] == 'native.system.review_tasks_bound'
                and e['year'] == year and e['provenance']['mechanism_id'] == event['provenance']['mechanism_id']
                and e['payload']['tasks'] == payload['native_tasks']
                and e['payload']['tasks_sha256'] == payload['native_tasks_sha256']]
            if len(snapshots) != 1 or len(bound) != 1:
                raise ValueError('routing lacks one actual snapshot and original review-task identity event')
            submitted = []
            for entry in batch['papers']:
                matching = [p for c in saved['conference_system']['conferences'] if c['conference_id'] == entry['conference_id']
                    for decisions in c['decisions'].values() for p in decisions
                    if p['id'] == entry['paper_id'] and p['year'] == year]
                # Original selection legitimately sets status and appends scores/
                # reviews after this snapshot; keep that temporal distinction.
                decision_fields = {'status', 'reviews', 'final_score', 'review_history'}
                if len(matching) != 1 or any(matching[0].get(k) != v for k, v in entry['paper'].items()
                        if k not in decision_fields):
                    raise ValueError('review input paper is not its exact archived actual native submission')
                before_history = entry['paper'].get('review_history', [])
                if matching[0].get('review_history', [])[:len(before_history)] != before_history:
                    raise ValueError('resubmission review-history prefix changed after native review input')
                submitted.append({'paper_id': entry['paper_id'], 'conference_id': entry['conference_id'],
                    'input_paper_sha256': sha(entry['paper']), 'archived_paper_sha256': sha(matching[0]),
                    'later_decision_fields': {k: deepcopy(matching[0].get(k)) for k in sorted(decision_fields)},
                    'eligible_reviewer_ids': deepcopy(entry['eligible_reviewer_ids'])})
            task_proofs = []
            for index, task in enumerate(payload['native_tasks']):
                if task['year'] != year or task['item_index'] != index:
                    raise ValueError('original review task collection order/year differs')
                eligible = next((p['eligible_reviewer_ids'] for p in batch['papers']
                    if p['paper_id'] == task['paper_id'] and p['conference_id'] == task['conference_id']), [])
                records = [r for p in saved['paper_tracker']['papers'] if p['id'] == task['paper_id']
                    for d in p['review_history'] if d['year'] == year and d['conference'] == task['conference_id']
                    for r in d['reviews'] if r['reviewer_id'] == task['reviewer_id']]
                if (task['reviewer_id'] not in eligible or len(records) != 1
                        or sha(records[0]) != task['native_review_sha256']
                        or records[0]['overall_score'] != task['native_score']):
                    raise ValueError('routed native reviewer task differs from one actual archived review')
                task_proofs.append({'task': deepcopy(task), 'archived_review_sha256': sha(records[0])})
            routing = {'event_id': event['event_id'], 'event_sha256': digest(event), 'event': deepcopy(event),
                'actual_review_count': payload['actual_review_count'], 'submitted_papers': submitted,
                'batch_origin_proof': batch_proof, 'command_origin_proof': command_proof,
                'snapshot_event_id': snapshots[0]['event_id'], 'task_identity_event_id': bound[0]['event_id'],
                'native_tasks': task_proofs}
            if transport is not None:
                routing['actual_review_transport'] = transport(payload['native_tasks'])
            routings.append(routing)
    return {'year': year, 'complete_plan_effects': plans, 'review_routings': routings}


def capability_effect_proof(cell, system, checkpoint):
    cell, checkpoint = Path(cell), Path(checkpoint)
    final = read_portable_checkpoint(checkpoint)
    path = cell/'code-contexts.jsonl'
    code_rows = [validate_record(json.loads(line)) for line in path.read_text().splitlines()] if path.exists() else []
    annual = []
    for year in range(1, final['year']+1):
        annual_path = checkpoint.parent/f'portable_checkpoint_year_{year}.json.gz'
        saved = read_portable_checkpoint(annual_path)
        binding = saved['portable']['contract']['binding']
        if saved['year'] != year or saved['native_system']['spec'] != system.to_dict():
            raise ValueError('annual native capability checkpoint/source/period differs')
        annual.append({**annual_capability_proof(saved, system, code_rows,
            transport=lambda tasks: _review_transport(cell, binding, tasks)),
            'checkpoint_sha256': file_sha256(annual_path)})
    return {'complete_plan_effect_count': sum(len(y['complete_plan_effects']) for y in annual),
        'routing_event_count': sum(len(y['review_routings']) for y in annual),
        'routed_actual_review_count': sum(r['actual_review_count'] for y in annual for r in y['review_routings']),
        'annual': annual, 'scope': 'Source/wire-bound captured complete original plans plus exact amendments; actual original submissions, requested/native reviewer identities, archived integer-parsed reviews and original cache/wire prompts. Native snapshot eligibility is captured by the pinned handler, not a counterfactual re-execution. No generated code or native world is executed.'}
