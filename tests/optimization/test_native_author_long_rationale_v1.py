"""Prospective annotation contract only; no actual model/world/code execution."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from tests.optimization.test_native_authoring_ir import ALPHA, BINDING, request
from tests.optimization.test_native_staged_author_v15 import Model, apply, author
from utopia.optimization.native_designer_tools_v25 import (
    AUTHORING_RECOVERY, BOUNDED_AUTHORING, LEGACY_HISTORY, tool_specifications,
)
from utopia.optimization.native_staged_author_v15 import (
    ACTION_SCHEMA, EDITOR_ACTION_SCHEMA, PLAN_ACTION_SCHEMA, host_action_schema,
    initial_draft, protocol_binding, replay_staged_generation,
)
from utopia.system.design_patch import digest


@pytest.fixture(autouse=True)
def forbid_execution_and_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('annotation checks must not execute code or use a network')
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)
    monkeypatch.setattr('requests.sessions.Session.request', forbidden)


def note(length):
    return ('SCRIPTED 非実行の説明\n"\\' * length)[:length]


def write_action(body):
    return {'tool': 'write_file', 'filename': 'code/' + ALPHA + '.py',
        'content': body['parent_system']['mechanisms'][0]['parameters']['code_artifact']['source']
            + '\n# SCRIPTED literal edit, not a scientific improvement\n'}


@pytest.mark.parametrize('length', [4096, 4097, 16384])
def test_long_note_is_retained_verbatim_without_changing_literal_edit(length):
    body = request(); state = initial_draft(body); action = write_action(body)
    annotated = {**deepcopy(action), 'rationale': note(length)}
    before = deepcopy(annotated)
    Draft202012Validator(ACTION_SCHEMA).validate(annotated)
    plain_state, plain = apply(state, action, body)
    changed, receipt = apply(state, annotated, body)
    assert plain['ok'] and receipt['ok'] and changed == plain_state
    assert annotated == before
    assert receipt['untrusted_author_annotations'] == {'rationale': annotated['rationale']}
    assert changed['document']['mechanisms'][0]['parameters']['code_artifact']['source'] == action['content']
    assert receipt['document_after_sha256'] == plain['document_after_sha256']


@pytest.mark.parametrize('profile', [LEGACY_HISTORY, AUTHORING_RECOVERY, BOUNDED_AUTHORING])
def test_sender_host_and_specialized_schema_views_share_new_note_contract(profile):
    action = {**write_action(request()), 'rationale': note(4097)}
    for schema in (ACTION_SCHEMA, EDITOR_ACTION_SCHEMA, host_action_schema(profile)):
        Draft202012Validator(schema).validate(action)
        assert 'maxLength' not in schema['$defs']['rationale']
    assert 'maxLength' not in PLAN_ACTION_SCHEMA['$defs']['rationale']
    tool = next(t for t in tool_specifications(conversation_profile=profile)
        if t['function']['name'] == 'write_file')
    arguments = {k: v for k, v in action.items() if k != 'tool'}
    Draft202012Validator(tool['function']['parameters']).validate(arguments)
    assert tool['function']['parameters']['properties']['rationale'] == ACTION_SCHEMA['$defs']['rationale']


@pytest.mark.parametrize('bad', [
    {'content': 7}, {'filename': 'code/absent.py'}, {'rationales': 'unknown field'},
    {'rationale': 7},
])
def test_long_note_does_not_repair_bad_operands_or_unknown_fields(bad):
    body = request(); state = initial_draft(body)
    action = {**write_action(body), 'rationale': note(4097), **bad}
    before = deepcopy(action)
    changed, receipt = apply(state, action, body)
    assert not receipt['ok'] and changed == state and action == before
    assert receipt['errors']
    assert all('maxLength' not in error['message'] for error in receipt['errors'])


def test_scripted_long_note_edit_and_explicit_finish_cold_replay_exactly(tmp_path):
    body = request(); edit = {**write_action(body), 'rationale': note(4097)}
    model = Model([edit, {'tool': 'finish', 'rationale': 'SCRIPTED explicit submission'}])
    result = author(model, tmp_path, max_steps=2)(body)
    assert 'generation_failure' not in result and len(model.calls) == 2
    folder = next(tmp_path.glob('generation-*'))
    step = json.loads((folder/'step-00.completed.json').read_text())
    assert step['model_reply']['output'] == edit
    assert step['transition']['untrusted_author_annotations']['rationale'] == edit['rationale']
    assert replay_staged_generation(folder, expected_provider_binding=BINDING) == result


def test_old_ceiling_is_a_different_bound_contract_not_relabelled_history():
    old = deepcopy(ACTION_SCHEMA); old['$defs']['rationale']['maxLength'] = 4096
    action = {**write_action(request()), 'rationale': note(4097)}
    assert not Draft202012Validator(old).is_valid(action)
    assert Draft202012Validator(ACTION_SCHEMA).is_valid(action)
    binding = protocol_binding()
    assert binding['action_schema_sha256'] == digest(ACTION_SCHEMA) != digest(old)
    assert ACTION_SCHEMA['$defs']['rationale']['type'] == 'string'
    assert ACTION_SCHEMA['$defs']['rationale']['minLength'] == 1
    assert ACTION_SCHEMA['$defs']['provenance']['maxProperties'] == 16
