"""Literal partial-prefix diagnostics never turn a prior answer into a new one."""
import hashlib
import json

import pytest

from scripts.reports.native_workflow_stop_diagnostic_v1 import prefix
from utopia.system.design_patch import clone, digest


def wires():
    payloads = [{'model': 'SCRIPTED', 'messages': [{'content': str(i)}]} for i in range(4)]
    return [{'year': 1, 'payload': p, 'payload_sha256': digest(p)} for p in payloads]


def replies(values, *, provider='old'):
    result = []
    for i, w in enumerate(values):
        body = json.dumps({'id': provider + str(i), 'usage': {'completion_tokens': 1},
            'choices': [{'message': {'content': str(i)}, 'finish_reason': 'stop'}]})
        result.append((w['payload_sha256'], 'response', body, hashlib.sha256(body.encode()).hexdigest()))
    return result


def test_equal_partial_inputs_and_choices_do_not_fill_unknown_last_response():
    prior = wires(); current = clone(prior[:3])
    result = prefix(current, replies(current[:2], provider='new'), prior, replies(prior))
    assert result['equal_full_request_prefix_count'] == 3
    assert result['equal_committed_literal_choice_prefix_count'] == 2
    assert result['stopped_requests']['wire_inputs_without_committed_reply'] == 1
    assert result['prior_matching_request_ordinals'] == [2]
    assert len(result['prior_matching_committed_responses']) == 1
    for k in ('new_missing_response_recovered_or_filled', 'whole_world_equivalence_claimed', 'timeout_cause_identified'):
        assert result[k] is False


def test_literal_request_change_is_not_scrubbed_to_enlarge_equal_prefix():
    prior = wires(); current = clone(prior[:3])
    current[1]['payload']['messages'][0]['content'] = 'different scientific value'
    current[1]['payload_sha256'] = digest(current[1]['payload'])
    result = prefix(current, replies(current[:2]), prior, replies(prior))
    assert result['equal_full_request_prefix_count'] == 1
    assert result['equal_committed_literal_choice_prefix_count'] == 1


@pytest.mark.parametrize('side', ['current', 'prior'])
def test_corrupt_original_provider_body_is_rejected(side):
    ws = wires(); a, b = replies(ws[:2]), replies(ws)
    target = a if side == 'current' else b
    h, outcome, data, sha = target[0]; target[0] = (h, outcome, data + ' ', sha)
    with pytest.raises(ValueError, match='provider response differs'):
        prefix(ws[:3], a, ws, b)


def test_empty_prefix_is_not_claimed_to_explain_a_transport_failure():
    ws = wires()
    with pytest.raises(ValueError, match='actual stopped HTTP prefix'):
        prefix([], [], ws, replies(ws))
