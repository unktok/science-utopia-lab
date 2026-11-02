"""Synthetic provenance/unit tests only: no native or model execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest
import torch

from tests.optimization.test_native_response_fidelity_v8 import numerical_endpoint_not_native
from utopia.agents.base_agent import PaperReview
from utopia.constants import IMPORTANT_NOTES
from utopia.optimization.native_response_fidelity import (
    BoundaryUnsupported, NativeResponseOperator, boundary_layout, raw_review_projection,
    project_response, make_response_completion_receipt,
)
from utopia.runtime.checkpointing import canonical_json, write_portable_checkpoint
from utopia.system.design_patch import digest
from utopia.system.native_review_identity import EVENT, SCHEMA
from utopia.utils.data_utils import file_sha256
from utopia.utils.seeding import derive_seed


def semantic_journal(tmp_path, *, scores=(3.75, 4.25, 5.75), production=False, reverse_records=False,
                     reverse_wire=False, reverse_sql=False):
    """Explicit synthetic task capture; never labelled actual world evidence."""
    endpoint = numerical_endpoint_not_native(0.)
    endpoint['system']['mechanisms'].append({'mechanism_id': 'world.review', 'implementation': 'native.phase.review.v1'})
    endpoint['system_fingerprint'] = digest(endpoint['system'])
    endpoint['world'].update(source_commit='synthetic-source', model_digest='synthetic-model', corpus_sha256='synthetic-corpus', seed=42)
    binding = {'cell': endpoint['system_fingerprint'], 'seed': 42, 'model': 'synthetic', 'model_revision': 'synthetic-model',
        'corpus_sha256': 'synthetic-corpus', 'science_config': {'source_commit': 'synthetic-source'}}
    if production:
        checkpoint = tmp_path/'simulation/checkpoints/native-design/portable_checkpoint_year_1.json.gz'
        journal, wire = tmp_path/'replies/responses.sqlite', tmp_path/'wire-requests.jsonl'
    else:
        checkpoint = tmp_path/'checkpoints/portable_checkpoint_year_1.json.gz'
        journal, wire = tmp_path/'cache/responses.sqlite', tmp_path/'wire.jsonl'
    journal.parent.mkdir(parents=True)
    tasks, wires, sql, papers = [], [], [], []
    # Native collection order deliberately does NOT equal semantic order.
    assignments = [('paper-b', 'reviewer-z'), ('paper-a', 'reviewer-y'), ('paper-a', 'reviewer-x')]
    review_map = {}
    for i, ((paper, reviewer), score) in enumerate(zip(assignments, scores)):
        text = f'Synthetic original review of {paper} by {reviewer}'
        body = {'overall_score': score, 'justification': 'unit test only'}
        review = {'reviewer_id': reviewer, 'arxiv_id': paper, 'conference_id': 'conference-1',
            'year': 1, 'overall_score': int(score), 'justification': 'unit test only', 'review_time': 100.}
        review_map.setdefault(paper, []).append(review)
        tasks.append({'item_index': i, 'year': 1, 'reviewer_id': reviewer, 'paper_id': paper,
            'conference_id': 'conference-1', 'prompt_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'parsed_response_sha256': digest(body), 'native_score': int(score), 'native_review_sha256': digest(review)})
        seed = derive_seed(42, 'phase3_reviews', 1, i, 0)
        payload = {'model': 'synthetic', 'seed': seed, 'messages': [{'role': 'user', 'content': IMPORTANT_NOTES+'\n\n'+text}],
            'extra_body': {'structured_outputs': {'json': PaperReview.model_json_schema()}}}
        sha = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
        identity = hashlib.sha256(canonical_json({'binding': binding, 'seed_ctx': ('phase3_reviews', 1),
            'item_index': i, 'attempt': 0, 'seed': seed}).encode()).hexdigest()
        data = canonical_json({'model': 'synthetic', 'choices': [{'message': {'content': canonical_json(body)}}]})
        sql.append((identity, sha, 'response', data, hashlib.sha256(data.encode()).hexdigest()))
        wires.append({'year': 1, 'payload_sha256': sha, 'payload': payload})
    for paper, reviews in review_map.items():
        papers.append({'id': paper, 'review_history': [{'year': 1, 'conference': 'conference-1', 'reviews': reviews}]})
    with sqlite3.connect(journal) as db:
        db.execute('CREATE TABLE metadata(binding TEXT)')
        db.execute('INSERT INTO metadata VALUES (?)', (canonical_json(binding),))
        db.execute('CREATE TABLE replies(identity TEXT,payload_sha TEXT,outcome TEXT,data TEXT,data_sha TEXT)')
        db.executemany('INSERT INTO replies VALUES (?,?,?,?,?)', reversed(sql) if reverse_sql else sql)
    wire.write_text(''.join(canonical_json(w)+'\n' for w in (reversed(wires) if reverse_wire else wires)))
    saved = {'portable': {'contract': {'binding': binding}, 'response_cache_count': len(scores)},
        'paper_tracker': {'papers': papers}, 'native_system': {'events': [{'event_type': EVENT, 'year': 1,
            'provenance': {'mechanism_id': 'world.review'}, 'payload': {'schema': SCHEMA, 'year': 1,
                'tasks': tasks, 'tasks_sha256': digest(tasks)}}]}}
    write_portable_checkpoint(checkpoint, saved)
    endpoint.update(checkpoint=str(checkpoint), checkpoint_sha256=file_sha256(checkpoint), response_cache_count=len(scores))
    records = [{'paper_id': p, 'conference_id': 'conference-1'} for p in sorted(review_map, reverse=reverse_records)]
    values = [[sum(r['overall_score'] for r in review_map[p['paper_id']])/len(review_map[p['paper_id']]),
        len(review_map[p['paper_id']])] for p in records]
    frame = endpoint['trace'][0]
    frame['records'] = records
    frame['inputs']['features'] = values
    frame['outputs']['utility'] = [r[0] for r in values]
    endpoint['native_loss'] = -sum(r[0] for r in values)
    return endpoint, journal, wire, saved


def extract(endpoint, journal, wire):
    layout, z, _ = boundary_layout(endpoint)
    raw, projection = raw_review_projection(endpoint, layout, z, journal=journal, wire=wire,
        mechanism='math', input_name='features')
    return z, raw, projection


@pytest.mark.parametrize('production', [False, True])
@pytest.mark.parametrize('reverse_wire,reverse_sql,reverse_records', [(False, False, False), (True, False, True), (False, True, True), (True, True, False)])
def test_heterogeneous_reviews_exact_semantic_join_int_before_mean_and_concurrent_orders(
        tmp_path, production, reverse_wire, reverse_sql, reverse_records):
    endpoint, journal, wire, _ = semantic_journal(tmp_path, production=production,
        reverse_wire=reverse_wire, reverse_sql=reverse_sql, reverse_records=reverse_records)
    z, raw, proof = extract(endpoint, journal, wire)
    assert proof['kind'] == 'positive-int-truncation-per-review-mean'
    assert raw.tolist() == [4.5, 2., 3., 1., 5.75, 4.25, 3.75]
    assert project_response(raw, proof, hard=True, temperature=.1).tolist() == z.tolist()
    # Averaging raw paper-a scores before int would produce 5, NOT native4.5.
    assert int((4.25+5.75)/2) != z[0]
    assert proof['contract']['raw_review_semantic_ids'] == [canonical_json({'year': 1,
        'conference_id': 'conference-1', 'paper_id': p, 'reviewer_id': r}) for p, r in
        [('paper-a', 'reviewer-x'), ('paper-a', 'reviewer-y'), ('paper-b', 'reviewer-z')]]
    raw.requires_grad_()
    soft = project_response(raw, proof, hard=False, temperature=.2)
    gradient, = torch.autograd.grad(soft.sum(), raw)
    assert all(g > 0 for g in gradient[4:])
    assert gradient[[0, 2]].tolist() == [0., 0.]


@pytest.mark.parametrize('tamper', ['duplicate-task', 'missing-task', 'wrong-reviewer', 'wrong-paper',
    'wrong-prompt', 'wrong-response', 'wrong-native-score', 'wrong-archive', 'untrusted-source',
    'duplicate-event', 'wrong-task-hash', 'wrong-year', 'wrong-boundary-paper', 'wrong-count', 'mean-before-int'])
def test_heterogeneous_adapter_rejects_incomplete_or_ambiguous_semantic_proof(tmp_path, tamper):
    endpoint, journal, wire, saved = semantic_journal(tmp_path)
    event = saved['native_system']['events'][0]
    tasks = event['payload']['tasks']
    if tamper == 'duplicate-task': tasks[1].update(paper_id=tasks[0]['paper_id'], reviewer_id=tasks[0]['reviewer_id'])
    elif tamper == 'missing-task': tasks.pop()
    elif tamper == 'wrong-reviewer': tasks[0]['reviewer_id'] = 'foreign-reviewer'
    elif tamper == 'wrong-paper': tasks[0]['paper_id'] = 'foreign-paper'
    elif tamper == 'wrong-prompt': tasks[0]['prompt_sha256'] = 'a'*64
    elif tamper == 'wrong-response': tasks[0]['parsed_response_sha256'] = 'a'*64
    elif tamper == 'wrong-native-score': tasks[0]['native_score'] += 1
    elif tamper == 'wrong-archive': saved['paper_tracker']['papers'][0]['review_history'][0]['reviews'][0]['overall_score'] += 1
    elif tamper == 'untrusted-source': event['provenance']['mechanism_id'] = 'math'
    elif tamper == 'duplicate-event': saved['native_system']['events'].append(deepcopy(event))
    elif tamper == 'wrong-year': event['year'] = 2
    elif tamper == 'wrong-boundary-paper': endpoint['trace'][0]['records'][0]['paper_id'] = 'foreign-paper'
    elif tamper == 'wrong-count': endpoint['trace'][0]['inputs']['features'][0][1] = 3.
    elif tamper == 'mean-before-int':
        endpoint['trace'][0]['inputs']['features'][0][0] = 5.
        endpoint['trace'][0]['outputs']['utility'][0] = 5.
    event['payload']['tasks_sha256'] = 'a'*64 if tamper == 'wrong-task-hash' else digest(tasks)
    write_portable_checkpoint(Path(endpoint['checkpoint']), saved)
    endpoint['checkpoint_sha256'] = file_sha256(Path(endpoint['checkpoint']))
    with pytest.raises((BoundaryUnsupported, ValueError)):
        extract(endpoint, journal, wire)


def test_packed_raw_operator_fit_backward_and_semantic_reload_without_native_execution(tmp_path, monkeypatch):
    monkeypatch.setattr('utopia.optimization.native_response_fidelity.verify_endpoint', lambda *a: None)
    declarations = [{'id': 'advice', 'mechanism': 'opaque', 'path': '/advice', 'lower': -1., 'upper': 1., 'quantum': None}]
    terms = [{'mechanism': 'math', 'output': 'utility', 'coefficient': -1.}]
    points, evidence = [], {}
    for i, theta in enumerate([-.25, 0., .25]):
        endpoint, journal, wire, _ = semantic_journal(tmp_path/str(i), scores=tuple(s+theta for s in (3.75, 4.25, 5.75)),
            reverse_records=bool(i % 2), reverse_sql=bool(i % 2))
        endpoint['coordinate_values'] = {'advice': theta}
        points.append(endpoint)
        evidence[endpoint['checkpoint_sha256']] = {'journal': str(journal), 'wire': str(wire),
            'mechanism': 'math', 'input_name': 'features'}
    model = NativeResponseOperator.fit(points, declarations, {}, terms,
        temperatures=[.2], numeric_response_evidence=evidence)
    result = model.backward([0.])
    assert result['gradient'][0] < 0
    assert result['frozen_boundary_gradient'] == [0.]
    path = tmp_path/'operator.json'
    model.save(path)
    restored = NativeResponseOperator.load(path)
    assert restored.backward([0.]) == result


@pytest.mark.parametrize('production', [False, True])
def test_completion_receipt_supports_only_exact_supported_native_layout_pairs(tmp_path, production):
    from types import SimpleNamespace
    endpoint, journal, wire, saved = semantic_journal(tmp_path, production=production)
    cache = SimpleNamespace(path=journal, binding=saved['portable']['contract']['binding'],
        committed_count=lambda: 3, committed_prefix_identity=lambda: {})
    receipt = make_response_completion_receipt(endpoint, cache, wire, run_manifest_sha256='a'*64)
    assert receipt['journal_sha256'] == file_sha256(journal)
    with pytest.raises(ValueError, match='layout pair'):
        make_response_completion_receipt(endpoint, cache, tmp_path/'foreign.jsonl', run_manifest_sha256='a'*64)
