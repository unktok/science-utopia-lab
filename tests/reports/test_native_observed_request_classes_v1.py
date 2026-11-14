import hashlib
import json

import pytest

from scripts.reports.native_observed_request_classes_v1 import groups, sequence, world_seed, AUDITS
from utopia.optimization.native_numeric_designer import save
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


def numeric_dispatch(tmp_path, *, seed=777):
    p = {'schema': 'scienceutopia.native-parameter-comparator.v1.plan', 'content_sha256': 'a' * 64,
        'objectives': ['throughput', 'content-utility'], 'generations': 3}
    a = {'schema': 'scienceutopia.native-parameter-comparator-audit.v1'}
    w = {'identity': 'original', 'objective': 'throughput', 'generation': 1, 'system': {'SCRIPTED': True},
        'physical_proof': {'seed': seed}}
    path = tmp_path / 'search/throughput/generation-1/started.json'
    save(path, {'plan_sha256': p['content_sha256'], 'objective': w['objective'], 'generation': w['generation'],
        'suggestion': {'suggestion_id': w['identity'], 'candidate': w['system']}, 'seed': seed})
    return p, a, w


def test_numeric_seed_uses_actual_sealed_original_dispatch_not_a_hardcoded_default(tmp_path):
    p, a, w = numeric_dispatch(tmp_path)
    assert world_seed(tmp_path, p, a, w) == 777
    w['physical_proof'] = {'status': 'pre-response-journal-failure'}
    assert world_seed(tmp_path, p, a, w) == 777
    assert 'scienceutopia.native-workflow-objective-loop-audit.v1' in AUDITS
    assert world_seed(tmp_path, p, {'schema': 'scienceutopia.native-workflow-objective-loop-audit.v1'},
        {'seed': 991}) == 991
    assert 'scienceutopia.native-workflow-fixed-evaluation-audit.v1' in AUDITS
    assert world_seed(tmp_path, p, {'schema': 'scienceutopia.native-workflow-fixed-evaluation-audit.v1'},
        {'seed': 72107}) == 72107


@pytest.mark.parametrize('case', ['unknown-objective', 'wrong-generation', 'wrong-system',
    'wrong-identity', 'wrong-plan', 'physical-seed', 'missing-dispatch'])
def test_numeric_seed_does_not_fabricate_missing_or_mismatched_evidence(tmp_path, case):
    p, a, w = numeric_dispatch(tmp_path)
    if case == 'unknown-objective': w['objective'] = '../untrusted'
    elif case == 'wrong-generation': w['generation'] = True
    elif case == 'wrong-system': w['system'] = {'changed': True}
    elif case == 'wrong-identity': w['identity'] = 'other'
    elif case == 'wrong-plan': p['content_sha256'] = 'b' * 64
    elif case == 'physical-seed': w['physical_proof']['seed'] = 61001
    elif case == 'missing-dispatch': (tmp_path / 'search/throughput/generation-1/started.json').unlink()
    with pytest.raises((ValueError, FileNotFoundError)): world_seed(tmp_path, p, a, w)
