"""Audit-only fixtures; not native measurements or Qwen response evidence."""
from copy import deepcopy
import hashlib
import json
import sqlite3

import pytest

from scripts.analyze_native_response_fidelity_v8 import inventory, transport_proof
from utopia.constants import IMPORTANT_NOTES
from utopia.runtime.checkpointing import canonical_json
from utopia.system.native_kernel import _hash


def wire_fixture(tmp_path):
    (tmp_path/'cache').mkdir()
    events, wires = [], []
    with sqlite3.connect(tmp_path/'cache/responses.sqlite') as db:
        db.execute('CREATE TABLE metadata(binding TEXT)')
        db.execute('INSERT INTO metadata VALUES (?)', (canonical_json({'model': 'scripted-fixture'}),))
        db.execute('CREATE TABLE replies(payload_sha TEXT,outcome TEXT,data TEXT,data_sha TEXT)')
        for year in range(1, 7):
            text = f'Actual fixture review prompt {year}'
            payload = {'model': 'scripted-fixture', 'messages': [
                {'role': 'user', 'content': IMPORTANT_NOTES+'\n\n'+text}]}
            sha = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
            data = canonical_json({'model': 'scripted-fixture', 'choices': []})
            db.execute('INSERT INTO replies VALUES (?,?,?,?)',
                (sha, 'response', data, hashlib.sha256(data.encode()).hexdigest()))
            wires.append({'year': year, 'payload_sha256': sha, 'payload': payload})
            identity = 'fixture-message-'+str(year)
            events.extend([
                {'event_type': 'native.system.context_delivered', 'actor_ids': ['actor-1'],
                    'payload': {'message': {'message_id': identity, 'received_year': year}}},
                {'event_type': 'native.system.review_context_used', 'year': year,
                    'payload': {'uses': [{'actor_id': 'actor-1', 'message_ids': [identity], 'prompt_sha256': _hash(text)}]},
                    'provenance': {'input_event_ids': ['fixture-source-event']}}])
    (tmp_path/'wire.jsonl').write_text(''.join(json.dumps(w)+'\n' for w in wires))
    return events


def test_audit_joins_actual_prompt_hashes_deliveries_and_physical_reply_bytes_without_mutation(tmp_path):
    events = wire_fixture(tmp_path)
    before = inventory(tmp_path)
    report = transport_proof(tmp_path, events)
    assert report['review_prompt_uses_verified'] == 6
    assert report['fresh_physical_responses'] == 6
    assert report['actual_actor_message_deliveries'] == 6
    assert inventory(tmp_path) == before
    forged = deepcopy(events)
    forged[1]['payload']['uses'][0]['prompt_sha256'] = 'forged'
    with pytest.raises(ValueError, match='do not match'):
        transport_proof(tmp_path, forged)
    forged = deepcopy(events)
    forged[1]['payload']['uses'][0]['actor_id'] = 'unaddressed-actor'
    with pytest.raises(ValueError, match='undelivered'):
        transport_proof(tmp_path, forged)


def test_audit_rejects_forged_response_content_even_with_original_payload(tmp_path):
    events = wire_fixture(tmp_path)
    with sqlite3.connect(tmp_path/'cache/responses.sqlite') as db:
        db.execute("UPDATE replies SET data='forged' WHERE rowid=1")
    with pytest.raises(ValueError, match='content hash'):
        transport_proof(tmp_path, events)


@pytest.mark.parametrize('reorder', ['wire-request-order', 'sql-completion-order'])
def test_audit_order_independent_payload_join_preserves_actual_sql_rowids(tmp_path, reorder):
    events = wire_fixture(tmp_path)
    if reorder == 'wire-request-order':
        wire = tmp_path/'wire.jsonl'
        wire.write_text('\n'.join(reversed(wire.read_text().splitlines()))+'\n')
        expected_rowids = list(range(1, 7))
    else:
        with sqlite3.connect(tmp_path/'cache/responses.sqlite') as db:
            db.execute('UPDATE replies SET rowid=100-rowid')
        expected_rowids = list(range(94, 100))
    before = inventory(tmp_path)
    report = transport_proof(tmp_path, events)
    assert report['review_prompt_uses_verified'] == 6
    assert report['transport_join']['sql_rowids'] == expected_rowids
    assert report['transport_join']['wire_lines_in_sql_order'] == list(range(6, 0, -1))
    assert inventory(tmp_path) == before


@pytest.mark.parametrize('tamper', ['duplicate-wire', 'duplicate-sql-sha', 'missing-wire', 'missing-sql',
    'mismatching-sha', 'tampered-payload', 'tampered-response'])
def test_audit_payload_bijection_rejects_duplicate_missing_mismatched_or_tampered_rows(tmp_path, tamper):
    events = wire_fixture(tmp_path)
    wire = tmp_path/'wire.jsonl'
    wires = [json.loads(s) for s in wire.read_text().splitlines()]
    if tamper == 'duplicate-wire': wires.append(deepcopy(wires[0]))
    elif tamper == 'missing-wire': wires.pop()
    elif tamper == 'mismatching-sha': wires[0]['payload_sha256'] = 'a'*64
    elif tamper == 'tampered-payload': wires[0]['payload']['messages'][0]['content'] = 'tampered'
    else:
        with sqlite3.connect(tmp_path/'cache/responses.sqlite') as db:
            if tamper == 'duplicate-sql-sha':
                db.execute('UPDATE replies SET payload_sha=? WHERE rowid=2', (wires[0]['payload_sha256'],))
            elif tamper == 'missing-sql': db.execute('DELETE FROM replies WHERE rowid=2')
            else: db.execute("UPDATE replies SET data='tampered' WHERE rowid=1")
    wire.write_text(''.join(json.dumps(row)+'\n' for row in wires))
    with pytest.raises(ValueError):
        transport_proof(tmp_path, events)
