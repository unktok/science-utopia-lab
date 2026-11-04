"""SCRIPTED syntax/interface verification; no provider or native world calls."""
import json
import hashlib

import pytest

from tests.optimization.test_native_search_generator_v14 import Model, IMAGE, BINDING, result_path
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_authoring_ir import (
    AuthoringIRDiagnostic, StableIDAuthoringProtocol, path_catalog, resolve_address)
from utopia.optimization.native_search_generator_v14 import LLMVocabularyGenerator, make_local_vocabulary_generator
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest

ALPHA = 'arbitrary.alpha-identity'
PROTOCOL = StableIDAuthoringProtocol()


def code_node(identity=ALPHA):
    return {'mechanism_id': identity, 'family': 'custom', 'implementation': 'code.python.v1',
        'version': 1, 'inputs': [], 'outputs': [], 'parameters': {'runtime_image_id': IMAGE, 'gain': .5,
            'code_artifact': {'schema': 'scienceutopia.code-mechanism.v1', 'label': 'SCRIPTED',
                'source': 'raise RuntimeError("DO_NOT_EXECUTE_GENERATED_SOURCE")\ndef step(context):\n    return {"outputs": {}, "state": {}}\n',
                'inputs': {}, 'outputs': {}, 'state_schema': {'type': 'object'}}}}


def parent():
    node = code_node()
    return SystemSpec.from_dict({'system_id': 'scripted-interface-fixture', 'version': 1,
        'agent_types': [], 'artifact_types': [], 'mechanisms': [node, {
            'mechanism_id': 'beta', 'family': 'custom', 'implementation': 'unlisted.test.placeholder.v1',
            'version': 1, 'inputs': [], 'outputs': [], 'parameters': {'gain': .75}}],
        'connections': [], 'schedules': [], 'initial_state': {'coordinate': .25, 'flag': True},
        'global_invariants': [], 'metadata': {}})


def request():
    return {'parent_system': parent().to_dict(), 'loss_spec': loss_spec(), 'rng_seed': 42,
        'count': 1, 'generation': 0, 'observations': [], 'history': []}


def edit(identity=ALPHA, path='/parameters/gain', value=1.25):
    return {'op': 'replace', 'selector': {'mechanism_id': identity}, 'path': path, 'value': value}


def coordinate(identity=ALPHA, path='/parameters/gain'):
    return {'id': 'arbitrary-coordinate', 'selector': {'mechanism_id': identity}, 'path': path,
        'lower': -1., 'upper': 2., 'mean': .2, 'sigma': .7}


def output():
    return {'operations': [edit()], 'factors': [], 'continuous': [coordinate()],
        'rationale': 'SCRIPTED address interface only; no scientific outcome'}


def compile_output(value=None):
    return PROTOCOL.compile(request(), value or output(), binding_sha256='c' * 64, provider_binding=BINDING)


def generator(model, directory, protocol=PROTOCOL):
    return LLMVocabularyGenerator(model, directory, image_id=IMAGE, provider_binding=BINDING, protocol=protocol)


def test_stable_ids_compile_exact_literal_patch_with_deterministic_lossless_provenance():
    original = request()
    definition = compile_output()
    assert definition['base_patch']['operations'] == [{'op': 'replace', 'path': '/mechanisms/0/parameters/gain', 'value': 1.25}]
    assert definition['continuous'] == [{k: v for k, v in coordinate().items() if k != 'selector'} | {
        'path': '/mechanisms/0/parameters/gain'}]
    trace = definition['provenance']['authoring_compiler']
    assert trace['raw_ir'] == output() and trace['raw_ir_sha256'] == digest(output())
    assert trace['translated_output']['operations'] == definition['base_patch']['operations']
    assert trace['translated_output_sha256'] == digest(trace['translated_output'])
    assert trace['base_operation_map'][0]['actual_owner_id'] == ALPHA
    assert trace['protocol'] == PROTOCOL.binding()
    assert trace['implicit_source_or_wire_repairs'] is False and trace['support_filtering'] is False
    assert compile_output() == definition and request() == original


def test_reordering_parent_resolves_same_exact_id_without_fuzzy_matching():
    body = request(); body['parent_system']['mechanisms'].reverse()
    definition = PROTOCOL.compile(body, output(), binding_sha256='c' * 64, provider_binding=BINDING)
    assert definition['base_patch']['operations'][0]['path'] == '/mechanisms/1/parameters/gain'
    assert definition['continuous'][0]['path'] == '/mechanisms/1/parameters/gain'
    bad = output(); bad['operations'][0]['selector']['mechanism_id'] = 'alpha'
    with pytest.raises(AuthoringIRDiagnostic, match='missing or ambiguous') as error:
        compile_output(bad)
    assert error.value.diagnostics[0]['match_count'] == 0


def test_exact_duplicate_id_is_rejected_instead_of_selecting_first_match():
    document = parent().to_dict(); document['mechanisms'].append(clone(document['mechanisms'][0]))
    with pytest.raises(AuthoringIRDiagnostic) as error:
        resolve_address(document, edit())
    assert error.value.diagnostics[0]['match_count'] == 2


def test_sequential_add_select_remove_uses_current_authored_document():
    value = output()
    value['operations'] = [{'op': 'add', 'path': '/mechanisms/0', 'value': code_node('fresh-unlisted-id')},
        edit(value=.9), {'op': 'remove', 'selector': {'mechanism_id': 'fresh-unlisted-id'}, 'path': ''}]
    definition = compile_output(value)
    operations = definition['base_patch']['operations']
    assert [o['path'] for o in operations] == ['/mechanisms/0', '/mechanisms/1/parameters/gain', '/mechanisms/0']
    assert operations[1]['value'] == .9 and definition['continuous'][0]['path'] == '/mechanisms/0/parameters/gain'


def test_local_json_pointer_escapes_are_literal_and_scalar_traversal_is_precise():
    body = output(); body['continuous'] = []
    body['operations'] = [{'op': 'add', 'selector': {'mechanism_id': ALPHA},
        'path': '/parameters/slash~1tilde~0', 'value': .3}]
    assert compile_output(body)['base_patch']['operations'][0]['path'] == '/mechanisms/0/parameters/slash~1tilde~0'
    body['operations'] = [edit(path='/parameters/code_artifact/source/absent', value='x')]
    with pytest.raises(AuthoringIRDiagnostic, match='scalar') as error:
        compile_output(body)
    assert error.value.diagnostics[0]['deepest_existing_prefix'] == '/mechanisms/0/parameters/code_artifact/source'
    assert error.value.diagnostics[0]['first_missing_segment'] == 'absent'


def test_full_document_escape_can_add_arbitrary_nodes_protocol_wires_schedules_process_metadata():
    source, sink = code_node('new-source-any-name'), code_node('new-sink-any-name')
    source['outputs'] = [{'port_id': 'invented', 'channel': 'artifact', 'artifact_type': 'invented-message', 'required': True}]
    source['parameters']['code_artifact']['outputs'] = {'invented': {'type': 'object'}}
    sink['inputs'] = [{'port_id': 'receive', 'channel': 'artifact', 'artifact_type': 'invented-message', 'required': True}]
    sink['parameters']['code_artifact']['inputs'] = {'receive': {'type': 'object'}}
    value = output(); value['continuous'] = []
    value['operations'] = [
        {'op': 'add', 'path': '/artifact_types/-', 'value': {'artifact_type_id': 'invented-message', 'description': 'authored'}},
        {'op': 'add', 'path': '/mechanisms/-', 'value': source},
        {'op': 'add', 'path': '/mechanisms/-', 'value': sink},
        {'op': 'add', 'path': '/connections/-', 'value': {'source_mechanism': source['mechanism_id'],
            'source_port': 'invented', 'target_mechanism': sink['mechanism_id'], 'target_port': 'receive',
            'channel': 'artifact', 'latency': 0}},
        {'op': 'add', 'path': '/schedules/-', 'value': {'mechanism_id': source['mechanism_id'], 'phase': 100, 'trigger': 'annual'}},
        {'op': 'add', 'path': '/schedules/-', 'value': {'mechanism_id': sink['mechanism_id'], 'phase': 110, 'trigger': 'annual'}},
        {'op': 'add', 'path': '/metadata/native_processes', 'value': {'explicit-authored-description': 'no host inference'}}]
    definition = compile_output(value)
    assert definition['base_patch']['operations'] == value['operations']
    assert definition['provenance']['authoring_compiler']['raw_ir'] == value
    # Literal generated source begins with a raise; successful compilation is
    # evidence of parsing/data transport, never source execution on the host.
    assert definition['base_patch']['operations'][1]['value']['parameters']['code_artifact']['source'].startswith('raise RuntimeError')


def test_precise_missing_path_reports_actual_owner_and_deepest_prefix():
    value = output(); value['operations'] = [{'op': 'replace', 'path': '/mechanisms/1/parameters/code_artifact/source', 'value': 'literal'}]
    with pytest.raises(AuthoringIRDiagnostic) as error:
        compile_output(value)
    diagnostic = error.value.diagnostics[0]
    assert diagnostic['operation_index'] == 0 and diagnostic['path'] == value['operations'][0]['path']
    assert diagnostic['actual_owner_id'] == 'beta'
    assert diagnostic['actual_owner_implementation'] == 'unlisted.test.placeholder.v1'
    assert diagnostic['deepest_existing_prefix'] == '/mechanisms/1/parameters'
    assert diagnostic['first_missing_segment'] == 'code_artifact' and diagnostic['available_keys'] == ['gain']


@pytest.mark.parametrize('field,value,expected', [
    ('source', 3, 'string'), ('source', '', 'string'), ('source', '界' * 21846, 'string'),
    ('inputs', '{}', 'object'), ('outputs', '{}', 'object'), ('state_schema', '{}', 'object')])
def test_literal_source_length_types_and_schema_objects_are_never_repaired(field, value, expected):
    body = output(); body['operations'] = [edit(path='/parameters/code_artifact/' + field, value=value)]
    with pytest.raises(AuthoringIRDiagnostic) as error:
        compile_output(body)
    diagnostic = error.value.diagnostics[0]
    assert diagnostic['expected_type'] == expected and diagnostic['actual_owner_id'] == ALPHA
    assert diagnostic['operation_index'] == 0 and diagnostic['stage'] == 'base'
    assert body['operations'][0]['value'] == value
    if field == 'source' and isinstance(value, str):
        assert diagnostic['source_utf8_bytes'] == len(value.encode())


@pytest.mark.parametrize('source', ['def step(:\n pass', 'def different(context):\n return {}', 'def step(a,b):\n return {}'])
def test_source_ast_and_step_abi_errors_have_exact_owner_path_without_source_execution(source):
    body = output(); body['operations'] = [edit(path='/parameters/code_artifact/source', value=source)]
    with pytest.raises(AuthoringIRDiagnostic) as error:
        compile_output(body)
    diagnostic = error.value.diagnostics[0]
    assert diagnostic['path'] == '/mechanisms/0/parameters/code_artifact/source'
    assert diagnostic['actual_owner_id'] == ALPHA and diagnostic['operation_index'] == 0
    assert diagnostic['expected_type'] == 'valid literal Python source/step ABI'
    if source.startswith('def step(:'):
        assert diagnostic['source_line'] == 1 and diagnostic['source_column']


def test_schema_port_value_must_be_object_and_not_encoded_text():
    body = output(); body['operations'] = [edit(path='/parameters/code_artifact/inputs', value={'new-port': '{}'})]
    with pytest.raises(AuthoringIRDiagnostic) as error:
        compile_output(body)
    diagnostic = error.value.diagnostics[0]
    assert diagnostic['path'] == '/mechanisms/0/parameters/code_artifact/inputs/new-port'
    assert diagnostic['expected_type'] == 'object' and diagnostic['operation_index'] == 0


def test_hidden_process_delegate_source_and_image_are_checked_without_host_execution():
    from dataclasses import replace
    from utopia.system import ArtifactTypeSpec
    from utopia.system.native_process import controlled_activity, CONTROL
    initial = parent()
    wrapped = controlled_activity(initial.mechanisms[0], count=1, limit=1)
    body = request(); body['parent_system'] = replace(initial,
        artifact_types=(ArtifactTypeSpec(CONTROL),), mechanisms=(wrapped, initial.mechanisms[1])).to_dict()
    value = output(); value['continuous'] = []
    value['operations'] = [edit(path='/parameters/delegate/parameters/runtime_image_id', value='sha256:' + 'f' * 64)]
    with pytest.raises(AuthoringIRDiagnostic, match='pinned operator sandbox') as error:
        PROTOCOL.compile(body, value, binding_sha256='c' * 64, provider_binding=BINDING)
    diagnostic = error.value.diagnostics[0]
    assert diagnostic['path'] == '/mechanisms/0/parameters/delegate/parameters/runtime_image_id'
    assert diagnostic['actual_owner_implementation'] == 'native.process.activity.v1'
    assert diagnostic['executed_owner_implementation'] == 'code.python.v1'
    assert diagnostic['operation_index'] == 0


@pytest.mark.parametrize('address', [
    {'selector': {'mechanism_id': ALPHA}, 'path': '/parameters/code_artifact/source'},
    {'path': '/initial_state/flag'}, {'path': '/system_id'}])
def test_coordinates_reject_source_text_boolean_without_reinterpretation(address):
    body = output(); body['continuous'][0].pop('selector'); body['continuous'][0].update(address)
    with pytest.raises(AuthoringIRDiagnostic, match='finite numeric') as error:
        compile_output(body)
    assert error.value.diagnostics[0]['expected_type'] == 'finite number'
    assert error.value.diagnostics[0]['stage'] == 'continuous'


@pytest.mark.parametrize('change', [{'sigma': 0}, {'lower': 2, 'upper': 1}, {'mean': float('inf')}])
def test_coordinate_settings_are_finite_and_ordered_with_no_fallback(change):
    body = output(); body['continuous'][0].update(change)
    with pytest.raises(AuthoringIRDiagnostic):
        compile_output(body)


@pytest.mark.parametrize('change', [
    lambda o: o['operations'][0].update(command='forbidden-unknown-field'),
    lambda o: o['operations'][0]['selector'].update(index=0),
    lambda o: o['operations'][0].update(op='remove'),
    lambda o: o['continuous'][0].update(extra=1),
    lambda o: o.update(factors=[{'id': 'f', 'kind': 'categorical', 'choices': 'not-array'}]),
    lambda o: o['continuous'][0].update(sigma=True)])
def test_nested_ir_schemas_are_strict(change):
    body = output(); change(body)
    with pytest.raises(AuthoringIRDiagnostic, match='schema'):
        compile_output(body)


def shift_factor():
    return {'id': 'shift', 'kind': 'bernoulli', 'choices': [
        {'id': 'stay', 'operations': [], 'provenance': {'mode': 'SCRIPTED'}},
        {'id': 'insert', 'operations': [{'op': 'add', 'path': '/mechanisms/0', 'value': code_node('inserted')}],
            'provenance': {'mode': 'SCRIPTED'}}]}


def tuning_factor():
    return {'id': 'tune', 'kind': 'bernoulli', 'choices': [
        {'id': 'low', 'operations': [edit('beta', value=.2)], 'provenance': {'mode': 'SCRIPTED'}},
        {'id': 'high', 'operations': [edit('beta', value=.8)], 'provenance': {'mode': 'SCRIPTED'}}]}


def test_factor_choice_branch_dependent_pointer_rejects_instead_of_guessing():
    body = output(); body['factors'] = [shift_factor(), tuning_factor()]; body['continuous'] = []
    with pytest.raises(AuthoringIRDiagnostic, match='branch-dependent pointer') as error:
        compile_output(body)
    diagnostic = error.value.diagnostics[0]
    assert diagnostic['stage'] == 'factor-address-stability' and diagnostic['factor_id'] == 'tune'
    assert diagnostic['previous_paths'] == ['/mechanisms/1/parameters/gain']
    assert diagnostic['translated_paths'] == ['/mechanisms/2/parameters/gain']


def test_coordinate_branch_dependent_pointer_rejects_without_transport():
    body = output(); body['factors'] = [shift_factor()]; body['continuous'] = [coordinate('beta')]
    with pytest.raises(AuthoringIRDiagnostic, match='branch-dependent pointer') as error:
        compile_output(body)
    diagnostic = error.value.diagnostics[0]
    assert diagnostic['stage'] == 'continuous-address-stability'
    assert diagnostic['previous_path'] == '/mechanisms/1/parameters/gain'
    assert diagnostic['path'] == '/mechanisms/2/parameters/gain'


def test_explicit_conditional_choices_compile_without_changing_support_or_logits():
    body = output(); body['continuous'] = []
    tuning = tuning_factor()
    tuning['support'] = [{'when': {'shift': 'stay'}, 'allow': ['low']},
        {'when': {'shift': 'insert'}, 'allow': ['high']}]
    body['factors'] = [shift_factor(), tuning]; body['logits'] = {'shift': [.4], 'tune': [-.7]}
    definition = compile_output(body)
    assert definition['factors'][1]['support'] == tuning['support']
    assert definition['factors'][1]['choices'][0]['operations'][0]['path'] == '/mechanisms/1/parameters/gain'
    assert definition['factors'][1]['choices'][1]['operations'][0]['path'] == '/mechanisms/2/parameters/gain'
    assert definition['logits'] == body['logits']
    assert definition['provenance']['authoring_compiler']['reachable_assignments_checked'] == 2


def test_authored_full_document_factor_paths_keep_literal_index_semantics():
    body = output(); tuning = tuning_factor(); body['continuous'] = []
    for choice in tuning['choices']:
        choice['operations'][0].pop('selector'); choice['operations'][0]['path'] = '/mechanisms/1/parameters/gain'
    body['factors'] = [shift_factor(), tuning]
    definition = compile_output(body)
    assert definition['factors'][1] == tuning
    assert definition['provenance']['authoring_compiler']['reachable_assignments_checked'] == 4


def test_path_catalog_has_exact_types_addresses_source_lengths_without_source_duplication():
    catalog = path_catalog(parent().to_dict())
    mechanism = catalog['mechanisms'][0]
    source = mechanism['fields']['/parameters/code_artifact/source']
    assert mechanism['mechanism_id'] == ALPHA and mechanism['document_path'] == '/mechanisms/0'
    assert source['role'] == 'literal-python-source' and source['numeric_coordinate_eligible'] is False
    assert source['utf8_bytes'] == len(code_node()['parameters']['code_artifact']['source'].encode())
    assert mechanism['fields']['/parameters/gain'] == 'number'
    assert catalog['document_fields']['/initial_state/flag'] == 'boolean'
    assert 'DO_NOT_EXECUTE_GENERATED_SOURCE' not in json.dumps(catalog)
    assert path_catalog(json.loads(json.dumps(parent().to_dict(), sort_keys=True))) == catalog


def test_optional_protocol_journal_cold_replay_and_rich_feedback_preserve_legacy_default(tmp_path):
    invalid = output(); invalid['operations'][0]['path'] = '/parameters/absent/source'
    model = Model([invalid, output()])
    definition = generator(model, tmp_path)(request())
    assert len(model.calls) == 2
    prompt = json.loads(model.calls[1]['prompt'])
    diagnostic = prompt['technical_feedback_from_previous_attempts'][0]['diagnostics'][0]
    assert diagnostic['first_missing_segment'] == 'absent' and diagnostic['actual_owner_id'] == ALPHA
    assert prompt['parent_path_catalog'] == path_catalog(request()['parent_system'])
    assert prompt['parent_system'] == request()['parent_system']
    saved_request = json.loads((result_path(tmp_path).parent / 'request.json').read_text())
    assert saved_request['authoring_protocol'] == PROTOCOL.binding()
    no_calls = Model([])
    sorted_request = json.loads(json.dumps(request(), sort_keys=True))
    assert generator(no_calls, tmp_path)(sorted_request) == definition and no_calls.calls == []
    with pytest.raises(ValueError, match='changed'):
        generator(Model([]), tmp_path, protocol=None)(request())
    legacy = LLMVocabularyGenerator(Model([]), tmp_path / 'legacy', image_id=IMAGE, provider_binding=BINDING)
    assert legacy.protocol is None


def test_protocol_identity_or_schema_mutation_is_rejected_before_provider_call(tmp_path):
    class Versioned(StableIDAuthoringProtocol):
        revision = 1
        def binding(self): return {**super().binding(), 'test_revision': self.revision}
    protocol = Versioned(); model = Model([output()]); author = generator(model, tmp_path, protocol=protocol)
    protocol.revision = 2
    with pytest.raises(ValueError, match='protocol changed'):
        author(request())
    assert not model.calls


@pytest.mark.parametrize('field', ['raw_ir', 'translated_output'])
def test_rehashed_compiler_trace_tamper_is_rejected_by_recompilation(tmp_path, field):
    generator(Model([output()]), tmp_path)(request())
    result_file = result_path(tmp_path)
    attempt_file = result_file.parent / 'attempt-00.completed.json'
    attempt, result = json.loads(attempt_file.read_text()), json.loads(result_file.read_text())
    forged = attempt['definition']
    forged['provenance']['authoring_compiler'][field]['operations'][0]['value'] = 99.
    attempt['content_sha256'] = digest({k: v for k, v in attempt.items() if k != 'content_sha256'})
    attempt_file.write_text(json.dumps(attempt))
    result['definition'] = clone(forged)
    result['attempts'][0]['completed_sha256'] = hashlib.sha256(attempt_file.read_bytes()).hexdigest()
    result['content_sha256'] = digest({k: v for k, v in result.items() if k != 'content_sha256'})
    result_file.write_text(json.dumps(result))
    with pytest.raises(ValueError, match='compiler envelope'):
        generator(Model([]), tmp_path)(request())


def test_failed_raw_ir_and_receipt_hashes_reach_next_generation_with_explicit_omissions(tmp_path):
    invalid = output(); invalid['operations'][0]['path'] = '/parameters/missing/source'
    failure = LLMVocabularyGenerator(Model([invalid]), tmp_path, image_id=IMAGE,
        provider_binding=BINDING, max_attempts=1, protocol=PROTOCOL)(request())
    evidence = failure['generation_failure']['attempt_evidence'][0]
    assert evidence['raw_ir'] == invalid and evidence['raw_ir_sha256'] == digest(invalid)
    assert evidence['completed_sha256'] and evidence['started_sha256']
    later = request(); later['generation'] = 1
    later['history'] = [{'definition': failure, 'generation_error': {
        'type': 'ValueError', 'message': 'complete generated definition/provenance and finite search settings required', 'loss': None},
        'report': {'status': 'invalid-generated-vocabulary', 'loss': None}}]
    prompt = json.loads(PROTOCOL.build_prompt(later, image_id=IMAGE, errors=[]))
    past = prompt['own_history']['generation_authoring_failures'][0]
    assert past['technical_errors'][0]['diagnostics'][0]['first_missing_segment'] == 'missing'
    archived = past['failed_ir_receipts'][0]
    assert archived['raw_ir_sha256'] == digest(invalid)
    operation = archived['operation_receipts'][0]
    assert operation['path'] == invalid['operations'][0]['path']
    assert operation['selector'] == invalid['operations'][0]['selector']
    assert operation['raw_operation_sha256'] == digest(invalid['operations'][0])
    assert operation['literal_operand']['sha256'] == digest(invalid['operations'][0]['value'])
    assert 'value' not in operation
    assert prompt['prompt_view_metadata']['silent_truncation'] is False
    assert prompt['prompt_view_metadata']['other_arm_data_included'] is False
    assert len(prompt['prompt_view_metadata']['omitted_fields']) == 3
    assert LLMVocabularyGenerator(Model([]), tmp_path, image_id=IMAGE,
        provider_binding=BINDING, max_attempts=1, protocol=PROTOCOL)(request()) == failure


def test_legacy_failure_technical_errors_are_visible_even_without_raw_attempt_evidence():
    body = request(); body['history'] = [{'definition': {'generation_failure': {
        'request_sha256': 'c' * 64, 'technical_errors': [{'type': 'ValueError', 'message': 'exact archived error'}]}},
        'generation_error': {'loss': None}, 'report': {'loss': None}}]
    prompt = json.loads(PROTOCOL.build_prompt(body, image_id=IMAGE, errors=[]))
    failure = prompt['own_history']['generation_authoring_failures'][0]
    assert failure['technical_errors'] == [{'type': 'ValueError', 'message': 'exact archived error'}]
    assert failure['failed_ir_receipts'] == []


def test_production_helper_defaults_stable_protocol_but_explicit_none_remains_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr('utopia.optimization.native_designer_preflight.require_certificate', lambda *a, **k: None)
    monkeypatch.setattr('utopia.optimization.native_search_generator_v14.LocalQwenDesignerModel', lambda *a, **k: Model([]))
    stable = make_local_vocabulary_generator(tmp_path / 'stable', image_id=IMAGE, provider_binding=BINDING)
    legacy = make_local_vocabulary_generator(tmp_path / 'legacy', image_id=IMAGE, provider_binding=BINDING, protocol=None)
    assert isinstance(stable.protocol, StableIDAuthoringProtocol) and legacy.protocol is None
