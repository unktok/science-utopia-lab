"""Learned opaque-response boundaries composed with original institution programs.

Native forward is unchanged. Autograd belongs to this calibrated representation,
not arbitrary Python, actual researcher text, or the full native simulator.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sqlite3

import numpy as np
import torch

from .loss import evaluate_loss
from .native_hybrid import native_endpoint
from .native_relaxation import replay_tensor_trace, trace_objective
from utopia.runtime.checkpointing import canonical_json, read_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.tensor_program import execute_tensor_program
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-response-boundary.v8'
DTYPE = torch.float64


class BoundaryUnsupported(ValueError):
    """Insufficient actual correspondence/support, never an imputed zero."""


def programs(endpoint):
    return {n['mechanism_id']: n['parameters']['program'] for n in endpoint['system']['mechanisms']
        if n['implementation'] == 'program.tensor.v1'}


def verify_endpoint(endpoint, declarations, loss_spec):
    actual = native_endpoint(endpoint['checkpoint'], SystemSpec.from_dict(endpoint['system']),
        declarations, loss_spec, world=endpoint['world'], code_contexts=endpoint.get('code_contexts'))
    if actual != endpoint:
        raise ValueError('native response endpoint facts differ from independently restored checkpoint')


def binding(endpoint):
    return {key: endpoint[key] for key in ('world', 'physical_initial_identity',
        'noncoordinate_system_sha256', 'coordinates_sha256', 'loss_spec_sha256')}


def boundary_layout(endpoint, *, record_keys=('paper_id', 'conference_id')):
    """Canonical semantic row IDs, preserving all actual rows and numeric columns."""
    ps = programs(endpoint)
    replay_tensor_trace(endpoint['trace'], ps, hard=True, verify_recorded=True)
    layout, values, seen = [], [], set()
    for index, frame in enumerate(endpoint['trace']):
        frame_key = (frame['year'], frame['mechanism'])
        if frame_key in seen:
            raise BoundaryUnsupported('repeated same-period tensor invocation lacks unique boundary call IDs')
        seen.add(frame_key)
        for name, source in frame['input_sources'].items():
            if source['mechanism'] in ps and source['path'] == '/values':
                continue
            array = torch.tensor(frame['inputs'][name], dtype=DTYPE)
            expected = ps[frame['mechanism']]['inputs'][name]
            if array.numel() == 0 and -1 in expected:
                array = array.reshape([0 if d == -1 else d for d in expected])
            records = frame['records']
            if records:
                if array.ndim < 1 or array.shape[0] != len(records):
                    raise BoundaryUnsupported('numeric boundary rows lack one-to-one actual record identities')
                ids = []
                for record in records:
                    if not all(key in record for key in record_keys):
                        raise BoundaryUnsupported('semantic record key absent; no invented alignment')
                    ids.append(canonical_json({key: record[key] for key in record_keys}))
                if len(set(ids)) != len(ids):
                    raise BoundaryUnsupported('duplicate semantic row identity')
                order = sorted(range(len(ids)), key=ids.__getitem__)
                array = array[order]
                identity = [ids[i] for i in order]
            else:
                if array.ndim > 0 and array.shape[0] > 0:
                    raise BoundaryUnsupported('nonempty opaque numeric rows have no declared semantic IDs')
                order, identity = [], []
            if not torch.isfinite(array).all():
                raise BoundaryUnsupported('nonfinite actual opaque boundary')
            start = len(values)
            values.extend(array.flatten().tolist())
            layout.append({'frame': index, 'year': frame['year'], 'mechanism': frame['mechanism'],
                'input': name, 'source': deepcopy(source), 'shape': list(array.shape),
                'semantic_ids': identity, 'offset': start, 'size': array.numel(),
                'canonical_to_actual': order})
    if not values:
        raise BoundaryUnsupported('no observed numeric opaque boundary to calibrate')
    # Original row order is not a new semantic identity. Canonical values are
    # explicitly reinstalled in the template's original order on replay.
    signature = [{k: v for k, v in e.items() if k != 'canonical_to_actual'} for e in layout]
    return layout, torch.tensor(values, dtype=DTYPE), digest(signature)


def make_response_completion_receipt(endpoint, response_cache, wire, *, run_manifest_sha256):
    """Future run-owner completion hook, NOT a retrospective audit seal.

    The owner persists this in its completion manifest before other analyses.
    Hash binding is verifiable; the caller's timing/authorship remains asserted,
    not authenticated. This function writes nothing and performs no model call.
    """
    checkpoint = Path(endpoint['checkpoint']).resolve()
    journal, wire = Path(response_cache.path).resolve(), Path(wire).resolve()
    _review_evidence_paths(checkpoint, journal, wire)
    if (file_sha256(checkpoint) != endpoint['checkpoint_sha256']
            or not _sha256(run_manifest_sha256)):
        raise ValueError('completion receipt requires actual checkpoint/cache/wire and run manifest hash')
    saved = read_portable_checkpoint(checkpoint)
    if (response_cache.binding != saved['portable']['contract']['binding']
            or response_cache.committed_count() != saved['portable']['response_cache_count']
            or response_cache.committed_count() != endpoint['response_cache_count']):
        raise ValueError('completion receipt cache differs from completed native checkpoint')
    value = {'schema': 'scienceutopia.native-response-completion-receipt.v8',
        'checkpoint_sha256': endpoint['checkpoint_sha256'], 'system_fingerprint': endpoint['system_fingerprint'],
        'journal_sha256': file_sha256(journal), 'wire_sha256': file_sha256(wire),
        'response_prefix': response_cache.committed_prefix_identity(), 'run_manifest_sha256': run_manifest_sha256,
        'creation_scope': 'run-owner-asserted-completion-hook', 'timing_authenticated': False}
    if value['journal_sha256'] != file_sha256(journal) or value['wire_sha256'] != file_sha256(wire):
        raise ValueError('completion evidence changed while capturing the owner receipt')
    value['content_sha256'] = digest(value)
    return value


def _sha256(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _review_evidence_paths(checkpoint, journal, wire):
    """Only the two existing original fixture/production layouts, never aliases."""
    if checkpoint.parent.name == 'checkpoints':
        root = checkpoint.parent.parent
        expected = (root/'cache/responses.sqlite', root/'wire.jsonl')
        profile = 'original-scripted-native-layout'
    elif (checkpoint.parent.name == 'native-design' and checkpoint.parent.parent.name == 'checkpoints'
            and checkpoint.parent.parent.parent.name == 'simulation'):
        root = checkpoint.parents[3]
        expected = (root/'replies/responses.sqlite', root/'wire-requests.jsonl')
        profile = 'local-qwen-native-factory-layout'
    else:
        raise ValueError('raw review checkpoint does not use a supported original native layout')
    if (journal, wire) != expected:
        raise ValueError('raw review evidence must be the actual checkpoint sibling journal/wire layout pair')
    return profile


def _review_task_identities(saved, endpoint, years):
    """Read trusted original-phase task identities from the actual checkpoint."""
    from utopia.system.native_review_identity import SCHEMA as identity_schema, EVENT
    events = [e for e in saved.get('native_system', {}).get('events', []) if e.get('event_type') == EVENT]
    if not events:
        return None  # Frozen v8 checkpoints retain their strict uniform adapter.
    review_nodes = {n['mechanism_id'] for n in endpoint['system']['mechanisms']
        if n['implementation'] in ('native.phase.review.v1', 'native.phase.review.with-delivered-context.v1')}
    by_year = {}
    for event in events:
        value = event.get('payload', {})
        year = event.get('year')
        if (set(value) != {'schema', 'year', 'tasks', 'tasks_sha256'} or value['schema'] != identity_schema
                or value['year'] != year or year in by_year
                or event.get('provenance', {}).get('mechanism_id') not in review_nodes
                or not isinstance(value['tasks'], list) or digest(value['tasks']) != value['tasks_sha256']):
            raise BoundaryUnsupported('actual native review identity event is duplicated, untrusted or altered')
        seen = set()
        for i, task in enumerate(value['tasks']):
            if (not isinstance(task, dict) or set(task) != {'item_index', 'year', 'reviewer_id', 'paper_id',
                    'conference_id', 'prompt_sha256', 'parsed_response_sha256', 'native_score', 'native_review_sha256'}
                    or type(task['item_index']) is not int or task['item_index'] != i or task['year'] != year
                    or any(not isinstance(task[k], str) or not task[k] for k in ('reviewer_id', 'paper_id', 'conference_id'))
                    or any(not _sha256(task[k]) for k in ('prompt_sha256', 'parsed_response_sha256', 'native_review_sha256'))
                    or type(task['native_score']) is not int):
                raise BoundaryUnsupported('actual native review task identity is incomplete or altered')
            key = task['conference_id'], task['paper_id'], task['reviewer_id']
            if key in seen:
                raise BoundaryUnsupported('duplicate actual native reviewer/paper identity')
            seen.add(key)
            # Verify the actual archived record, not merely a count/mean or the
            # observer's copied score. Optional later native transforms remain
            # opaque and unsupported instead of being erased by this adapter.
            rows = [r for p in saved.get('paper_tracker', {}).get('papers', []) if p['id'] == task['paper_id']
                for d in p.get('review_history', []) if d.get('year') == year and d.get('conference') == task['conference_id']
                for r in d.get('reviews', []) if r.get('reviewer_id') == task['reviewer_id']]
            if (len(rows) != 1 or digest(rows[0]) != task['native_review_sha256']
                    or rows[0].get('overall_score') != task['native_score']
                    or rows[0].get('arxiv_id') != task['paper_id']
                    or rows[0].get('conference_id') != task['conference_id']):
                raise BoundaryUnsupported('review identity does not bind one unchanged actual archived native review record')
        by_year[year] = value['tasks']
    if set(by_year) != set(years):
        raise BoundaryUnsupported('native review identity years do not exactly cover the represented review boundary')
    return by_year


def raw_review_projection(endpoint, layout, native_values, *, journal, wire, mechanism, input_name,
                          score_column=0, count_column=1, upper=10, completion_receipt=None):
    """Actual per-review int() THEN paper mean, with verified task identities.

    Old checkpoints without task identities retain the strict uniform adapter.
    No record is aligned by score, title, SQL order or concurrent wire order.
    """
    from utopia.agents.base_agent import PaperReview
    from utopia.utils.seeding import derive_seed
    if type(upper) is not int or upper < 1:
        raise ValueError('native positive-int projection requires an explicit positive integer upper bound')
    journal, wire = Path(journal).resolve(), Path(wire).resolve()
    checkpoint = Path(endpoint['checkpoint']).resolve()
    evidence_layout = _review_evidence_paths(checkpoint, journal, wire)
    if file_sha256(checkpoint) != endpoint['checkpoint_sha256']:
        raise ValueError('actual review checkpoint content changed')
    saved = read_portable_checkpoint(checkpoint)
    before = (file_sha256(journal), file_sha256(wire))
    with sqlite3.connect(journal.resolve().as_uri()+'?mode=ro', uri=True) as db:
        metadata = db.execute('SELECT binding FROM metadata').fetchall()
        stored_rows = db.execute('SELECT rowid,identity,payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
        sql_rowids = [row[0] for row in stored_rows]
        replies = [row[1:] for row in stored_rows]
    if len(metadata) != 1:
        raise ValueError('actual numeric response journal has no unique binding')
    b = json.loads(metadata[0][0])
    if (b != saved['portable']['contract']['binding']
            or len(replies) != saved['portable']['response_cache_count']
            or len(replies) != endpoint['response_cache_count']):
        raise ValueError('raw response full binding/count differs from actual completed checkpoint')
    world = endpoint['world']
    if (b['cell'] != endpoint['system_fingerprint'] or b['seed'] != world['seed']
            or b['science_config']['source_commit'] != world['source_commit']
            or b['model_revision'] != world['model_digest'] or b['corpus_sha256'] != world['corpus_sha256']):
        raise ValueError('raw response identity differs from actual native endpoint')
    wires = [json.loads(line) for line in wire.read_text().splitlines()]
    wire_shas = [r['payload_sha256'] for r in wires]
    reply_shas = [row[1] for row in replies]
    if (any(not _sha256(s) for s in (*wire_shas, *reply_shas))
            or len(set(wire_shas)) != len(wires) or len(set(reply_shas)) != len(replies)
            or set(wire_shas) != set(reply_shas)):
        raise ValueError('raw response/wire are not exact fresh one-to-one physical calls')
    # Worker request logging precedes HTTP, while SQLite is committed in
    # completion order. These orders need not agree under concurrency.
    wire_by_sha = {row['payload_sha256']: (index+1, row) for index, row in enumerate(wires)}
    completion_provenance = {'status': 'no-run-completion-receipt', 'timing_authenticated': False,
        'hash_scope': 'current-read-only-bytes-not-a-historical-run-completion-seal'}
    if completion_receipt is not None:
        receipt = completion_receipt
        prefix = {'schema': 'scienceutopia.completed-response-prefix.v1', 'response_count': len(replies),
            'binding_sha256': hashlib.sha256(canonical_json(b).encode()).hexdigest(),
            'rows_sha256': hashlib.sha256(canonical_json([[i, p, o, h] for i, p, o, d, h in replies]).encode()).hexdigest()}
        if (not isinstance(receipt, dict) or set(receipt) != {'schema', 'checkpoint_sha256', 'system_fingerprint',
                'journal_sha256', 'wire_sha256', 'response_prefix', 'run_manifest_sha256', 'creation_scope',
                'timing_authenticated', 'content_sha256'}
                or receipt['schema'] != 'scienceutopia.native-response-completion-receipt.v8'
                or receipt['content_sha256'] != digest({k: v for k, v in receipt.items() if k != 'content_sha256'})
                or receipt['checkpoint_sha256'] != endpoint['checkpoint_sha256']
                or receipt['system_fingerprint'] != endpoint['system_fingerprint']
                or receipt['journal_sha256'] != before[0] or receipt['wire_sha256'] != before[1]
                or receipt['response_prefix'] != prefix or not _sha256(receipt['run_manifest_sha256'])
                or receipt['creation_scope'] != 'run-owner-asserted-completion-hook' or receipt['timing_authenticated'] is not False):
            raise ValueError('caller-supplied completion receipt differs from actual native evidence')
        completion_provenance = {'status': 'hashbound-caller-supplied-completion-assertion',
            'content_sha256': receipt['content_sha256'], 'run_manifest_sha256': receipt['run_manifest_sha256'],
            'timing_authenticated': False, 'hash_scope': 'verified-provided-receipt-not-independent-proof-of-creation-time'}
    selected = [e for e in layout if e['mechanism'] == mechanism and e['input'] == input_name]
    if not selected or len({e['year'] for e in selected}) != len(selected):
        raise BoundaryUnsupported('one explicitly selected actual review boundary per year required')
    task_schema = PaperReview.model_json_schema()
    task_identities = _review_task_identities(saved, endpoint, [e['year'] for e in selected])
    review_requests = {}
    for entry in selected:
        shape = entry['shape']
        if (type(score_column) is not int or type(count_column) is not int or score_column == count_column
                or min(score_column, count_column) < 0 or len(shape) != 2 or max(score_column, count_column) >= shape[1]):
            raise BoundaryUnsupported('review boundary is not the declared numeric score/count matrix')
        original = native_values[entry['offset']:entry['offset']+entry['size']].reshape(shape)
        counts = original[:, count_column].tolist()
        if any(c < 0 or c != int(c) for c in counts):
            raise BoundaryUnsupported('review count column must contain actual nonnegative integer counts')
        task_count = len(task_identities[entry['year']]) if task_identities is not None else int(sum(counts))
        for item in range(task_count):
            for attempt in range(3):
                ctx = ('phase3_reviews', entry['year'])
                seed = derive_seed(b['seed'], *ctx, item, attempt)
                identity = hashlib.sha256(canonical_json({'binding': b, 'seed_ctx': ctx,
                    'item_index': item, 'attempt': attempt, 'seed': seed}).encode()).hexdigest()
                proof = {'year': entry['year'], 'seed': seed, 'item': item, 'attempt': attempt}
                if task_identities is not None:
                    proof['native_task'] = task_identities[entry['year']][item]
                review_requests[identity] = proof
    by_year, transport_rows = {}, []
    for sql_rowid, (identity, payload_sha, outcome, data, data_sha) in zip(sql_rowids, replies):
        wire_line, row = wire_by_sha[payload_sha]
        if (outcome != 'response' or any(not _sha256(s) for s in (identity, payload_sha, data_sha))
                or hashlib.sha256(data.encode()).hexdigest() != data_sha):
            raise ValueError('raw numeric reply content hash differs')
        response = json.loads(data)
        if (row['payload_sha256'] != payload_sha or response['model'] != b['model'] or row['payload']['model'] != b['model']
                or hashlib.sha256(canonical_json(row['payload']).encode()).hexdigest() != payload_sha):
            raise ValueError('raw numeric reply/payload/model binding differs')
        transport_rows.append({'sql_rowid': sql_rowid, 'wire_line': wire_line,
            'payload_sha256': payload_sha, 'cache_identity': identity})
        try:
            from utopia.models.models import parse_json_response
            body = parse_json_response(response['choices'][0]['message']['content'])
        except (ValueError, KeyError, IndexError, TypeError):
            continue
        if isinstance(body, dict) and 'overall_score' in body:
            proof = review_requests.get(identity)
            payload = row['payload']
            actual_seed = payload.get('seed', payload.get('extra_body', {}).get('seed'))
            schema = (payload.get('extra_body', {}).get('structured_outputs', {}).get('json')
                or payload.get('response_format', {}).get('json_schema', {}).get('schema'))
            if proof is None or proof['year'] != row['year'] or actual_seed != proof['seed'] or schema != task_schema:
                raise BoundaryUnsupported('numeric score lacks actual original phase3 review cache identity/schema proof')
            value = body['overall_score']
            if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= upper:
                raise BoundaryUnsupported('raw review score outside declared positive int projection')
            if task_identities is not None:
                from utopia.constants import IMPORTANT_NOTES
                task = proof['native_task']
                users = [m.get('content') for m in payload.get('messages', []) if m.get('role') == 'user']
                prefix = IMPORTANT_NOTES+'\n\n'
                if (len(users) != 1 or not isinstance(users[0], str) or not users[0].startswith(prefix)
                        or hashlib.sha256(users[0][len(prefix):].encode()).hexdigest() != task['prompt_sha256']
                        or digest(body) != task['parsed_response_sha256'] or int(value) != task['native_score']):
                    raise BoundaryUnsupported('raw review prompt/result differs from the actual identity-bound original task')
            by_year.setdefault(row['year'], []).append({'value': value, 'payload_sha256': payload_sha,
                'response_sha256': data_sha, 'cache_identity': identity, 'original_review_task': proof,
                'sql_rowid': sql_rowid, 'wire_line': wire_line})
    raw, indices, cohorts = native_values.clone(), [], []
    aggregation, semantic_ids, raw_reviews = [], [], []
    for entry in selected:
        shape = entry['shape']
        if len(shape) != 2 or max(score_column, count_column) >= shape[1]:
            raise BoundaryUnsupported('review boundary is not the declared numeric score/count matrix')
        original = native_values[entry['offset']:entry['offset']+entry['size']].reshape(shape)
        cohort = by_year.get(entry['year'], [])
        counts = original[:, count_column]
        if len(cohort) != int(counts.sum()) or any(c < 0 or c != int(c) for c in counts.tolist()):
            raise BoundaryUnsupported('actual raw review replies and native review counts do not correspond')
        if task_identities is not None:
            mapped, seen = {}, set()
            for reply in cohort:
                task = reply['original_review_task']['native_task']
                identity = {k: task[k] for k in ('year', 'conference_id', 'paper_id', 'reviewer_id')}
                key = canonical_json(identity)
                if key in seen:
                    raise BoundaryUnsupported('multiple raw responses claim one actual successful native review task')
                seen.add(key)
                mapped.setdefault((task['paper_id'], task['conference_id']), []).append((key, reply))
            claimed = set()
            for row, semantic_id in enumerate(entry['semantic_ids']):
                identity = json.loads(semantic_id)
                if set(identity) != {'paper_id', 'conference_id'}:
                    raise BoundaryUnsupported('review matrix must use exact paper/conference semantic row identities')
                key = identity['paper_id'], identity['conference_id']
                actual = sorted(mapped.get(key, []), key=lambda r: r[0])
                if len(actual) != counts[row]:
                    raise BoundaryUnsupported('actual raw reviewer identities do not match the exact native paper review count')
                if not actual:
                    if original[row, score_column] != 0:
                        raise BoundaryUnsupported('unreviewed native score is not its actual observed zero')
                    continue
                parsed_mean = sum(int(r['value']) for _, r in actual)/len(actual)
                if original[row, score_column] != parsed_mean:
                    raise BoundaryUnsupported('mean of original per-review integer parses differs from the actual native feature')
                target = entry['offset']+row*shape[1]+score_column
                source_indices = []
                for semantic, reply in actual:
                    claimed.add(semantic)
                    source_indices.append(len(native_values)+len(raw_reviews))
                    semantic_ids.append(semantic)
                    raw_reviews.append(reply['value'])
                aggregation.append({'target': target, 'sources': source_indices})
            if claimed != seen:
                raise BoundaryUnsupported('actual native review task has no exact represented semantic paper row')
            cohorts.append({'year': entry['year'], 'actual_replies': len(cohort),
                'reply_content_sha256': digest(sorted(cohort, key=lambda r: canonical_json(r['original_review_task']['native_task'])))})
            continue
        distinct = {r['value'] for r in cohort}
        if len(distinct) != 1:
            raise BoundaryUnsupported('heterogeneous or absent raw replies have no unique semantic row correspondence')
        value = next(iter(distinct))
        for row in range(shape[0]):
            if counts[row] == 0:
                if original[row, score_column] != 0:
                    raise BoundaryUnsupported('unreviewed native score is not its actual observed zero')
                continue
            if original[row, score_column] != math.trunc(value):
                raise BoundaryUnsupported('original int(raw reply) does not reproduce native review feature; extra transforms remain opaque')
            index = entry['offset'] + row*shape[1]+score_column
            raw[index] = value
            indices.append(index)
        cohorts.append({'year': entry['year'], 'uniform_raw_score': value, 'native_int_score': math.trunc(value),
            'actual_replies': len(cohort), 'reply_content_sha256': digest(cohort)})
    if set(by_year) != {e['year'] for e in selected}:
        raise BoundaryUnsupported('raw review years do not match represented review boundary')
    if before != (file_sha256(journal), file_sha256(wire)):
        raise ValueError('raw response evidence changed during read-only extraction')
    if task_identities is not None:
        raw = torch.cat((raw, raw.new_tensor(raw_reviews)))
        indices = list(range(len(native_values), len(raw)))
    contract = {'mechanism': mechanism, 'input_name': input_name, 'score_column': score_column,
        'count_column': count_column, 'upper': upper, 'native_parser': 'int-positive-truncation',
        'task_schema_sha256': digest(task_schema), 'original_task_seed_ctx': 'phase3_reviews'}
    if task_identities is not None:
        contract.update(native_boundary_size=len(native_values), raw_review_semantic_ids=semantic_ids,
            aggregation=aggregation, native_aggregation='mean-after-individual-original-int-parse')
    return raw, {'kind': 'positive-int-truncation-per-review-mean' if task_identities is not None else 'positive-int-truncation',
        'indices': indices, 'upper': upper,
        'contract': contract, 'evidence_layout': evidence_layout,
        'checkpoint_sha256': endpoint['checkpoint_sha256'], 'checkpoint_response_count': len(replies),
        'full_checkpoint_binding_sha256': digest(b),
        'transport_join': {'kind': 'unique-payload-sha256-bijection-in-sql-completion-order',
            'sql_rowids': sql_rowids, 'wire_lines_in_sql_order': [r['wire_line'] for r in transport_rows],
            'row_binding_sha256': digest(transport_rows)},
        'completion_provenance': completion_provenance,
        'journal': str(journal.resolve()), 'journal_sha256': before[0], 'wire': str(wire.resolve()),
        'wire_sha256': before[1], 'cohorts': cohorts,
        'correspondence': ('exact native year/conference/paper/reviewer identities; int EACH raw reply THEN mean; no imputed identities'
            if task_identities is not None else 'uniform actual reply cohort only; no heterogeneous averaging or imputed identities')}


def project_response(raw, projection, *, hard, temperature):
    result = raw.clone()
    indices = projection.get('indices', [])
    per_review = projection.get('kind') == 'positive-int-truncation-per-review-mean'
    if not indices:
        return result[:projection['contract']['native_boundary_size']] if per_review else result
    selected = raw[indices]
    upper = projection['upper']
    if not torch.isfinite(selected).all() or bool(((selected < 0) | (selected > upper)).any()):
        raise BoundaryUnsupported('predicted response outside declared native projection domain')
    if hard:
        result[indices] = torch.trunc(selected)
    else:
        levels = torch.arange(1, upper+1, dtype=raw.dtype)
        result[indices] = torch.sigmoid((selected[:, None]-levels[None, :])/temperature).sum(1)
    if per_review:
        contract = projection['contract']
        for group in contract['aggregation']:
            result[group['target']] = result[group['sources']].mean()
        return result[:contract['native_boundary_size']]
    return result


def response_replay(endpoint, layout, values, coordinates, declarations, *, hard, temperature):
    """Same registered tensor equations, with explicit learned opaque input ports."""
    ps = programs(endpoint)
    parameters = {name: {key: torch.tensor(value, dtype=DTYPE) for key, value in p['parameters'].items()} for name, p in ps.items()}
    for coordinate, declaration in zip(coordinates, declarations):
        if declaration['mechanism'] not in parameters:
            continue  # Its possible effect is ONLY the declared learned boundary, never a fabricated source derivative.
        path = declaration['path'].split('/')[1:]
        if path[:2] != ['program', 'parameters'] or len(path) < 3:
            raise ValueError('represented coordinate is not an actual tensor parameter')
        key = path[2].replace('~1', '/').replace('~0', '~')
        if len(path) == 3:
            parameters[declaration['mechanism']][key] = coordinate
        else:
            leaf = parameters[declaration['mechanism']][key].clone()
            leaf[tuple(int(v) for v in path[3:])] = coordinate
            parameters[declaration['mechanism']][key] = leaf
    overrides = {}
    for entry in layout:
        array = values[entry['offset']:entry['offset']+entry['size']].reshape(entry['shape'])
        if entry['canonical_to_actual']:
            inverse = np.argsort(entry['canonical_to_actual']).tolist()
            array = array[inverse]
        overrides[(entry['frame'], entry['input'])] = array
    memory, produced, frames = {}, {}, []
    for index, frame in enumerate(endpoint['trace']):
        name = frame['mechanism']
        inputs = {}
        for key, source in frame['input_sources'].items():
            if source['mechanism'] in ps and source['path'] == '/values':
                dependency = (source['mechanism'], source['port'], source['period'])
                if dependency not in produced:
                    raise BoundaryUnsupported('missing actual represented upstream dependency')
                inputs[key] = produced[dependency]
            else:
                inputs[key] = overrides[(index, key)]
        if name not in memory:
            memory[name] = {k: torch.tensor(v, dtype=DTYPE) for k, v in frame['state_before'].items()}
        outputs, memory[name] = execute_tensor_program(ps[name], inputs, parameters=parameters[name],
            state=memory[name], hard=hard, temperature=temperature)
        for port, tensor in outputs.items():
            produced[(name, port, frame['year'])] = tensor
        frames.append({'year': frame['year'], 'mechanism': name, 'outputs': outputs})
    return frames


def endpoint_decomposition(left, right, declarations, terms, *, temperature):
    if binding(left) != binding(right):
        raise ValueError('endpoint decomposition changes undeclared native controls')
    layout, z0, signature = boundary_layout(left)
    _, z1, other = boundary_layout(right)
    if signature != other:
        return {'status': 'unsupported-record-routing-or-shape-change', 'left_layout_sha256': signature,
            'right_layout_sha256': other, 'native_delta': right['native_loss']-left['native_loss'],
            'full_native_world_autograd': False}
    t0, t1 = [torch.tensor([p['coordinate_values'][d['id']] for d in declarations], dtype=DTYPE) for p in (left, right)]
    def value(theta, z, hard):
        return float(trace_objective(response_replay(left, layout, z, theta, declarations,
            hard=hard, temperature=temperature), terms).detach())
    s00, s10, s11 = value(t0, z0, False), value(t1, z0, False), value(t1, z1, False)
    h00, h11 = value(t0, z0, True), value(t1, z1, True)
    components = {'direct_soft': s10-s00, 'response_drift_soft': s11-s10,
        'hard_soft_gap_change': (h11-s11)-(h00-s00),
        'native_unrepresented_residual_change': (right['native_loss']-h11)-(left['native_loss']-h00)}
    delta = right['native_loss']-left['native_loss']
    return {'status': 'exact-endpoint-accounting', 'native_delta': delta, 'components': components,
        'sum': math.fsum(components.values()), 'accounting_error': math.fsum(components.values())-delta,
        'hard_represented_losses': [h00, h11], 'soft_represented_losses': [s00, s11],
        'boundary_numeric_max_drift': float((z1-z0).abs().max()),
        'endpoint_sha256s': [left['checkpoint_sha256'], right['checkpoint_sha256']],
        'scope': 'Conditional cross-endpoint replays, not new native counterfactual executions.',
        'full_native_world_autograd': False}


class NativeResponseOperator:
    """Identified local response map + unchanged compositional tensor equations."""
    def __init__(self, state):
        self.state = deepcopy(state)
        self._hash = digest(self.state)

    def _check(self):
        if digest(self.state) != self._hash:
            raise ValueError('response representation/temperature/provenance changed')

    @classmethod
    def fit(cls, endpoints, declarations, loss_spec, terms, *, temperatures=(1., .2, .05, .01),
            numeric_response_evidence=None, rank_rtol=1e-10):
        if len(endpoints) < 2 or not temperatures or any(type(t) not in (int, float) or not math.isfinite(t) or t <= 0 for t in temperatures):
            raise ValueError('distinct native calibration and explicit positive temperatures required')
        first = endpoints[0]
        if len({p['checkpoint_sha256'] for p in endpoints}) != len(endpoints):
            raise ValueError('duplicate physical calibration endpoint is not a replicate')
        if numeric_response_evidence is not None and (not isinstance(numeric_response_evidence, dict)
                or set(numeric_response_evidence) != {p['checkpoint_sha256'] for p in endpoints}):
            raise ValueError('numeric response evidence keys must be exactly the calibration checkpoints; no unused extras')
        if type(rank_rtol) not in (float, int) or not math.isfinite(rank_rtol) or rank_rtol <= 0:
            raise ValueError('response rank tolerance must be finite positive')
        layouts, raw_values, projections = [], [], []
        for endpoint in endpoints:
            verify_endpoint(endpoint, declarations, loss_spec)
            if binding(endpoint) != binding(first):
                raise ValueError('calibration source/model/corpus/initial world/noncoordinate design differs')
            layout, numeric, signature = boundary_layout(endpoint)
            if layouts and signature != layouts[0][1]:
                raise BoundaryUnsupported('calibration records/routing/shapes differ; no padding')
            layouts.append((layout, signature))
            if numeric_response_evidence is not None:
                raw, projection = raw_review_projection(endpoint, layout, numeric,
                    **numeric_response_evidence[endpoint['checkpoint_sha256']])
            else:
                raw, projection = numeric, {'kind': 'identity-post-native-boundary', 'indices': [], 'contract': {'parser': 'identity'}}
            if projections and {k: projection[k] for k in ('kind', 'indices', 'contract')} != {k: projections[0][k] for k in ('kind', 'indices', 'contract')}:
                raise BoundaryUnsupported('native parser correspondence changes across calibration')
            raw_values.append(raw)
            projections.append(projection)
        names = [c['id'] for c in declarations]
        controls = torch.tensor([[p['coordinate_values'][key] for key in names] for p in endpoints], dtype=DTYPE)
        center = controls.mean(0)
        design = torch.cat((controls.new_ones(len(endpoints), 1), controls-center), 1)
        singular = torch.linalg.svdvals(design)
        if int((singular > singular[0]*rank_rtol).sum()) != design.shape[1]:
            raise BoundaryUnsupported('response coordinates not independently identified by native interventions')
        targets = torch.stack(raw_values)
        weights = torch.linalg.lstsq(design, targets, driver='gelsd').solution
        state = {'schema': SCHEMA, 'declarations': deepcopy(declarations), 'loss_spec': deepcopy(loss_spec),
            'terms': deepcopy(terms), 'binding': binding(first), 'calibration': deepcopy(endpoints),
            'coordinate_names': names, 'center': center.tolist(), 'weights': weights.tolist(),
            'layout': layouts[0][0], 'layout_sha256': layouts[0][1], 'projection': projections[0],
            'raw_response_proofs': projections, 'numeric_response_evidence': deepcopy(numeric_response_evidence),
            'calibration_controls': controls.tolist(), 'raw_fit_rmse': float((design@weights-targets).square().mean().sqrt()),
            'temperature': float(temperatures[0]), 'temperature_selection': None,
            'derivative_scope': 'Autograd of a learned response boundary and declared native parse relaxation composed with original tensor institutions; not native/LLM pathwise.',
            'full_native_world_autograd': False, 'native_derivative_verified': False}
        candidates = []
        for temperature in temperatures:
            state['temperature'] = float(temperature)
            operator = cls(state)
            predicted = [float(operator.value(c)[0].detach()) for c in controls]
            errors = [v-p['native_loss'] for v, p in zip(predicted, endpoints)]
            candidates.append({'temperature': temperature, 'native_calibration_losses': [p['native_loss'] for p in endpoints],
                'predicted_calibration_losses': predicted, 'rmse': math.sqrt(math.fsum(e*e for e in errors)/len(errors))})
        selected = min(range(len(candidates)), key=lambda i: (candidates[i]['rmse'], i))
        state['temperature'] = float(candidates[selected]['temperature'])
        state['temperature_selection'] = {'rule': 'minimum native calibration loss RMSE; ties retain declared order',
            'candidates': candidates, 'selected_index': selected,
            'calibration_checkpoint_sha256s': [p['checkpoint_sha256'] for p in endpoints], 'unused_endpoints_seen': 0}
        return cls(state)

    def support(self, coordinates):
        from scipy.optimize import linprog
        points = np.array(self.state['calibration_controls'])
        target = torch.as_tensor(coordinates, dtype=DTYPE).detach().cpu().numpy()
        if target.shape != (points.shape[1],) or not np.isfinite(target).all():
            raise BoundaryUnsupported('nonfinite/wrong-dimensional response query')
        result = linprog(np.zeros(len(points)), A_eq=np.vstack((points.T, np.ones(len(points)))),
            b_eq=np.r_[target, 1.], bounds=(0., None), method='highs')
        if not result.success:
            raise BoundaryUnsupported('response query outside native calibration convex hull; no extrapolation')
        return result.x.tolist()

    def value(self, coordinates, *, freeze_boundary=False, hard=False):
        self._check()
        coordinates = torch.as_tensor(coordinates, dtype=DTYPE)
        hull = self.support(coordinates)
        center, weights = coordinates.new_tensor(self.state['center']), coordinates.new_tensor(self.state['weights'])
        raw = weights[0] + (coordinates-center)@weights[1:]
        z = project_response(raw, self.state['projection'], hard=hard, temperature=self.state['temperature'])
        if freeze_boundary:
            z = z.detach()
        frames = response_replay(self.state['calibration'][0], self.state['layout'], z, coordinates,
            self.state['declarations'], hard=hard, temperature=self.state['temperature'])
        return trace_objective(frames, self.state['terms']), {'hull_weights': hull}

    def backward(self, coordinates):
        coordinates = torch.tensor(coordinates, dtype=DTYPE, requires_grad=True)
        loss, support = self.value(coordinates)
        frozen, _ = self.value(coordinates, freeze_boundary=True)
        def gradient(value):
            g = torch.autograd.grad(value, coordinates, allow_unused=True)[0] if value.requires_grad else None
            return torch.zeros_like(coordinates) if g is None else g
        total, direct = gradient(loss), gradient(frozen)
        return {'coordinates': coordinates.detach().tolist(), 'represented_loss': float(loss.detach()),
            'gradient': total.tolist(), 'frozen_boundary_gradient': direct.tolist(),
            'learned_response_contribution': (total-direct).tolist(), 'support': support,
            'representation_sha256': self._hash, 'native_derivative_verified': False,
            'scope': self.state['derivative_scope'], 'full_native_world_autograd': False}

    def validate_unused(self, endpoint, *, atol=1e-3, rtol=1e-4):
        self._check()
        _tolerances(atol, rtol)
        if endpoint['checkpoint_sha256'] in {p['checkpoint_sha256'] for p in self.state['calibration']}:
            raise ValueError('unused verification endpoint was calibration data')
        verify_endpoint(endpoint, self.state['declarations'], self.state['loss_spec'])
        if binding(endpoint) != self.state['binding']:
            raise ValueError('unused endpoint changes undeclared native controls')
        _, _, signature = boundary_layout(endpoint)
        if signature != self.state['layout_sha256']:
            return {'status': 'unsupported-record-routing-or-shape-change', 'checkpoint_sha256': endpoint['checkpoint_sha256'],
                'native_loss': endpoint['native_loss'], 'predicted_loss': None, 'gradient': None}
        x = [endpoint['coordinate_values'][key] for key in self.state['coordinate_names']]
        try:
            prediction, _ = self.value(x)
        except BoundaryUnsupported as error:
            return {'status': 'unsupported-native-calibration-query', 'reason': str(error),
                'checkpoint_sha256': endpoint['checkpoint_sha256'], 'native_loss': endpoint['native_loss'],
                'predicted_loss': None, 'gradient': None}
        predicted = float(prediction.detach())
        error = abs(predicted-endpoint['native_loss'])
        return {'status': 'passed-unused-native-endpoint' if error <= atol+rtol*abs(endpoint['native_loss']) else 'failed-unused-native-fidelity',
            'checkpoint_sha256': endpoint['checkpoint_sha256'], 'coordinates': x, 'predicted_loss': predicted,
            'native_loss': endpoint['native_loss'], 'absolute_error': error, 'atol': atol, 'rtol': rtol,
            'representation_sha256': self._hash, 'full_native_world_autograd': False}

    def integrated_check(self, left, right, *, quadrature=128, atol=1e-2, rtol=1e-3):
        _tolerances(atol, rtol)
        if type(quadrature) is not int or not 16 <= quadrature <= 512:
            raise ValueError('bounded declared path quadrature required')
        validations = [self.validate_unused(p, atol=atol, rtol=rtol) for p in (left, right)]
        if any(v['status'].startswith('unsupported') for v in validations):
            return {'status': 'unsupported-native-endpoint-path', 'endpoint_checks': validations,
                'predicted_finite_delta': None, 'point_gradient': None}
        a, b = [np.array([p['coordinate_values'][key] for key in self.state['coordinate_names']]) for p in (left, right)]
        delta, distance = b-a, float(np.linalg.norm(b-a))
        if not distance:
            raise ValueError('distinct native coordinate endpoints required')
        nodes, weights = np.polynomial.legendre.leggauss(quadrature)
        integral, frozen = 0., 0.
        for node, weight in zip(nodes, weights):
            result = self.backward((a+(node+1)*.5*delta).tolist())
            integral += float(weight)*.5*float(np.dot(result['gradient'], delta))
            frozen += float(weight)*.5*float(np.dot(result['frozen_boundary_gradient'], delta))
        endpoint_delta = float((self.value(b)[0]-self.value(a)[0]).detach())
        actual_delta = right['native_loss']-left['native_loss']
        numerical_error = abs(integral-endpoint_delta)
        error = abs(integral-actual_delta)
        delta_agreement = numerical_error <= atol and error <= atol+rtol*abs(actual_delta)
        endpoint_agreement = all(v['status'] == 'passed-unused-native-endpoint' for v in validations)
        passed = delta_agreement and endpoint_agreement
        return {'status': 'passed-unused-native-finite-path-check' if passed else 'failed-unused-native-finite-path-fidelity',
            'predicted_finite_delta': integral, 'represented_endpoint_delta': endpoint_delta,
            'actual_native_delta': actual_delta, 'predicted_average_directional_derivative': integral/distance,
            'actual_native_secant': actual_delta/distance, 'frozen_boundary_predicted_finite_delta': frozen,
            'frozen_boundary_native_error': abs(frozen-actual_delta), 'response_aware_native_error': error,
            'representation_quadrature_error': numerical_error, 'quadrature': quadrature,
            'finite_delta_agreement': delta_agreement, 'absolute_endpoint_fidelity': endpoint_agreement,
            'point_gradient_at_midpoint': self.backward(((a+b)*.5).tolist()), 'endpoint_checks': validations,
            'atol': atol, 'rtol': rtol, 'representation_sha256': self._hash,
            'scope': 'Path integral of fitted-model autograd versus an unused finite native endpoint difference; NOT a native point Jacobian.',
            'native_derivative_verified': False, 'full_native_world_autograd': False}

    def save(self, path, *, verification_endpoints=()):
        self._check()
        value = {'schema': SCHEMA+'.saved', 'model': self.state, 'verification_endpoints': list(verification_endpoints),
            'representation_sha256': self._hash, 'module_sha256': file_sha256(Path(__file__))}
        value['content_sha256'] = digest(value)
        write_json_atomic(path, value, sort_keys=True, allow_nan=False)

    @classmethod
    def load(cls, path):
        value = json.loads(Path(path).read_text())
        if value['content_sha256'] != digest({k: v for k, v in value.items() if k != 'content_sha256'}):
            raise ValueError('saved response operator content changed')
        if value['module_sha256'] != file_sha256(Path(__file__)):
            raise ValueError('response representation source changed; explicit migration required')
        state = value['model']
        refitted = cls.fit(state['calibration'], state['declarations'], state['loss_spec'], state['terms'],
            temperatures=[c['temperature'] for c in state['temperature_selection']['candidates']],
            numeric_response_evidence=state['numeric_response_evidence'])
        if refitted.state != state or refitted._hash != value['representation_sha256']:
            raise ValueError('saved response fit/temperature/provenance does not reconstruct from native evidence')
        for endpoint in value['verification_endpoints']:
            refitted.validate_unused(endpoint)
        return refitted


def _tolerances(atol, rtol):
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in (atol, rtol)):
        raise ValueError('fidelity tolerances must be finite nonnegative scalars')
