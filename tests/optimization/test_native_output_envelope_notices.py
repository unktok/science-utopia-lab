"""Offline conditional advice; no provider, container or authored-code execution."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from tests.optimization.test_native_authoring_ir import request, BINDING, IMAGE
from utopia.optimization.native_contract_notices import contract_notices
from utopia.optimization.native_staged_author_v15 import initial_draft, transition
from utopia.system.code_mechanisms import CodeExecutionError, validate_code_result
from utopia.utils.data_utils import file_sha256


NOTICE = 'potential-input-payload-without-output-envelope'
SOURCE = """def step(context):
    observations_in = context['inputs']['observations'][0]['payload']
    return {'outputs': {'world': [observations_in]}, 'state': {}}
"""


def document(source=SOURCE):
    value = request()['parent_system']
    node = value['mechanisms'][0]
    artifact = node['parameters']['code_artifact']
    node['inputs'] = [{'port_id': 'observations', 'channel': 'artifact', 'required': False}]
    node['outputs'] = [{'port_id': 'world', 'channel': 'artifact', 'required': False}]
    artifact.update(source=source, inputs={'observations': {'type': 'object'}},
        outputs={'world': {'type': 'object'}})
    return value


def notices(value):
    return [row for row in contract_notices(value) if row['code'] == NOTICE]


def test_observed_failure_shape_is_explained_without_execution_repair_or_mutation():
    value = document(); before = deepcopy(value)
    rows = notices(value)
    assert value == before and len(rows) == 1
    row = rows[0]
    assert row['input_port'] == 'observations' and row['output_port'] == 'world'
    assert row['payload_variable'] == 'observations_in' and row['line'] == 3
    assert not row['changes_validity'] and not row['authored_value_changed_by_host']
    assert not row['native_execution_performed']
    artifact = value['mechanisms'][0]['parameters']['code_artifact']
    payload = {'conferences': {'conferences': []}, 'year': 2016}
    result = {'outputs': {'world': [payload]}, 'state': {}}
    original = deepcopy(result)
    with pytest.raises(CodeExecutionError, match=r"outputs\['world'\] record must be"):
        validate_code_result(artifact, result)
    assert result == original
    validate_code_result(artifact, {'outputs': {'world': [{'payload': payload}]}, 'state': {}})


@pytest.mark.parametrize('source', [
    SOURCE.replace('[observations_in]', "[{'payload': observations_in}]"),
    SOURCE.replace('[observations_in]', '[]'),
    SOURCE.replace('[observations_in]', '[opaque(observations_in)]'),
    SOURCE.replace("    return", "    observations_in = {}\n    return"),
    'this source is deliberately not executable python',
])
def test_wrapped_empty_opaque_or_rebound_values_are_not_inferred(source):
    assert notices(document(source)) == []


def test_literal_reads_renamed_entry_argument_ports_and_process_delegate_are_preserved():
    source = """def step(frame, /):
    return {'outputs': {'a/b~c': [frame['inputs']['raw/new'][2]['payload']]}, 'state': {}}
"""
    value = document(source); node = value['mechanisms'][0]
    artifact = node['parameters']['code_artifact']
    artifact['inputs'] = {'raw/new': {'type': 'object'}}
    artifact['outputs'] = {'a/b~c': {'type': 'object'}}
    value['mechanisms'] = [{'mechanism_id': 'outer', 'implementation': 'native.process.activity.v1',
        'parameters': {'delegate': node}}]
    before = deepcopy(value)
    row, = notices(value)
    assert value == before and row['mechanism_id'] == 'outer'
    assert row['executed_mechanism_id'] == node['mechanism_id']
    assert row['path'] == '/mechanisms/0/parameters/delegate/parameters/code_artifact/source'
    assert row['input_port'] == 'raw/new' and row['output_port'] == 'a/b~c'
    assert row['payload_variable'] is None


def test_payload_that_is_already_an_envelope_is_legal_despite_conditional_notice():
    value = document(); artifact = value['mechanisms'][0]['parameters']['code_artifact']
    assert len(notices(value)) == 1
    # This data could be an intentional input payload. Syntax cannot decide it.
    input_payload = {'payload': {'nested': True}, 'actor_ids': ['actor']}
    validate_code_result(artifact, {'outputs': {'world': [input_payload]}, 'state': {}})


def test_static_validation_and_explicit_finish_remain_legal_with_advice():
    body = request(); body['parent_system'] = document()
    state = initial_draft(body); before = deepcopy(state)
    unchanged, receipt = transition(state, {'tool': 'finish', 'rationale': 'SCRIPTED conditional advice'}, body,
        binding_sha256='d'*64, provider_binding=BINDING)
    assert unchanged == before and state == before
    assert receipt['ok'] and receipt['result']['valid'] and receipt['definition'] is not None
    row, = [n for n in receipt['result']['execution_contract_notices']['notices'] if n['code'] == NOTICE]
    assert not row['changes_validity']


def test_new_notice_cold_replays_without_extra_model_calls_or_source_evaluation(tmp_path):
    from tests.optimization.test_native_bounded_author_context_v45 import Model
    from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator, replay_staged_generation
    from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
    body = request(); body['parent_system'] = document()
    actions = [{'tool': 'plan', 'objective_reasoning': 'SCRIPTED', 'design_intent': 'SCRIPTED'},
        {'tool': 'finish'}]
    model = Model(actions)
    generator = StagedVocabularyGenerator(model, tmp_path / 'author', image_id=IMAGE,
        provider_binding=BINDING, max_steps=16, max_tokens=8192, conversation_profile=BOUNDED_AUTHORING)
    definition = generator(body)
    assert 'generation_failure' not in definition
    cell = next((tmp_path / 'author').glob('generation-*'))
    paths = [p for p in cell.rglob('*') if p.is_file()]
    hashes = {str(p): file_sha256(p) for p in paths}
    assert replay_staged_generation(cell) == definition and len(model.calls) == 2
    assert {str(p): file_sha256(p) for p in paths} == hashes


def test_optional_actual_failed_candidate_is_not_changed_or_rerun():
    root = Path('/Users/shiro/unktok/dev/science-utopia-lab-experiments/pre-scale-search-v1-a1/outputs/pre-scale-search-v1-a1/search/run-00/efficiency--code-fixed-graph')
    state_path = root / 'campaign/native-adaptive-state.json'
    system_path = root / 'worlds/native-adaptive-861dc934151ea50b23067a4d-s41001/system.json'
    if not state_path.is_file() or not system_path.is_file():
        pytest.skip('optional immutable actual pre-scale E failure evidence unavailable')
    paths = [state_path, system_path]
    hashes = {str(p): file_sha256(p) for p in paths}
    value = json.loads(system_path.read_text())
    rows = notices(value)
    assert any(row['input_port'] == 'observations' and row['output_port'] == 'world' for row in rows)
    record = json.loads(state_path.read_text())['records'][0]
    assert record['generation_error'] is None
    assert record['observations'][0]['status'] == 'failed'
    assert record['observations'][0]['loss'] is None
    assert {str(p): file_sha256(p) for p in paths} == hashes
