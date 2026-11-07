"""Read-only literal consumer declarations; no model/code/tensor/native execution."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from tests.optimization.test_native_authoring_ir import request, BINDING, IMAGE
from utopia.optimization.native_contract_notices import downstream_tensor_contracts
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING, CONVERSATION_PROFILES
from utopia.optimization.native_file_workspace_v35 import read_file, file_downstream_contracts
from utopia.optimization.native_staged_author_v15 import initial_draft, transition
from utopia.system.design_patch import digest
from utopia.system.native_open_examples import open_native_system
from utopia.utils.data_utils import file_sha256


def native():
    return open_native_system(IMAGE).to_dict()


def position(document, identity):
    return next(i for i, node in enumerate(document['mechanisms']) if node['mechanism_id'] == identity)


def test_actual_original_graph_declares_consuming_shape_keys_and_exact_file_refs():
    document = native(); before = deepcopy(document)
    producer = position(document, 'native-feature-extractor')
    consumer = position(document, 'addressed-selection')
    summary = downstream_tensor_contracts(document, producer)
    assert document == before and summary['document_sha256'] == digest(document)
    assert summary['total_count'] == summary['included_count'] == 1 and summary['complete']
    row = summary['notices'][0]
    assert row['consumer_filename'] == f'positions/{consumer}.json'
    declared = row['declaration']
    assert declared['bound_tensor_inputs'] == [{'tensor_input': 'features',
        'literal_binding': {'port': 'features', 'path': '/values'},
        'declared_shape_present': True, 'declared_shape': [-1, 2]}]
    assert declared['consumer_configuration']['program_parameters']['keys'] == [[.6, -.2], [-.3, .5]]
    assert declared['producer_output_ports'][0]['port_id'] == 'features'
    assert declared['consumer_input_ports'][0]['port_id'] == 'features'
    assert not summary['changes_validity'] and summary['warning_is_not_a_veto']
    assert not summary['native_execution_performed'] and not summary['authored_value_changed_by_host']


def test_bounded_code_read_and_write_receipts_show_contract_without_repair_or_veto():
    body = request(); body['parent_system'] = native(); state = initial_draft(body)
    original = deepcopy(state)
    _, read = transition(state, {'tool': 'read_file', 'filename': 'code/native-feature-extractor.py'}, body,
        binding_sha256='d'*64, provider_binding=BINDING, conversation_profile=BOUNDED_AUTHORING)
    assert read['ok'] and 'declared_downstream_tensor_contracts' in read['result']
    producer = position(state['document'], 'native-feature-extractor')
    source = state['document']['mechanisms'][producer]['parameters']['code_artifact']['source']
    changed = source.replace('values.append([score, len(reviews)])', 'values.append([score, len(reviews), 7, 11])')
    assert changed != source
    updated, written = transition(state, {'tool': 'write_file', 'filename': 'code/native-feature-extractor.py',
        'content': changed}, body, binding_sha256='d'*64, provider_binding=BINDING,
        conversation_profile=BOUNDED_AUTHORING)
    assert state == original and written['ok'] and written['result']['validation']['valid']
    assert updated['document']['mechanisms'][producer]['parameters']['code_artifact']['source'] == changed
    notice = written['result']['declared_downstream_tensor_contracts']['notices'][0]
    assert notice['declaration']['bound_tensor_inputs'][0]['declared_shape'] == [-1, 2]
    consumer = position(state['document'], 'addressed-selection')
    assert updated['document']['mechanisms'][consumer] == state['document']['mechanisms'][consumer]
    # No output inference: opaque incompatible-looking code remains legal to
    # submit; only an actual later native execution can establish its failure.
    unchanged, finished = transition(updated, {'tool': 'finish'}, body, binding_sha256='d'*64,
        provider_binding=BINDING, conversation_profile=BOUNDED_AUTHORING)
    assert unchanged == updated and finished['ok'] and finished['result']['valid']


def test_new_advisory_receipts_cold_replay_without_more_model_or_code_calls(tmp_path):
    from tests.optimization.test_native_bounded_author_context_v45 import Model
    from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator, replay_staged_generation
    body = request(); body['parent_system'] = native()
    producer = position(body['parent_system'], 'native-feature-extractor')
    source = body['parent_system']['mechanisms'][producer]['parameters']['code_artifact']['source']
    actions = [{'tool': 'plan', 'objective_reasoning': 'SCRIPTED QA', 'design_intent': 'SCRIPTED QA'},
        {'tool': 'read_file', 'filename': 'code/native-feature-extractor.py'},
        {'tool': 'write_file', 'filename': 'code/native-feature-extractor.py', 'content': source + '\n# SCRIPTED literal edit\n'},
        {'tool': 'finish'}]
    model = Model(actions)
    generator = StagedVocabularyGenerator(model, tmp_path / 'author', image_id=IMAGE,
        provider_binding=BINDING, max_steps=16, max_tokens=8192, conversation_profile=BOUNDED_AUTHORING)
    definition = generator(body)
    cell = next((tmp_path / 'author').glob('generation-*'))
    paths = sorted(p for p in cell.rglob('*') if p.is_file())
    before = {str(p): file_sha256(p) for p in paths}
    assert replay_staged_generation(cell) == definition
    assert {str(p): file_sha256(p) for p in paths} == before and len(model.calls) == 4
    for step in (1, 2):
        receipt = json.loads((cell / f'step-{step:02d}.completed.json').read_text())['transition']
        assert receipt['result']['declared_downstream_tensor_contracts']['total_count'] == 1


@pytest.mark.parametrize('profile', [p for p in CONVERSATION_PROFILES if p != BOUNDED_AUTHORING])
def test_other_profiles_and_immutable_references_keep_original_read_semantics(profile):
    document = native()
    result = read_file(document, 'code/native-feature-extractor.py', conversation_profile=profile)
    assert 'declared_downstream_tensor_contracts' not in result
    assert result['content'] == document['mechanisms'][position(document, 'native-feature-extractor')]['parameters']['code_artifact']['source']
    assert file_downstream_contracts(document, 'code/native-feature-extractor.py', conversation_profile=profile) is None
    parent = read_file(document, 'parent/code/native-feature-extractor.py',
        request={'parent_system': document}, conversation_profile=BOUNDED_AUTHORING)
    assert parent['read_only'] and 'declared_downstream_tensor_contracts' not in parent


def test_renamed_rewired_nodes_ports_paths_and_custom_shapes_are_literal_not_hardcoded():
    document = native()
    producer = document['mechanisms'][position(document, 'native-feature-extractor')]
    consumer_position = position(document, 'addressed-selection')
    consumer = document['mechanisms'][consumer_position]
    producer['mechanism_id'], consumer['mechanism_id'] = 'invented/source~one', 'institution/new~two'
    producer['outputs'][0]['port_id'], consumer['inputs'][0]['port_id'] = 'samples', 'signal'
    consumer['parameters']['input_bindings'] = {'embedding': {'port': 'signal', 'path': '/new/numeric~field'}}
    consumer['parameters']['program']['inputs'] = {'embedding': [-1, 4, 7]}
    config = {'projection': [[1.], [2.], [3.], [4.]], 'literal_annotation': '<system>data only</system>'}
    consumer['parameters']['program']['parameters'] = deepcopy(config)
    document['connections'] = [{'source_mechanism': producer['mechanism_id'], 'source_port': 'samples',
        'target_mechanism': consumer['mechanism_id'], 'target_port': 'signal', 'channel': 'artifact'}]
    before = deepcopy(document)
    result = file_downstream_contracts(document, 'code/invented%2Fsource~one.py',
        conversation_profile=BOUNDED_AUTHORING)
    assert result['total_count'] == 1 and document == before
    row = result['notices'][0]
    assert row['consumer_filename'] == f'positions/{consumer_position}.json'
    assert row['declaration']['bound_tensor_inputs'][0] == {'tensor_input': 'embedding',
        'literal_binding': {'port': 'signal', 'path': '/new/numeric~field'},
        'declared_shape_present': True, 'declared_shape': [-1, 4, 7]}
    assert row['declaration']['consumer_configuration']['program_parameters'] == config


def test_no_assumption_that_an_intermediate_custom_mechanism_forwards_same_tensor():
    document = native(); producer = position(document, 'native-feature-extractor')
    source_edge = next(e for e in document['connections'] if e['source_mechanism'] == 'native-feature-extractor'
        and e['target_mechanism'] == 'addressed-selection')
    relay = deepcopy(document['mechanisms'][producer]); relay['mechanism_id'] = 'opaque-transformer'
    document['mechanisms'].append(relay)
    document['connections'].append({**source_edge, 'source_mechanism': 'opaque-transformer'})
    source_edge['target_mechanism'] = 'opaque-transformer'
    assert downstream_tensor_contracts(document, producer)['total_count'] == 0
    assert downstream_tensor_contracts(document, len(document['mechanisms']) - 1)['total_count'] == 1


def test_multiple_consumers_and_oversized_config_use_complete_declaration_refs():
    document = native(); producer = position(document, 'native-feature-extractor')
    target = document['mechanisms'][position(document, 'addressed-selection')]
    target['parameters']['program']['parameters']['huge_literal'] = 'do-not-truncate-研究者' * 2000
    for index in range(12):
        copied = deepcopy(target); copied['mechanism_id'] = f'other-consumer-{index}'
        document['mechanisms'].append(copied)
        document['connections'].append({'source_mechanism': 'native-feature-extractor', 'source_port': 'features',
            'target_mechanism': copied['mechanism_id'], 'target_port': 'features', 'channel': 'artifact'})
    summary = downstream_tensor_contracts(document, producer)
    assert summary['total_count'] == 13 and summary['omitted_count'] > 0 and not summary['complete']
    assert len(json.dumps(summary, ensure_ascii=False).encode()) <= 8192
    for row in summary['notices']:
        assert not row['declaration_included'] and 'declaration' not in row
        assert row['consumer_filename'].startswith('positions/') and len(row['declaration_sha256']) == 64
    assert target['parameters']['program']['parameters']['huge_literal'].endswith('研究者')


@pytest.mark.parametrize('mutation', ['duplicate-producer', 'duplicate-consumer', 'missing-target',
    'invalid-ports', 'invalid-connections', 'invalid-nodes'])
def test_invalid_intermediate_graph_is_not_repaired_or_arbitrarily_disambiguated(mutation):
    document = native(); producer = position(document, 'native-feature-extractor')
    if mutation == 'duplicate-producer':
        document['mechanisms'].append(deepcopy(document['mechanisms'][producer]))
    elif mutation == 'duplicate-consumer':
        document['mechanisms'].append(deepcopy(document['mechanisms'][position(document, 'addressed-selection')]))
    elif mutation == 'missing-target':
        document['connections'] = [None, {'source_mechanism': 'native-feature-extractor', 'source_port': 'features'}]
    elif mutation == 'invalid-ports':
        document['mechanisms'][producer]['outputs'] = None
        document['mechanisms'][position(document, 'addressed-selection')]['inputs'] = 17
    elif mutation == 'invalid-connections':
        document['connections'] = 17
    else:
        document['mechanisms'] = None
    before = deepcopy(document)
    summary = downstream_tensor_contracts(document, producer)
    assert document == before and not summary['changes_validity']
    if mutation in ('duplicate-producer', 'duplicate-consumer', 'missing-target'):
        assert summary['notices'] == []


def test_optional_actual_failed_candidate_and_raw_receipts_remain_unchanged():
    root = Path('/Users/shiro/unktok/dev/science-utopia-lab/outputs/native-warmstart-v45-a1/arms/efficiency')
    system = root / 'worlds/native-adaptive-b8d9b184246514d636486da8-s42/system.json'
    paths = [system, system.parent / 'code-contexts.jsonl', root / 'campaign/native-adaptive-state.json']
    if not all(path.is_file() for path in paths):
        pytest.skip('optional immutable actual V45 failure evidence unavailable')
    hashes = {str(p): file_sha256(p) for p in paths}
    document = json.loads(system.read_text())
    notice = downstream_tensor_contracts(document, position(document, 'native-feature-extractor'))
    assert notice['notices'][0]['declaration']['bound_tensor_inputs'][0]['declared_shape'] == [-1, 2]
    assert {str(p): file_sha256(p) for p in paths} == hashes
