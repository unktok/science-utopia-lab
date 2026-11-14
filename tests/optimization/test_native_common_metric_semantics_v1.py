"""Prospective description coverage only; no new measurement/world/inference."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from tests.optimization.test_native_authoring_ir import request
from tests.optimization.test_native_bounded_author_context_v45 import frame
from utopia.optimization.common_content_observer import make_contract
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.optimization import native_objective_view
from utopia.optimization.native_bounded_author_context_v45 import archive_entries
from utopia.optimization.native_objective_view import loss_arithmetic
from utopia.optimization.native_staged_author_v15 import initial_draft, protocol_binding

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def forbid_code_and_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('definition checks must not execute code or use a network')
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)
    monkeypatch.setattr('requests.sessions.Session.request', forbidden)


def utility_request():
    body = request()
    body['loss_spec'] = json.loads((ROOT/'research/objectives/losses/native-common-content-utility-v1.json').read_text())
    return body


@pytest.mark.parametrize('metric', ['native.common_content_score_sum', 'native.common_content_utility_sum'])
def test_existing_content_metrics_receive_source_owned_not_invented_definitions(metric):
    body = utility_request(); body['loss_spec']['per_run']['terms'][0]['metric_id'] = metric
    before = deepcopy(body['loss_spec']); view = loss_arithmetic(before)
    description = view['measurement_definitions'][metric]
    assert view['metrics_without_text_definition'] == []
    assert view['archived_loss_spec_sha256'] == loss_spec_sha256(before)
    assert view['per_run'] == before['per_run'] and view['across_seeds'] == before['across_seeds']
    assert 'accepted native decision occurrence' in description and 'preserving repeated accepted records' in description
    assert 'arithmetic mean rating' in description and 'final_score are not inputs' in description
    assert 'not scientific truth' in description
    assert ('subtract 3' in description) == metric.endswith('utility_sum')
    assert not view['candidate_policy_supplied'] and not view['extra_eligibility_constraint']
    assert body['loss_spec'] == before


def test_definition_agrees_with_unchanged_common_observer_contract():
    provider = {'model': 'SCRIPTED', 'model_digest': 'SCRIPTED'}
    contract = make_contract(source_commit='a'*40, provider=provider,
        backend={**provider, 'ollama_version': 'SCRIPTED'}, maximum_posts=3)
    assert contract['input_fields'] == ['title', 'abstract', 'topics']
    assert contract['pooling'] == 'arithmetic mean, all critics required'
    assert contract['utility'] == 'sum over accepted decision records of (common mean score - 3)'
    definition = loss_arithmetic(utility_request()['loss_spec'])['measurement_definitions']['native.common_content_utility_sum']
    assert 'original title, abstract and topics' in definition and 'subtract 3' in definition


@pytest.mark.parametrize('value', [-2., 0., 13.333333333333332])
def test_description_addition_does_not_change_loss_or_missing_value_semantics(value):
    spec = utility_request()['loss_spec']; view = loss_arithmetic(spec)
    measurement = {'run_id': 'SCRIPTED', 'metrics': {
        'native.common_content_utility_sum': {'status': 'measured', 'value': value}}}
    projected = {**deepcopy(spec), 'per_run': view['per_run'], 'across_seeds': view['across_seeds']}
    assert evaluate_loss(projected, [measurement]) == evaluate_loss(spec, [measurement])
    assert evaluate_loss(spec, [measurement])['loss'] == -value
    measurement['metrics']['native.common_content_utility_sum'] = {'status': 'unavailable', 'value': None}
    assert evaluate_loss(projected, [measurement])['loss'] is None


def test_bounded_frame_includes_definition_without_promoting_registry_prose_or_mutating_archive():
    body = utility_request(); marker = 'SCRIPTED_REGISTRY_IS_NOT_AN_EXTRA_REQUIREMENT'
    body['loss_spec']['interpretation'] = marker
    before = deepcopy(body); prompt, messages = frame(body, initial_draft(body), [])
    view = json.loads(prompt)['loss_arithmetic']
    definition = view['measurement_definitions']['native.common_content_utility_sum']
    assert definition in messages[1]['content']
    assert definition not in messages[0]['content']
    assert marker not in json.dumps(messages)
    assert archive_entries(body, [])['archive/request.json']['value'] == before
    assert body == before


def test_unknown_metrics_remain_explicitly_undefined_and_view_source_is_bound():
    spec = utility_request()['loss_spec']; spec['per_run']['terms'][0]['metric_id'] = 'SCRIPTED.unregistered'
    view = loss_arithmetic(spec)
    assert view['measurement_definitions'] == {}
    assert view['metrics_without_text_definition'] == ['SCRIPTED.unregistered']
    assert protocol_binding()['objective_view_source_sha256'] == hashlib.sha256(
        Path(native_objective_view.__file__).read_bytes()).hexdigest()
