import hashlib
import json

import pytest

from scripts.reports.native_observed_request_classes_v1 import groups, sequence
from utopia.system.design_patch import digest


def wire(text='literal', seed=1):
    payload = {'model': 'fixed', 'messages': [{'role': 'user', 'content': text}], 'seed': seed}
    return {'payload': payload, 'payload_sha256': digest(payload)}


def reply(w, content='same', created=1):
    body = json.dumps({'choices': [{'message': {'role': 'assistant', 'content': content}, 'finish_reason': 'stop'}], 'created': created})
    return w['payload_sha256'], 'response', body, hashlib.sha256(body.encode()).hexdigest()


def test_full_payloads_remain_literal_but_provider_envelopes_are_separate():
    w = wire(); a = sequence([w], [reply(w)]); b = sequence([w], [reply(w, created=2)])
    assert a['ordered_full_request_payload_sha256'] == b['ordered_full_request_payload_sha256']
    assert a['ordered_literal_response_choices_sha256'] == b['ordered_literal_response_choices_sha256']
    assert a['ordered_full_provider_body_hashes_sha256'] != b['ordered_full_provider_body_hashes_sha256']
    for changed in (wire('different'), wire(seed=2)):
        assert sequence([changed], [])['ordered_full_request_payload_sha256'] != a['ordered_full_request_payload_sha256']


def test_uncommitted_inputs_remain_visible_and_order_is_required():
    a, b = wire('a'), wire('b')
    result = sequence([a, b], [reply(b)])
    assert result['wire_inputs_without_committed_reply'] == 1
    with pytest.raises(ValueError, match='ordered original'):
        sequence([a, b], [reply(b), reply(a)])
    with pytest.raises(ValueError, match='request hash'):
        sequence([{'payload': a['payload'], 'payload_sha256': 'wrong'}], [])
    row = list(reply(a)); row[-1] = 'wrong'
    with pytest.raises(ValueError, match='provider response'):
        sequence([a], [row])


def test_equal_input_does_not_imply_equal_model_response():
    w = wire()
    rows = [{'identity': name, 'seed': 1, 'status': 'complete', 'requests': sequence([w], [reply(w, content=text)])}
            for name, text in [('a', 'one'), ('b', 'two')]]
    g = groups(rows)
    assert len(g) == 1 and g[0]['physical_ids'] == ['a', 'b']
    assert not g[0]['all_literal_response_choices_equal']


def test_failed_prefixes_and_different_world_seeds_are_not_pooled():
    w = wire(); s = sequence([w], [reply(w)])
    rows = [{'identity': name, 'seed': seed, 'status': status, 'requests': s}
            for name, seed, status in [('a', 1, 'complete'), ('b', 2, 'complete'), ('c', 1, 'failed')]]
    g = groups(rows)
    assert [r['physical_ids'] for r in g] == [['a'], ['b']]
    with pytest.raises(ValueError, match='unique physical'):
        groups(rows+[rows[0]])
