"""SCRIPTED conditional ABI feedback; no provider, container or native probe."""
from copy import deepcopy

import pytest
from jsonschema.exceptions import ValidationError

from tests.optimization.test_native_authoring_ir import request, BINDING
from utopia.optimization.native_contract_notices import contract_notices, notice_summary
from utopia.optimization.native_staged_author_v15 import initial_draft, transition, draft_summary
from utopia.system.code_mechanisms import CodeExecutionError, validate_context, validate_code_result


def document(schema=None):
    value = request()['parent_system']
    artifact = value['mechanisms'][0]['parameters']['code_artifact']
    artifact['inputs'] = {'scores': {'type': 'array'} if schema is None else schema}
    return value


def test_payload_array_notice_predicts_nonempty_record_failure_without_executing_source():
    value = document(); before = deepcopy(value)
    notices = contract_notices(value)
    assert value == before and len(notices) == 1
    notice = notices[0]
    assert notice['path'] == '/mechanisms/0/parameters/code_artifact/inputs/scores'
    assert notice['runtime_object'] == 'one record payload'
    assert not notice['changes_validity'] and not notice['authored_value_changed_by_host']
    assert not notice['native_execution_performed']
    artifact = value['mechanisms'][0]['parameters']['code_artifact']
    context = {'inputs': {'scores': [{'payload': {'records': [], 'values': []}}]},
        'state': {}, 'random_seed': 42}
    with pytest.raises(ValidationError, match="not of type 'array'"):
        validate_context(artifact, context)  # Validates data only; source raises if executed.
    context['inputs']['scores'] = []
    validate_context(artifact, context)  # Empty delivery remains executable, not a new veto.


@pytest.mark.parametrize('schema', [{}, {'type': 'object'}, {'type': ['object', 'array']},
    {'type': 'object', 'properties': {'values': {'type': 'array'}}},
    {'anyOf': [{'type': 'array'}, {'type': 'object'}]}, False,
    {'type': ['array', 'array']}, {'type': {'invalid': 'schema'}}])
def test_no_claim_of_general_schema_satisfiability_or_nested_array_rejection(schema):
    assert contract_notices(document(schema)) == []


def test_output_and_state_warnings_are_conditional_not_technical_rejections():
    body = request(); state = initial_draft(body)
    state, edited = transition(state, {'tool': 'edit', 'operations': [{'op': 'replace',
        'path': '/mechanisms/0/parameters/code_artifact/state_schema', 'value': {'type': 'array'}}]},
        body, binding_sha256='d' * 64, provider_binding=BINDING)
    assert edited['ok'] and edited['result']['validation']['valid']
    after, result = transition(state, {'tool': 'finish', 'rationale': 'SCRIPTED dormant node, no execution'},
        body, binding_sha256='d' * 64, provider_binding=BINDING)
    assert result['ok'] and result['result']['valid'] and result['definition'] is not None
    assert after == state  # No change to legality or authored bytes.
    notice = result['result']['execution_contract_notices']['notices'][0]
    assert notice['runtime_object'] == 'returned state'
    assert draft_summary(state)['execution_contract_notices']['notices'] == [notice]
    artifact = deepcopy(state['document']['mechanisms'][0]['parameters']['code_artifact'])
    with pytest.raises(CodeExecutionError, match='contract'):
        validate_code_result(artifact, {'outputs': {}, 'state': {}})
    artifact['state_schema'] = {'type': 'object'}
    artifact['outputs'] = {'out': {'type': 'array'}}
    value = document({'type': 'object'})
    value['mechanisms'][0]['parameters']['code_artifact'] = artifact
    assert contract_notices(value)[0]['path'].endswith('/outputs/out')
    validate_code_result(artifact, {'outputs': {'out': []}, 'state': {}})


def test_process_wrapped_code_and_pointer_escaping_preserve_exact_owner():
    value = document(); node = value['mechanisms'][0]
    node['parameters']['code_artifact']['inputs'] = {'a/b~c': {'type': ['array', 'number']}}
    value['mechanisms'] = [{'mechanism_id': 'wrapper', 'implementation': 'native.process.activity.v1',
        'parameters': {'delegate': node}}]
    notice = contract_notices(value)[0]
    assert notice['mechanism_id'] == 'wrapper' and notice['executed_mechanism_id'] == node['mechanism_id']
    assert notice['path'] == '/mechanisms/0/parameters/delegate/parameters/code_artifact/inputs/a~1b~0c'


def test_notices_are_bounded_and_never_assume_other_implementations_follow_code_abi():
    value = document()
    artifact = value['mechanisms'][0]['parameters']['code_artifact']
    artifact['inputs'] = {str(index): {'type': 'array'} for index in range(12)}
    summary = notice_summary(value)
    assert summary['total_count'] == 12 and summary['included_count'] == 8 and summary['omitted_count'] == 4
    assert not summary['complete'] and summary['omission']
    value['mechanisms'][0]['version'] = 2
    assert contract_notices(value) == []
    value['mechanisms'][0]['version'] = 1
    value['mechanisms'][0]['implementation'] = 'arbitrary.other.abi'
    assert contract_notices(value) == []
    assert contract_notices({'mechanisms': [None, {'implementation': 'code.python.v1'}]}) == []
