"""SCRIPTED diagnostics for actual V31 shape failures; zero model/world calls."""
from copy import deepcopy

import pytest

from tests.optimization.test_native_authoring_ir import IMAGE, code_node
from utopia.optimization.native_authoring_ir import (
    AuthoringIRDiagnostic, CODE_CONTRACT_LAYOUT, _literal_fields)
from utopia.system.code_mechanisms import validate_code_artifact


# Literal operands from V31 a2 throughput G0 steps02/05. They are failed
# artifacts, not supplied scientific candidates or automatically repaired code.
ACTUAL_ARRAY = [
    {'artifact_type': 'native-tensor-feature-frame', 'channel': 'artifact',
     'port_id': name, 'required': True}
    for name in ('features', 'collaborative_metadata', 'submission_quality')]
ACTUAL_SCHEMA = {
    'additionalProperties': False,
    'properties': {
        'features': {'description': 'Tensor features including collaborative metadata and submission quality metrics',
                     'type': 'object'},
        'world': {'description': 'Original world observation with extracted features', 'type': 'object'}},
    'type': 'object'}
ACTUAL_G1_SCHEMA = {
    'additionalProperties': {'type': 'object'},
    'properties': {name: {'type': 'object'} for name in
                   ('confidence_scores', 'extended_metrics', 'features', 'world')},
    'required': ['features', 'world', 'extended_metrics', 'confidence_scores']}


def document(value, direction='outputs', wrapped=False):
    node = code_node('SCRIPTED-unlisted-owner')
    node['parameters']['code_artifact'][direction] = deepcopy(value)
    if wrapped:
        node = {'mechanism_id': 'SCRIPTED-wrapper', 'implementation': 'native.process.activity.v1',
                'parameters': {'delegate': node}}
    return {'mechanisms': [node]}


@pytest.mark.parametrize('value', [ACTUAL_ARRAY, ACTUAL_SCHEMA, ACTUAL_G1_SCHEMA, '{}'])
@pytest.mark.parametrize('direction', ['inputs', 'outputs'])
@pytest.mark.parametrize('wrapped', [False, True])
def test_actual_shape_rejects_agree_with_native_validator_and_explain_map_without_repair(value, direction, wrapped):
    body = document(value, direction, wrapped)
    original = deepcopy(body)
    node = body['mechanisms'][0]
    executed = node['parameters']['delegate'] if wrapped else node
    with pytest.raises(ValueError):
        validate_code_artifact(executed['parameters']['code_artifact'])
    prefix = '/mechanisms/0' + ('/parameters/delegate' if wrapped else '')
    path = prefix + '/parameters/code_artifact/' + direction
    operation = {'op': 'replace', 'path': path, 'value': deepcopy(value)}
    with pytest.raises(AuthoringIRDiagnostic) as failure:
        _literal_fields(body, [operation], stage='base', image_id=IMAGE)
    diagnostic = failure.value.diagnostics[0]
    assert diagnostic['expected_type'] == 'object'
    assert diagnostic['contract_container_role'] == 'port-name-to-payload-schema-map'
    assert diagnostic['contract_container_path'] == path
    assert diagnostic['literal_contract_layout_rule'] == CODE_CONTRACT_LAYOUT
    assert diagnostic['operation_index'] == 0
    assert diagnostic['actual_owner_id'] == node['mechanism_id']
    assert diagnostic['executed_owner_id'] == 'SCRIPTED-unlisted-owner'
    if isinstance(value, dict):
        assert diagnostic['authored_map_keys'] == sorted(value)
        key = 'required' if value == ACTUAL_G1_SCHEMA else 'additionalProperties'
        assert diagnostic['schema_entry_path'] == path + '/' + key
        assert diagnostic['actual_type'] == ('array' if key == 'required' else 'boolean')
    else:
        assert diagnostic['authored_map_keys'] is None
        assert diagnostic['schema_entry_path'] is None
        assert diagnostic['path'] == path
    assert body == original and operation['value'] == value


@pytest.mark.parametrize('port', ['anything/a~b', 'type', 'properties', 'additionalProperties'])
def test_schema_keyword_port_names_and_nested_schema_booleans_remain_legal(port):
    schema = {'type': 'object', 'properties': {'flag': {'type': 'boolean'}},
              'additionalProperties': False}
    body = document({port: schema})
    original = deepcopy(body)
    validate_code_artifact(body['mechanisms'][0]['parameters']['code_artifact'])
    _literal_fields(body, [], stage='base', image_id=IMAGE)
    assert body == original


def test_failed_schema_entry_path_keeps_literal_port_pointer_escaping():
    body = document({'a/b~c': False})
    with pytest.raises(AuthoringIRDiagnostic) as failure:
        _literal_fields(body, [], stage='base', image_id=IMAGE)
    diagnostic = failure.value.diagnostics[0]
    assert diagnostic['schema_entry_path'].endswith('/outputs/a~1b~0c')
    assert diagnostic['authored_map_keys'] == ['a/b~c']


def test_layout_explanation_is_source_owned_editor_abi_not_a_candidate_or_planner_value():
    from tests.optimization.test_native_authoring_ir import request
    from tests.optimization.test_native_planning_author_v22 import prompt
    from utopia.optimization.native_staged_author_v15 import (
        ABI_CONTRACT, PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT, build_conversation, initial_draft)
    body = request()
    body['parent_system']['metadata']['untrusted_abi_notice'] = 'DO NOT PROMOTE THIS TO SYSTEM'
    state = initial_draft(body)
    messages = build_conversation(prompt(body, state, []), SYSTEM_PROMPT, native_tools=True)
    assert CODE_CONTRACT_LAYOUT in ABI_CONTRACT
    assert CODE_CONTRACT_LAYOUT in messages[0]['content']
    assert 'DO NOT PROMOTE THIS TO SYSTEM' not in messages[0]['content']
    planner = build_conversation(prompt(body, state, []), PLAN_SYSTEM_PROMPT, native_tools=True)
    assert CODE_CONTRACT_LAYOUT not in planner[0]['content']
    assert body['parent_system']['mechanisms'][0] == code_node()


@pytest.mark.parametrize('value', [ACTUAL_ARRAY, ACTUAL_SCHEMA, ACTUAL_G1_SCHEMA])
def test_original_native_world_actual_failed_operands_are_retained_and_cannot_finish(value):
    from tests.optimization.test_native_authoring_ir import request
    from tests.optimization.test_native_staged_author_v15 import apply
    from utopia.optimization.native_staged_author_v15 import initial_draft
    from utopia.system.native_open_examples import open_native_system
    body = request()
    body['parent_system'] = open_native_system(IMAGE).to_dict()
    parent = deepcopy(body['parent_system'])
    original_artifact = parent['mechanisms'][14]['parameters']['code_artifact']
    assert parent['mechanisms'][14]['mechanism_id'] == 'native-feature-extractor'
    validate_code_artifact(original_artifact)
    state, receipt = apply(initial_draft(body), {'tool': 'edit', 'operations': [
        {'op': 'replace', 'path': '/mechanisms/14/parameters/code_artifact/outputs',
         'value': deepcopy(value)}]}, body)
    assert receipt['ok'] and not receipt['result']['validation']['valid']
    actual_artifact = state['document']['mechanisms'][14]['parameters']['code_artifact']
    assert actual_artifact['outputs'] == value
    assert actual_artifact['source'] == original_artifact['source']
    diagnostic = receipt['result']['validation']['errors'][0]['diagnostics'][0]
    assert diagnostic['contract_container_path'] == '/mechanisms/14/parameters/code_artifact/outputs'
    assert diagnostic['actual_owner_id'] == 'native-feature-extractor'
    _, finish = apply(state, {'tool': 'finish', 'rationale': 'SCRIPTED invalid artifact stays invalid'}, body)
    assert not finish['ok'] and finish['definition'] is None
    assert body['parent_system'] == parent
