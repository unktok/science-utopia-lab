"""Read-only ABI discovery checks; no generated policy, model or native execution."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from utopia.system import SystemSpec, MechanismSpec, PortSpec, MechanismFamily, ChannelKind
from utopia.system.design_patch import clone
from utopia.system.native_capability_catalog import native_capability_catalog, native_capability_index
from utopia.system.native_kernel import NativeScienceKernel
from utopia.system.native_researcher_work import (
    IMPLEMENTATION, REQUEST, RESPONSE, validate_work_node, validate_work_request,
)
from utopia.system.runtime import GraphRuntimeError, DeliveredValue


def work_request():
    return {'schema': REQUEST, 'request_id': 'SCRIPTED-shape-check', 'actor_id': 'existing-actor',
        'instruction': 'SCRIPTED arbitrary user-authored content, no scientific activity enum',
        'content': {'anything': ['is', 'literal', 1]}, 'artifact_ids': [],
        'response_schema': {'type': 'object'}}


def work_node():
    return MechanismSpec('arbitrary-node', MechanismFamily.CUSTOM, IMPLEMENTATION,
        inputs=(PortSpec('tasks', ChannelKind.ARTIFACT, REQUEST, required=False),),
        outputs=(PortSpec('responses', ChannelKind.ARTIFACT, RESPONSE, required=False),),
        parameters={'max_requests_per_invocation': 5})


def test_implementation_index_equals_actual_default_registry_plus_conditional_code():
    index = native_capability_index()
    actual = set(NativeScienceKernel(SystemSpec('scripted-empty-registry-check', 1))._registry().registered)
    found = {(item['implementation'], item['version']) for item in index['implementations']}
    assert found == actual | {('code.python.v1', 1)}
    assert ('native.researcher.work.v15', 1) in actual
    assert len(found) == len(index['implementations'])
    assert index['coverage']['omitted'] and index['coverage']['silent_size_truncation'] is False
    assert index['effects'] == {'candidate_mutation': False, 'handlers_invoked': False,
        'docker_calls': 0, 'model_calls': 0, 'native_years': 0}


def test_catalogue_never_constructs_executor_calls_model_or_runs_native_handler(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail('read-only catalogue invoked an executor/model/native handler')
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.__init__', fail)
    monkeypatch.setattr('utopia.system.native_kernel.NativeScienceKernel._stage', fail)
    monkeypatch.setattr('utopia.system.native_researcher_work.execute_researcher_work', fail)
    monkeypatch.setattr('requests.Session', fail)
    catalog = native_capability_catalog()
    assert catalog['cards'][IMPLEMENTATION]['privilege']['not_granted']


def test_full_catalog_and_prompt_index_stay_small_with_explicit_partial_detail_coverage():
    index, catalog = native_capability_index(), native_capability_catalog()
    assert len(json.dumps(index).encode()) < 20_000
    assert len(json.dumps(catalog).encode()) < 45_000
    assert set(catalog['cards']) == set(index['coverage']['detailed_contract_implementations'])
    assert index['coverage']['identifier_only_implementations']
    assert 'operator-specific registry_extension plugins' in index['coverage']['omitted']
    assert all(item['detail_path'] == '/cards/' + item['implementation'] for item in index['implementations']
        if item['implementation'] in catalog['cards'])


def test_cards_bind_actual_validator_files_and_do_not_instantiate_policies_or_tasks():
    catalog = native_capability_catalog()
    root = Path(__file__).resolve().parents[2]
    for card in catalog['cards'].values():
        for source in card['validators']:
            assert hashlib.sha256((root / source['path']).read_bytes()).hexdigest() == source['sha256']
    assert catalog['registry_sources']
    assert 'mechanism_id' not in catalog['cards'][IMPLEMENTATION]
    assert catalog['cards'][IMPLEMENTATION]['request_shape_schema']['properties']['instruction'] == {
        'type': 'string', 'minLength': 1}
    assert 'default' not in json.dumps(catalog['cards'][IMPLEMENTATION])


def test_completed_count_verifier_is_discoverable_with_actual_typed_input_and_no_truth_privilege():
    from utopia.system.native_claim_verification import IMPLEMENTATION as CLAIM_VERIFIER,CLAIM
    card=native_capability_catalog()['cards'][CLAIM_VERIFIER]
    sample={'schema':CLAIM,'claim_id':'authored-count','metric':'review-records',
        'after_year':0,'through_year':1,'asserted_value':0,'supersedes':None}
    Draft202012Validator(card['request_shape_schema']).validate(sample)
    assert 'scientific truth of a paper' in card['privilege']['not_granted']
    with pytest.raises(ValidationError):
        Draft202012Validator(card['request_shape_schema']).validate({**sample,'matches_native_records':True})


def test_researcher_work_card_matches_actual_exact_node_ports_and_parameter_contract():
    card = native_capability_catalog()['cards'][IMPLEMENTATION]
    node = work_node()
    validate_work_node(node)
    Draft202012Validator(card['parameters_shape_schema']).validate(dict(node.parameters))
    node_document = SystemSpec('SCRIPTED-node-shape', 1, mechanisms=(node,)).to_dict()['mechanisms'][0]
    assert card['ports']['inputs'] == node_document['inputs']
    assert card['ports']['outputs'] == node_document['outputs']
    validate_work_node(replace(node, inputs=(*node.inputs,
        PortSpec('extra-dependency', ChannelKind.SIGNAL, 'arbitrary-control', required=False))))


@pytest.mark.parametrize('parameters', [
    {}, {'max_requests_per_invocation': 0}, {'max_requests_per_invocation': 65},
    {'max_requests_per_invocation': True}, {'max_requests_per_invocation': '1'},
    {'max_requests_per_invocation': 1, 'policy': 'not-a-parameter'},
])
def test_researcher_work_parameter_shape_and_actual_validator_agree(parameters):
    card = native_capability_catalog()['cards'][IMPLEMENTATION]
    with pytest.raises(ValidationError):
        Draft202012Validator(card['parameters_shape_schema']).validate(parameters)
    with pytest.raises(GraphRuntimeError):
        validate_work_node(replace(work_node(), parameters=parameters))


@pytest.mark.parametrize('change', [
    lambda value: value.update(request_id=''), lambda value: value.update(actor_id='x' * 201),
    lambda value: value.update(schema='invented'), lambda value: value.update(extra='unexpected'),
    lambda value: value.update(instruction=''), lambda value: value.update(content=[]),
    lambda value: value.update(artifact_ids=['same', 'same']), lambda value: value.update(artifact_ids=['']),
    lambda value: value.update(response_schema={'type': 'array'}),
])
def test_researcher_work_request_shape_matches_actual_validator_for_structural_errors(change):
    card = native_capability_catalog()['cards'][IMPLEMENTATION]
    good = work_request()
    Draft202012Validator(card['request_shape_schema']).validate(good)
    assert validate_work_request(good) == good
    change(good)
    with pytest.raises(ValidationError):
        Draft202012Validator(card['request_shape_schema']).validate(good)
    with pytest.raises(GraphRuntimeError):
        validate_work_request(good)


def test_work_semantic_checks_are_not_misrepresented_as_shape_validation():
    card = native_capability_catalog()['cards'][IMPLEMENTATION]
    whitespace = work_request(); whitespace['instruction'] = '   '
    Draft202012Validator(card['request_shape_schema']).validate(whitespace)
    with pytest.raises(GraphRuntimeError):
        validate_work_request(whitespace)
    with pytest.raises(GraphRuntimeError):
        validate_work_node(replace(work_node(), parameters={'max_requests_per_invocation': 1.}))
    docs = json.dumps(card['semantic_constraints'])
    assert 'whitespace stripping' in docs and 'never bool or float' in docs
    assert '262144' in docs and 'reference-free/regex-free' in docs


def test_domain_action_payload_schemas_come_directly_from_actual_action_registry():
    from utopia.system.native_open_domain import default_actions, COMMAND_SCHEMA
    card = native_capability_catalog()['cards']['native.domain.commands.v1']
    assert card['action_payload_schemas'] == {
        name: schema for name, (schema, handler) in default_actions().actions.items()}
    assert card['request_shape_schema']['properties']['schema'] == {'const': COMMAND_SCHEMA}
    assert card['ports']['inputs'].startswith('commands port')


def test_transfer_shape_and_pure_actual_command_validator_agree_without_native_effects():
    from utopia.system.native_resource_transfers import _command
    schema = native_capability_catalog()['cards']['native.world.resource-transfers.v1']['request_shape_schema']
    good = {'transaction_id': 'SCRIPTED', 'from_actor': 'a', 'to_actor': 'b', 'amount': 1.}
    def value(payload):
        return DeliveredValue(ChannelKind.ARTIFACT, 'arbitrary-authored-type', payload,
            (), (), ('causal-event',), 'authored-producer', 'out', 1, 1)
    Draft202012Validator(schema).validate(good)
    assert _command(value(good))[-1] == good
    for amount in (0, -1, True, '1'):
        bad = clone(good); bad['amount'] = amount
        with pytest.raises(ValidationError):
            Draft202012Validator(schema).validate(bad)
        with pytest.raises(GraphRuntimeError):
            _command(value(bad))


def test_process_card_fields_equal_actual_controlled_delegate_contract():
    from tests.optimization.test_native_authoring_ir import code_node
    from utopia.system.native_process import controlled_activity, _validate_parameters
    node = SystemSpec.from_dict({'system_id': 'SCRIPTED', 'version': 1,
        'mechanisms': [code_node()]}).mechanisms[0]
    wrapped = controlled_activity(node, count=0, limit=2)
    card = native_capability_catalog()['cards']['native.process.activity.v1']
    assert set(card['parameter_fields']) == set(wrapped.parameters)
    assert _validate_parameters(wrapped.parameters) == node


def test_code_card_describes_actual_artifact_fields_without_source_template():
    from tests.optimization.test_native_authoring_ir import code_node
    from utopia.system.code_mechanisms import validate_code_artifact
    artifact = code_node()['parameters']['code_artifact']
    validate_code_artifact(artifact)  # AST only; source begins with a deliberate raise.
    card = native_capability_catalog()['cards']['code.python.v1']
    assert set(card['parameter_fields']['code_artifact']) == set(artifact)
    assert 'source template' in card['schema_scope']
    assert set(card['execution_ABI']['context_keys']) == {'period', 'phase', 'random_seed', 'parameters', 'state', 'inputs'}
