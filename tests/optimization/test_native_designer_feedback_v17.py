"""SCRIPTED diagnostic fidelity; no institution recommendation or live inference."""
import json

from tests.optimization.test_native_authoring_ir import BINDING, request
from utopia.optimization.native_staged_author_v15 import initial_draft, transition, draft_summary


def apply(state, action):
    return transition(state, action, request(), binding_sha256='d' * 64, provider_binding=BINDING)


def factor():
    return {'id': 'arbitrary-factor', 'kind': 'bernoulli', 'choices': [
        {'id': str(index), 'operations': [], 'provenance': {'kind': 'SCRIPTED-only'}} for index in range(2)]}


def test_wrong_bernoulli_width_returns_exact_declared_shape_without_fixing_authored_values():
    state, receipt = apply(initial_draft(request()), {'tool': 'configure', 'factors': [factor()],
        'logits': {'arbitrary-factor': [.7, -.3]}})
    assert receipt['ok'] and not receipt['result']['validation']['valid']
    diagnostic = receipt['result']['validation']['errors'][0]['diagnostics'][0]
    assert diagnostic['factor_id'] == 'arbitrary-factor'
    assert diagnostic['factor_kind'] == 'bernoulli'
    assert diagnostic['expected_shape'] == [1] and diagnostic['actual_shape'] == [2]
    assert diagnostic['all_values_finite'] and not diagnostic['authored_value_changed_by_host']
    assert state['logits']['arbitrary-factor'] == [.7, -.3]
    assert draft_summary(state)['declared_factor_logit_shapes'][0]['expected_shape'] == [1]
    state, receipt = apply(state, {'tool': 'configure', 'logits': {'arbitrary-factor': [.7]}})
    assert receipt['ok'] and receipt['result']['validation']['valid']


def test_categorical_shape_is_choice_count_not_a_fixed_policy_menu():
    authored = factor(); authored['kind'] = 'categorical'
    state, receipt = apply(initial_draft(request()), {'tool': 'configure', 'factors': [authored],
        'logits': {'arbitrary-factor': [.7, -.3]}})
    assert receipt['result']['validation']['valid']
    assert draft_summary(state)['declared_factor_logit_shapes'][0]['expected_shape'] == [2]


def test_noop_source_edit_is_legal_but_explicitly_distinguished_from_document_change():
    body = request(); source = body['parent_system']['mechanisms'][0]['parameters']['code_artifact']['source']
    state = initial_draft(body)
    action = {'tool': 'edit', 'operations': [{'op': 'replace',
        'path': '/mechanisms/0/parameters/code_artifact/source', 'value': source}]}
    state, receipt = apply(state, action)
    assert receipt['ok'] and not receipt['result']['literal_document_changed']
    assert 'legal retention' in receipt['result']['edit_effect_notice']
    action['operations'][0]['value'] += '\n# SCRIPTED literal difference, not scientific merit\n'
    state, receipt = apply(state, json.loads(json.dumps(action, sort_keys=True)))
    assert receipt['ok'] and receipt['result']['literal_document_changed']
    assert receipt['result']['edit_effect_notice'] is None
