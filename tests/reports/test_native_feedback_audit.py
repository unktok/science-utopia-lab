import hashlib
import json
import sqlite3

import pytest

from scripts.audit_native_feedback_v2 import wire_summary
from utopia.runtime.checkpointing import canonical_json


def recorded(tmp_path):
    (tmp_path / 'replies').mkdir()
    payload = {'model': 'fixed-model', 'messages': [{'role': 'user', 'content': 'advisory-feedback exploration_weight=0.7'}]}
    digest = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
    data = '{"actual_response":true}'
    db = sqlite3.connect(tmp_path / 'replies/responses.sqlite')
    db.execute('CREATE TABLE replies (payload_sha TEXT,outcome TEXT,data TEXT,data_sha TEXT)')
    db.execute('INSERT INTO replies VALUES (?,?,?,?)', (digest, 'response', data, hashlib.sha256(data.encode()).hexdigest()))
    db.commit(); db.close()
    wire = tmp_path / 'wire-requests.jsonl'
    wire.write_text(json.dumps({'year': 2, 'payload': payload, 'payload_sha256': digest}) + '\n')
    return wire


def test_actual_inputs_and_completed_reply_hashes_match(tmp_path):
    recorded(tmp_path)
    result = wire_summary(tmp_path, needle='advisory-feedback', required=True)
    assert result['actual_requests'] == 1 and result['contexts_by_year'] == {'2': 1}


def test_corrupt_actual_request_is_rejected(tmp_path):
    wire = recorded(tmp_path)
    row = json.loads(wire.read_text()); row['payload']['model'] = 'changed'
    wire.write_text(json.dumps(row) + '\n')
    with pytest.raises(ValueError, match='request payload hash'):
        wire_summary(tmp_path, needle='advisory-feedback', required=True)


def test_missing_wire_does_not_become_invented_input_evidence(tmp_path):
    assert wire_summary(tmp_path, needle='institution', required=False) == {'recorded': False}
    with pytest.raises(ValueError, match='journal required'):
        wire_summary(tmp_path, needle='institution', required=True)


def test_request_not_in_completed_journal_is_rejected(tmp_path):
    recorded(tmp_path)
    db = sqlite3.connect(tmp_path / 'replies/responses.sqlite'); db.execute('DELETE FROM replies'); db.commit(); db.close()
    with pytest.raises(ValueError, match='completed response-cache inputs differ'):
        wire_summary(tmp_path, needle='institution', required=True)
