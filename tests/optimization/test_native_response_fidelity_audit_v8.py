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
