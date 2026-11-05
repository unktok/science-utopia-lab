"""Explicit non-executable annotations, not permissive unknown-field repair."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from tests.optimization.test_native_authoring_ir import BINDING, request
from tests.optimization.test_native_staged_author_v15 import Model, author, apply
from utopia.optimization.native_staged_author_v15 import (
    ACTION_SCHEMA, initial_draft, replay_staged_generation, turn_response_schema)


@pytest.mark.parametrize('action', [
    {'tool': 'inspect', 'path': ''},
    {'tool': 'edit', 'operations': [{'op': 'add', 'path': '/metadata/SCRIPTED', 'value': 42}]},
    {'tool': 'splice', 'path': '/mechanisms/0/parameters/code_artifact/source', 'offset': 0, 'delete': 0, 'text': '# SCRIPTED\n'},
    {'tool': 'configure', 'factors': []}, {'tool': 'validate'},
    {'tool': 'finish', 'rationale': 'SCRIPTED explicit retention'}])
def test_declared_notes_do_not_change_the_literal_action_effect_or_spoof_provenance(action):
    state = initial_draft(request())
    annotated = {**deepcopy(action), 'rationale': 'SCRIPTED reasoning, not a measured result',
        'provenance': {'author': 'local-model', 'claimed_verified': True}}
    Draft202012Validator(ACTION_SCHEMA).validate(annotated)
    plain_state, plain_receipt = apply(state, action)
    new_state, new_receipt = apply(state, annotated)
    assert new_receipt['ok'] and new_state == plain_state
    assert new_receipt['document_after_sha256'] == plain_receipt['document_after_sha256']
    assert new_receipt['untrusted_author_annotations'] == {key: annotated[key] for key in ('rationale', 'provenance')}
    assert 'claimed_verified' not in str(new_state)
    if new_receipt['definition']:
        provenance = new_receipt['definition']['provenance']
        assert provenance['kind'] == 'automatic-local-LLM-staged-v15'
        assert 'claimed_verified' not in provenance
        Draft202012Validator(turn_response_schema(1)).validate(annotated)
    if action['tool'] == 'configure':
        assert new_receipt['result']['configured_fields'] == ['factors']


@pytest.mark.parametrize('action', [
    {'tool': 'configure', 'rationale': 'SCRIPTED note only'},
    {'tool': 'edit', 'operations': [], 'provenance': {}},
    {'tool': 'inspect', 'path': '', 'rationale': 7},
    {'tool': 'inspect', 'path': '', 'provenance': 'not an object'},
    {'tool': 'inspect', 'path': '', 'provenance': {str(i): i for i in range(17)}},
    {'tool': 'inspect', 'path': '', 'unlisted': 'not an allowed annotation'}])
def test_annotations_do_not_supply_missing_action_fields_or_accept_other_unknown_keys(action):
    assert list(Draft202012Validator(ACTION_SCHEMA).iter_errors(action))
    state = initial_draft(request())
    unchanged, receipt = apply(state, action)
    assert unchanged == state and not receipt['ok']


def test_changed_model_action_with_notes_cold_replays_without_stripping_or_redispatch(tmp_path):
    edit = {'tool': 'edit', 'operations': [{'op': 'add', 'path': '/metadata/SCRIPTED_new', 'value': 3}],
        'rationale': 'SCRIPTED exact change', 'provenance': {'author': 'local-model'}}
    finish = {'tool': 'finish', 'rationale': 'SCRIPTED technical boundary', 'provenance': {'untrusted': 'author claim'}}
    model = Model([edit, finish])
    result = author(model, tmp_path, max_steps=2)(request())
    assert 'generation_failure' not in result
    folder = next(tmp_path.glob('generation-*'))
    assert replay_staged_generation(folder, expected_provider_binding=BINDING) == result
    assert len(model.calls) == 2
