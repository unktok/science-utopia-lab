"""Actual installed SDK/HTTPX request construction, never network/model inference."""
import json

import httpx
from openai import OpenAI
import pytest

from utopia.optimization.native_scientist_transport_v1 import (
    configure_existing_client, contract, record_value, require_record, validate)
from utopia.system.design_patch import clone, digest


@pytest.mark.parametrize('bad', [None, True, 0, -1, float('nan'), float('inf'), '900', 3601])
def test_invalid_operator_read_allowance_is_not_coerced_or_unbounded(bad):
    with pytest.raises(ValueError):
        contract(read_seconds=bad)


def test_real_sdk_sends_new_timeout_but_identical_body_through_existing_wrappers():
    sent, recorded = [], []
    def transport(request):
        sent.append({'body': request.content, 'timeout': clone(request.extensions['timeout']),
            'read_header': request.headers['x-stainless-read-timeout'],
            'retry_header': request.headers['x-stainless-retry-count']})
        return httpx.Response(200, json={'id': 'SCRIPTED', 'object': 'chat.completion', 'created': 0,
            'model': 'qwen3:8b', 'choices': [{'index': 0, 'message': {'role': 'assistant',
                'content': '{}'}, 'finish_reason': 'stop'}]})
    with OpenAI(api_key='SCRIPTED-not-a-real-key', base_url='http://127.0.0.1:11434/v1',
            timeout=120, max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(transport))) as client:
        original = client.chat.completions.create
        def recorded_callback(**payload):
            recorded.append(clone(payload)); return original(**payload)
        client.chat.completions.create = recorded_callback
        payload = {'model': 'qwen3:8b', 'messages': [{'role': 'user', 'content': 'SCRIPTED'}],
            'max_tokens': 768, 'seed': 42, 'temperature': .7, 'reasoning_effort': 'none'}
        client.chat.completions.create(**payload)
        identity = id(client)
        applied = configure_existing_client(client, contract(read_seconds=900))
        client.chat.completions.create(**payload)
        assert id(client) == identity and client.chat.completions.create is recorded_callback
    assert len(sent) == len(recorded) == 2 and recorded == [payload, payload]
    assert sent[0]['body'] == sent[1]['body']
    assert sent[0]['timeout'] == dict.fromkeys(('connect', 'read', 'write', 'pool'), 120)
    assert sent[1]['timeout'] == {'connect': 10, 'read': 900, 'write': 30, 'pool': 30}
    assert sent[1]['read_header'] == '900' and sent[1]['retry_header'] == '0'
    assert not applied['client_object_replaced'] and not applied['completion_callback_replaced']
    assert 'timeout' not in json.loads(sent[1]['body'])


def test_sdk_timeout_remains_unknown_failure_and_is_never_retried():
    sent = []
    def transport(request):
        sent.append(request)
        raise httpx.ReadTimeout('SCRIPTED unknown completion', request=request)
    with OpenAI(api_key='SCRIPTED', base_url='http://127.0.0.1:11434/v1', max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(transport))) as client:
        configure_existing_client(client, contract(read_seconds=900))
        from openai import APITimeoutError
        with pytest.raises(APITimeoutError):
            client.chat.completions.create(model='qwen3:8b', messages=[{'role': 'user', 'content': 'SCRIPTED'}])
    assert len(sent) == 1


@pytest.mark.parametrize('kind', ['retry', 'endpoint'])
def test_adapter_refuses_changed_endpoint_or_existing_retry_policy(kind):
    with OpenAI(api_key='SCRIPTED', max_retries=1 if kind == 'retry' else 0,
            base_url='http://127.0.0.1:9999/v1' if kind == 'endpoint' else 'http://127.0.0.1:11434/v1') as client:
        with pytest.raises(ValueError):
            configure_existing_client(client, contract(read_seconds=900))


def test_application_record_binds_operator_profile_not_candidate_parameters():
    value = contract(read_seconds=900)
    cache = {'model': 'qwen3:8b', 'model_revision': 'a' * 64}
    args = dict(source='b' * 40, system_fingerprint='c' * 64, seed=42, run_id='SCRIPTED', cache_binding=cache)
    applied = {'http_timeout_seconds': value['http_timeout_seconds'], 'sdk_max_retries': 0,
        'client_object_replaced': False, 'completion_callback_replaced': False, 'request_body_modified': False}
    record = record_value(value, **args, applied=applied)
    record['content_sha256'] = digest(record)
    assert require_record(record, value, **args) == record
    with pytest.raises(ValueError):
        require_record(record, contract(read_seconds=600), **args)
    with pytest.raises(ValueError):
        require_record(record, value, **{**args, 'run_id': 'different-world'})
