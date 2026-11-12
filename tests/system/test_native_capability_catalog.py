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
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus


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


def test_review_routing_contract_is_discoverable_and_matches_real_command_validation():
    from tests.system.test_native_review_routing_v13 import unit_batch
    from utopia.system.native_review_routing import REVIEW, SNAPSHOT, validate_routing_plan
    from utopia.system.code_mechanisms import sha
    catalog = native_capability_catalog()
    sim, batch, plan = unit_batch()
    card = catalog['cards'][REVIEW]
    Draft202012Validator(card['batch_shape_schema']).validate(batch)
    Draft202012Validator(catalog['cards'][SNAPSHOT]['response_shape_schema']).validate(batch)
    Draft202012Validator(card['request_shape_schema']).validate(plan)
    assert validate_routing_plan(sim, 1, batch, plan)['p'][0].id == 'b'
    # Card hash contract describes the exact real interpreter hash, not a recipe.
    encoded = json.dumps(batch, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
    assert hashlib.sha256(encoded).hexdigest() == plan['batch_sha256'] == sha(batch)
    assert 'policy' not in card and 'source' not in card
    assert 'No routing algorithm' in card['schema_scope']
    bad = clone(plan); bad['tasks'][0]['extra'] = 'not permitted'
    with pytest.raises(ValidationError):
        Draft202012Validator(card['request_shape_schema']).validate(bad)
    with pytest.raises(GraphRuntimeError):
        validate_routing_plan(sim, 1, batch, bad)


def test_review_routing_shape_does_not_claim_semantic_eligibility_or_year_validation():
    from tests.system.test_native_review_routing_v13 import unit_batch
    from utopia.system.native_review_routing import REVIEW, validate_routing_plan
    card = native_capability_catalog()['cards'][REVIEW]
    sim, batch, plan = unit_batch()
    plan['tasks'][0]['reviewer_id'] = 'unknown'
    Draft202012Validator(card['request_shape_schema']).validate(plan)
    with pytest.raises(GraphRuntimeError):
        validate_routing_plan(sim, 1, batch, plan)
    assert 'duplicate triples' in ' '.join(card['semantic_constraints'])
    assert 'not bool/float' in ' '.join(card['semantic_constraints'])


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


def test_opening_observation_card_matches_literal_existing_ports_without_new_effect():
    from utopia.system.native_kernel import legacy_world_system, CONTEXT_RECEIVER
    catalog = native_capability_catalog()
    original = legacy_world_system().to_dict()
    opening = next(n for n in original['mechanisms'] if n['implementation'] == 'native.phase.open.v1')
    assert catalog['cards']['native.phase.open.v1']['ports']['outputs'] == opening['outputs']
    card = catalog['cards'][CONTEXT_RECEIVER]
    assert card['ports']['outputs'] == []
    sample = {'payload': {'arbitrary-protocol': {'hypotheses': ['literal content']}}, 'actor_ids': ['existing']}
    Draft202012Validator(card['producer_code_envelope_shape_schema']).validate(sample)
    assert 'instruction' not in card['producer_code_envelope_shape_schema']['properties']['payload']
    with pytest.raises(ValidationError):
        Draft202012Validator(card['producer_code_envelope_shape_schema']).validate({'payload': {}, 'actor_ids': []})


def test_documented_delivery_uses_real_handler_and_preserves_arbitrary_payload():
    from types import SimpleNamespace
    from utopia.system.native_kernel import CONTEXT_RECEIVER, institutional_context_prompt
    kernel = NativeScienceKernel(SystemSpec('scripted-only-delivery', 1))
    actor = SimpleNamespace(can_author=True, institutional_context=[])
    kernel._simulation = SimpleNamespace(ecosystem=SimpleNamespace(agent_population={'existing': actor}))
    payload = {'not-a-catalogue-policy': {'arbitrary': ['literal', 3]}}
    value = DeliveredValue(ChannelKind.ARTIFACT, 'SCRIPTED-new-protocol', payload,
        ('existing',), (), ('actual-scripted-lineage',), 'unseeded-producer', 'out', 1, 1)
    context = SimpleNamespace(inputs={'any-port': (value,)}, period=1)
    card = native_capability_catalog()['cards'][CONTEXT_RECEIVER]
    Draft202012Validator(card['producer_code_envelope_shape_schema']).validate({'payload': payload, 'actor_ids': ['existing']})
    result = kernel._receive_context(context)
    assert not result.outputs and len(result.events) == 1
    assert actor.institutional_context[0]['payload'] == payload
    assert result.events[0].event_type == 'native.system.context_delivered'
    assert 'literal' in institutional_context_prompt(actor)
    with pytest.raises(GraphRuntimeError, match='already delivered'): kernel._receive_context(context)
    for ids in ((), ('unknown',)):
        bad = replace(value, actor_ids=ids)
        with pytest.raises(GraphRuntimeError): kernel._receive_context(SimpleNamespace(inputs={'any': (bad,)}, period=2))


def test_observation_shape_on_original_native_years(tmp_path, fixed_corpus, monkeypatch):
    from tests.system.test_native_science_kernel import make_sim
    from utopia.system.native_kernel import legacy_world_system
    schema = native_capability_catalog()['cards']['native.phase.open.v1']['response_shape_schema']
    original = NativeScienceKernel.observation; observed = []
    def capture(self):
        result = original(self); observed.append(result); return result
    monkeypatch.setattr(NativeScienceKernel, 'observation', capture)
    sim, _ = make_sim(tmp_path/'native-observations', native=NativeScienceKernel(legacy_world_system()))
    try:
        sim.run()
        assert len(observed) == 13*6
        for value in observed: Draft202012Validator(schema).validate(value)
        assert {s['year'] for s in observed} == set(range(1, 7))
    finally:
        sim.llm.response_cache.close()


def test_retained_information_extension_is_bound_to_actual_old_source_and_current_contract():
    import ast
    import subprocess
    from utopia.optimization.native_numeric_designer import checked
    root = Path(__file__).resolve().parents[2]
    r = checked(json.loads((root/'research/results/native-information-capability-discovery-v1.json').read_text()))
    old = subprocess.check_output(['git', 'show', r['prior_scientific_source_commit']+
                                   ':utopia/system/native_capability_catalog.py'], cwd=root)
    assert hashlib.sha256(old).hexdigest() == r['prior_catalog_source_sha256']
    # Parse this original data source; never import/execute historical code.
    fields = next(ast.literal_eval(n.value) for n in ast.parse(old).body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CATALOG_IMPLEMENTATIONS' for t in n.targets))
    assert all(identity not in fields for identity in r['new_detailed_implementations'])
    catalog = native_capability_catalog(); index = catalog['index']
    assert catalog['content_sha256'] == r['catalog_content_sha256']
    assert len(catalog['cards']) == r['detailed_cards'] == 10
    assert len(index['implementations']) == r['index_implementations'] == 36
    assert len(json.dumps(catalog).encode()) == r['full_catalog_json_bytes']
    assert r['verification']['passed'] == 89 and not r['actual_qwen_discovery_or_benefit_demonstrated']
    assert not r['new_native_privileges'] and r['new_campaign_requires_fresh_source_bound_readiness']
