"""SCRIPTED transport time allowance; never timed model performance evidence."""
import json

import pytest
import requests

from utopia.optimization.native_designer_decoding_v24 import decoding_contract
from utopia.optimization.native_designer_wire import post, wire_record


@pytest.mark.parametrize('role', ['planner', 'editor'])
def test_staged_read_allowance_is_declared_without_enlarging_token_or_step_budgets(role):
    from utopia.optimization.native_designer_decoding_v24 import STAGED_MAX_STEPS
    contract = decoding_contract('staged-v15', role=role)
    assert contract['http_timeout_seconds'] == [10, 900]
    assert contract['max_tokens'] == 8192 and STAGED_MAX_STEPS == 8
    assert 'http_timeout_seconds' not in decoding_contract('one-shot-v14')


def test_single_timed_out_post_retains_exact_wire_and_timeout_without_retry():
    calls = []
    payload = {'messages': [{'role': 'user', 'content': 'SCRIPTED\n\\literal'}]}
    record = {}

    class Session:
        def post(self, endpoint, **kwargs):
            calls.append((endpoint, kwargs))
            assert kwargs['timeout'] == (10, 900)
            assert kwargs['data'] == wire_record(payload, {})['request_wire_utf8'].encode()
            raise requests.exceptions.ReadTimeout('SCRIPTED no completed response')

    with pytest.raises(requests.exceptions.ReadTimeout, match='SCRIPTED'):
        post(Session(), 'SCRIPTED endpoint', payload, {}, record, timeout=(10, 900))
    assert len(calls) == 1
    assert record['http_timeout_seconds'] == [10, 900]
    assert json.loads(record['request_wire_utf8']) == payload
    assert 'response_payload' not in record and 'raw_http_response' not in record


def test_legacy_wire_timeout_remains_300():
    class Session:
        def post(self, endpoint, **kwargs):
            assert kwargs['timeout'] == 300
            return 'SCRIPTED response'

    record = {}
    assert post(Session(), 'SCRIPTED endpoint', {}, {}, record) == 'SCRIPTED response'
    assert record['http_timeout_seconds'] == 300
