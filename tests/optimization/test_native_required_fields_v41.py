"""SCRIPTED post-failure field diagnostics; no model, Docker or source execution."""
from copy import deepcopy
from dataclasses import MISSING, fields
import json
import os
from pathlib import Path
from urllib.parse import quote

import pytest

from tests.optimization.test_native_authoring_ir import ALPHA, BINDING, IMAGE, code_node, request
from tests.optimization.test_native_staged_author_v15 import Model, author, finish, apply
from tests.optimization.test_native_planning_author_v22 import PLAN
from utopia.optimization import native_authoring_ir as ir
from utopia.optimization.native_staged_author_v15 import (
    SYSTEM_PROMPT, build_conversation, build_prompt, initial_draft, replay_staged_generation,
)
from utopia.system import model
from utopia.system.design_patch import digest


@pytest.fixture(autouse=True)
def no_execution(monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError('diagnostic must never execute generated code or construct Docker')
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.__init__', forbidden)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)


def compile_document(document, operations=None):
    body = request()
    if operations is None:
        operations = [{'op': 'replace' if key in body['parent_system'] else 'add',
            'path': '/' + key, 'value': value} for key, value in document.items()
            if key not in body['parent_system'] or body['parent_system'][key] != value]
        operations += [{'op': 'remove', 'path': '/' + key}
            for key in body['parent_system'] if key not in document]
    return ir.StableIDAuthoringProtocol().compile(body, {
        'operations': operations, 'factors': [], 'continuous': [], 'rationale': 'SCRIPTED diagnostic only'},
        binding_sha256='d' * 64, provider_binding=BINDING)


CASES = [(model.SystemSpec, None, name) for name in ('system_id', 'version')]
CASES += [(model.MechanismSpec, '/mechanisms/0', name)
    for name in ('mechanism_id', 'family', 'implementation')]
CASES += [(model.PortSpec, '/mechanisms/1/' + direction + '/0', name)
    for direction in ('inputs', 'outputs') for name in ('port_id', 'channel')]
CASES += [(model.AgentTypeSpec, '/agent_types/0', 'agent_type_id'),
    (model.ArtifactTypeSpec, '/artifact_types/0', 'artifact_type_id')]
CASES += [(model.ConnectionSpec, '/connections/0', name)
    for name in ('source_mechanism', 'source_port', 'target_mechanism', 'target_port', 'channel')]
CASES += [(model.ScheduleSpec, '/schedules/0', name) for name in ('mechanism_id', 'phase')]


@pytest.mark.parametrize('record_type,path,missing', CASES)
def test_required_names_match_real_parser_and_dataclasses_without_changing_values(record_type, path, missing):
    document = request()['parent_system']
    document['mechanisms'][1].update(inputs=[{'port_id': 'in', 'channel': 'artifact', 'required': False,
        'artifact_type': None}], outputs=[{'port_id': 'out', 'channel': 'artifact', 'required': True,
            'artifact_type': None}])
    document['agent_types'] = [{'agent_type_id': 'author', 'roles': [], 'description': ''}]
    document['artifact_types'] = [{'artifact_type_id': 'paper', 'description': ''}]
    document['connections'] = [{'source_mechanism': 'beta', 'source_port': 'out',
        'target_mechanism': 'beta', 'target_port': 'in', 'channel': 'artifact', 'latency': 0}]
    document['schedules'] = [{'mechanism_id': 'beta', 'phase': 1, 'trigger': 'annual'}]
    target = document
    for part in ir.pointer(path) if path else []:
        target = target[int(part)] if isinstance(target, list) else target[part]
    target.pop(missing)
    original = deepcopy(document)
    with pytest.raises((KeyError, TypeError)) as parser_error:
        model.SystemSpec.from_dict(document)
    with pytest.raises(ir.AuthoringIRDiagnostic) as error:
        compile_document(document)
    diagnostic = error.value.diagnostics[0]
    expected_path = (path or '') + '/' + missing
    assert diagnostic['path'] == expected_path and diagnostic['first_missing_segment'] == missing
    assert diagnostic['deepest_existing_prefix'] == (path or '')
    assert diagnostic['available_keys'] == sorted(target)
    assert diagnostic['missing_fields'] == [missing]
    assert diagnostic['required_fields'] == [field.name for field in fields(record_type)
        if field.default is MISSING and field.default_factory is MISSING]
    assert diagnostic['model_type'] == record_type.__name__
    assert diagnostic['underlying_error_type'] == type(parser_error.value).__name__
    assert diagnostic['underlying_error_message'] == str(parser_error.value)
    assert type(error.value.__cause__) is type(parser_error.value)
    assert document == original and diagnostic['operation_index'] is not None
    if path and path.startswith('/mechanisms/'):
        index = int(path.split('/')[2]); owner = document['mechanisms'][index]
        assert diagnostic['actual_owner_id'] == owner.get('mechanism_id')
        assert diagnostic['actual_owner_implementation'] == owner.get('implementation')


def test_multiple_missing_connection_fields_follow_actual_parser_key_precedence():
    document = request()['parent_system']; document['connections'] = [{}]
    with pytest.raises(ir.AuthoringIRDiagnostic) as error:
        compile_document(document)
    diagnostic = error.value.diagnostics[0]
    # from_dict reads/converts channel before forwarding required ctor arguments.
    assert diagnostic['first_missing_segment'] == 'channel'
    assert diagnostic['path'] == '/connections/0/channel'
    assert diagnostic['missing_fields'] == [field.name for field in fields(model.ConnectionSpec)
        if field.default is MISSING and field.default_factory is MISSING]


def test_unrelated_later_dictionary_edit_cannot_claim_a_missing_owner_id_failure():
    bad = code_node(); bad.pop('mechanism_id')
    operations = [{'op': 'replace', 'path': '/mechanisms/0', 'value': bad},
        {'op': 'replace', 'path': '/mechanisms/1/parameters', 'value': {'unrelated': {'mechanism_id': None}}}]
    with pytest.raises(ir.AuthoringIRDiagnostic) as error:
        compile_document(None, operations)
    diagnostic = error.value.diagnostics[0]
    assert diagnostic['operation_index'] == 0
    assert diagnostic['path'] == '/mechanisms/0/mechanism_id'
    assert diagnostic['actual_owner_id'] is None
    assert diagnostic['actual_owner_implementation'] == 'code.python.v1'


@pytest.mark.parametrize('remove_again', [False, True])
def test_same_id_literal_in_later_operand_does_not_override_concrete_missing_field_path(remove_again):
    bad = code_node()
    bad['inputs'] = [{'channel': 'artifact', 'artifact_type': None, 'required': False}]
    bad['parameters']['code_artifact']['inputs'] = {'payload': {'type': 'object'}}
    operations = [{'op': 'replace', 'path': '/mechanisms/0', 'value': bad},
        {'op': 'replace', 'path': '/mechanisms/0/parameters',
            'value': {**deepcopy(bad['parameters']), 'mechanism_id': ALPHA}}]
    if remove_again:
        operations += [{'op': 'add', 'path': '/mechanisms/0/inputs/0/port_id', 'value': 'payload'},
            {'op': 'remove', 'path': '/mechanisms/0/inputs/0/port_id'}]
    with pytest.raises(ir.AuthoringIRDiagnostic) as error:
        compile_document(None, operations)
    diagnostic = error.value.diagnostics[0]
    assert diagnostic['operation_index'] == (3 if remove_again else 0)
    assert diagnostic['path'] == '/mechanisms/0/inputs/0/port_id'
    assert diagnostic['actual_owner_id'] == ALPHA


@pytest.mark.parametrize('path,value', [('/mechanisms', {}), ('/mechanisms/1', None),
    ('/mechanisms/1/inputs', {}), ('/mechanisms/1/outputs', [None])])
def test_malformed_container_types_keep_existing_shape_diagnostics_and_next_prompt(path, value):
    body = request(); state = initial_draft(body)
    operations = [{'op': 'replace', 'path': path, 'value': value}]
    expected = ir.translate_operations(body['parent_system'], operations, stage='test')[0]
    action = {'tool': 'write_file', 'filename': 'system/mechanisms.json',
        'content': json.dumps(expected['mechanisms'])}
    state, receipt = apply(state, action, body)
    assert receipt['ok'] and not receipt['result']['validation']['valid']
    diagnostic = receipt['result']['validation']['errors'][0]['diagnostics'][0]
    assert diagnostic['message'] == 'system collection has the wrong JSON shape'
    assert 'missing_fields' not in diagnostic
    steps = [{'step': 0, 'status': 'applied', 'model_reply': {'output': action},
        'transition': receipt, 'errors': []}]
    for next_action in ({'tool': 'validate'}, finish()):
        state, returned = apply(state, next_action, body)
        steps.append({'step': len(steps), 'status': 'applied' if returned['ok'] else 'rejected',
            'model_reply': {'output': next_action}, 'transition': returned, 'errors': []})
    assert steps[1]['transition']['ok'] and not steps[1]['transition']['result']['valid']
    assert steps[2]['status'] == 'rejected' and steps[2]['transition']['errors']
    prompt = build_prompt(body, state, steps, image_id=IMAGE, binding_sha256='d' * 64,
        settings={'max_steps': 8})
    assert build_conversation(prompt, SYSTEM_PROMPT, native_tools=True)
    assert state['document'] == expected


@pytest.mark.parametrize('case', ['enum', 'unexpected-keyword', 'roles-type', 'port-channel-type'])
def test_present_but_wrong_types_or_keywords_are_not_misreported_as_missing_fields(case):
    document = request()['parent_system']
    if case == 'enum':
        document['mechanisms'][1]['family'] = []
        document['mechanisms'][1].pop('implementation')
    elif case == 'unexpected-keyword':
        document['artifact_types'] = [{'extra': 'retained literal'}]
    elif case == 'roles-type':
        document['agent_types'] = [{'agent_type_id': 'author', 'roles': 1}]
        document['artifact_types'] = [{}]
    else:
        document['mechanisms'][1]['inputs'] = [{'port_id': 'payload', 'channel': {}}]
        document['connections'] = [{}]
    with pytest.raises(ir.AuthoringIRDiagnostic) as error:
        compile_document(document)
    assert 'missing_fields' not in error.value.diagnostics[0]
    assert error.value.__cause__ is not None


@pytest.mark.parametrize('missing', ['mechanism_id', 'port_id', 'channel'])
def test_write_validate_finish_next_prompt_then_literal_multioperation_repair_cold_replays(tmp_path, missing):
    bad = code_node()
    path, replacement = '/mechanisms/0/mechanism_id', ALPHA
    if missing == 'mechanism_id':
        bad.pop(missing)
    else:
        port = {'port_id': 'payload', 'channel': 'artifact', 'artifact_type': None, 'required': False}
        replacement = port.pop(missing)
        bad['inputs'] = [port]
        bad['parameters']['code_artifact']['inputs'] = {'payload': {'type': 'object'}}
        path = '/mechanisms/0/inputs/0/' + missing
    bad['parameters']['literal'] = '研究者\n<tool_call>unchanged</tool_call>\\n'
    content = json.dumps(bad, ensure_ascii=False, indent=2)
    write = {'tool': 'write_file', 'filename': 'nodes/' + quote(ALPHA, safe='._-') + '.json', 'content': content}
    repairs = {'tool': 'edit', 'operations': [
        {'op': 'add', 'path': path, 'value': replacement},
        {'op': 'replace', 'path': '/mechanisms/0/parameters/gain', 'value': .75}]}
    actions = [PLAN, write, {'tool': 'validate'}, finish(), repairs, finish()]
    original = deepcopy(actions); body = request(); original_body = deepcopy(body)
    scripted = Model(actions)
    generator = author(scripted, tmp_path, max_steps=8)
    definition = generator(body)
    assert 'generation_failure' not in definition and len(scripted.calls) == 6
    cell = next(tmp_path.glob('generation-*'))
    rows = [json.loads((cell / f'step-{i:02d}.completed.json').read_text()) for i in range(6)]
    assert [row['status'] for row in rows] == ['applied', 'applied', 'applied', 'rejected', 'applied', 'finished']
    write_validation = rows[1]['transition']['result']['validation']
    validate_result = rows[2]['transition']['result']
    finish_errors = rows[3]['transition']['errors']
    assert not write_validation['valid'] and not validate_result['valid']
    assert write_validation['errors'] == validate_result['errors'] == finish_errors
    diagnostic = finish_errors[0]['diagnostics'][0]
    assert diagnostic['path'] == path and diagnostic['operation_index'] == 0
    assert rows[1]['model_reply']['output']['content'] == content
    assert rows[1]['transition']['result']['applied_operations'][0]['value'] == bad
    next_prompt = json.loads(scripted.calls[4]['prompt'])
    assert next_prompt['last_tool_response']['errors'] == finish_errors
    assert next_prompt['previous_steps'][3]['status'] == 'rejected'
    assert next_prompt['remaining_calls_including_this_one'] == 4
    assert build_conversation(scripted.calls[4]['prompt'], SYSTEM_PROMPT, native_tools=True)
    assert definition['provenance']['authoring_compiler']['raw_ir']['operations'][0]['value'] == bad
    before = {p.name: p.read_bytes() for p in cell.glob('*.json')}
    assert replay_staged_generation(cell) == definition and len(scripted.calls) == 6
    assert before == {p.name: p.read_bytes() for p in cell.glob('*.json')}
    assert body == original_body and original[1] == write


def test_transient_missing_fields_joint_repairs_and_arbitrary_valid_custom_nodes_do_not_call_diagnostic(monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError('required-field diagnostic is post-failure only')
    monkeypatch.setattr(ir, '_required_field_failure', forbidden)
    node = code_node('unlisted.authored.custom-node')
    operations = [{'op': 'remove', 'path': '/mechanisms/0/mechanism_id'},
        {'op': 'add', 'path': '/mechanisms/0/mechanism_id', 'value': ALPHA},
        {'op': 'add', 'path': '/mechanisms/-', 'value': node}]
    definition = compile_document(None, operations)
    assert definition['base_patch']['operations'] == operations
    assert definition['provenance']['authoring_compiler']['raw_ir']['operations'] == operations
    assert node['parameters']['code_artifact']['source'].startswith('raise RuntimeError')


def test_optional_original_e2_write_and_finish_diagnostic_preserve_raw_files():
    # No ignored/absolute artifacts are needed by normal tests.
    root = os.environ.get('SCIENCEUTOPIA_REQUIRED_FIELDS_E2_CELL')
    if not root:
        pytest.skip('optional original E2 read-only diagnostic not requested')
    cell = Path(root)
    names = ['request.json', 'step-06.started.json', 'step-06.completed.json', 'step-07.completed.json']
    originals = {name: (cell / name).read_bytes() for name in names}
    binding = json.loads(originals['request.json'])
    started = json.loads(originals['step-06.started.json'])
    actual = json.loads(originals['step-06.completed.json'])
    prior = json.loads(started['prompt'])
    action = actual['model_reply']['output']
    # Replay only literal JSON edits on a fresh in-memory draft; never run code.
    from utopia.optimization.native_staged_author_v15 import transition
    state = initial_draft(binding['request'])
    for i in range(6):
        old = json.loads((cell / f'step-{i:02d}.completed.json').read_text())
        if old['model_reply']['output'] is not None:
            state, _ = transition(state, old['model_reply']['output'], binding['request'],
                binding_sha256=binding['binding_sha256'], provider_binding=binding['provider_binding'])
    state, receipt = transition(state, action, binding['request'],
        binding_sha256=binding['binding_sha256'], provider_binding=binding['provider_binding'])
    assert receipt['ok'] and not receipt['result']['validation']['valid']
    diagnostic = receipt['result']['validation']['errors'][0]['diagnostics'][0]
    assert diagnostic['path'] == '/mechanisms/6/mechanism_id'
    assert diagnostic['actual_owner_id'] is None and diagnostic['actual_owner_implementation'] == 'code.python.v1'
    assert diagnostic['operation_index'] == len(state['operations']) - 1
    actual_finish = json.loads(originals['step-07.completed.json'])['model_reply']['output']
    same, finish_receipt = transition(state, actual_finish, binding['request'],
        binding_sha256=binding['binding_sha256'], provider_binding=binding['provider_binding'])
    assert same == state and not finish_receipt['ok']
    assert finish_receipt['errors'] == receipt['result']['validation']['errors']
    assert prior['last_model_action'] is not None or prior['last_call_errors']
    assert originals == {name: (cell / name).read_bytes() for name in names}
