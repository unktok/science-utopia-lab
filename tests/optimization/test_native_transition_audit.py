import json
import sqlite3

from scripts.audit_native_transition_v3 import compare_direction_records
from utopia.system.code_mechanisms import sha


def fixture_wire(root, *, reverse=False, changed=False):
    root.mkdir()
    (root / 'replies').mkdir()
    rows = []
    for index in range(2):
        history = 'Accepted fixture' if changed and index == 0 else 'Rejected fixture'
        prompt = f'You are a university researcher at institution_{index:04d}.\nNow, you are trying to decide the research direction of your next project.\n{history}\n## Your Funding Situation\nFunding fixture'
        payload = {'seed': index + 42, 'messages': [{'role': 'user', 'content': prompt}],
            'response_format': {'json_schema': {'name': 'research_direction_selection'}}}
        rows.append({'year': 3, 'payload': payload, 'payload_sha256': sha(payload)})
    db = sqlite3.connect(root / 'replies/responses.sqlite')
    db.execute('CREATE TABLE replies(payload_sha TEXT,data TEXT)')
    for row in rows:
        reply = {'choices': [{'message': {'content': 'Changed QA reply' if changed and row['payload']['seed'] == 42 else 'QA reply'}}]}
        db.execute('INSERT INTO replies VALUES(?,?)', (row['payload_sha256'], json.dumps(reply)))
    db.commit()
    db.close()
    ordered = list(reversed(rows)) if reverse else rows
    (root / 'wire-requests.jsonl').write_text('\n'.join(json.dumps(r) for r in ordered))


def test_actual_author_activity_matching_ignores_http_arrival_order(tmp_path):
    left, right = tmp_path / 'left', tmp_path / 'right'
    fixture_wire(left)
    fixture_wire(right, reverse=True, changed=True)
    result = compare_direction_records(left, right, author_ids=['institution_0000_researcher_0', 'institution_0001_researcher_0'])
    assert result['unidentified_requests'] == [0, 0]
    assert result['left_only'] == result['right_only'] == 0
    assert all(p['same_request_seed'] for p in result['pairs'])
    assert [p['publication_history_view_changed'] for p in result['pairs']] == [True, False]
    assert [p['reply_content_changed'] for p in result['pairs']] == [True, False]
