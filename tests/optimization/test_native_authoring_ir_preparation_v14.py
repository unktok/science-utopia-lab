"""Pure preparation/CLI guards; no model tags, corpus/image access or inference.

The production manifest's inherited `no_calls_during_preparation` field means
no designer generation POST or native inference. Production preparation DOES
inspect model tags, load corpus identity and inspect the local sandbox image.
These tests replace those constructors and never perform that inspection.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from scripts import prepare_native_authoring_ir_qa_v14 as preparation
from tests.optimization.test_native_autonomous_driver_v14 import SOURCE, IMAGE, PROVIDER
from utopia.optimization.native_search_v14 import make_search_plan
from utopia.system.design_patch import digest
from utopia.system.native_open_examples import open_native_system

PROTOCOL_SHA = 'e' * 64
RUNTIME_BINDING = {'python_hash_seed_environment': '42', 'python_hash_probe': 123}


def inputs():
    loss = json.loads((Path(__file__).resolve().parents[2] /
        'research/objectives/losses/native-joint-v5-throughput.json').read_text())
    return {'source_commit': SOURCE, 'initial_system': open_native_system(IMAGE).to_dict(),
        'loss_spec': loss, 'provider_binding': deepcopy(PROVIDER),
        'runtime_seed_binding': deepcopy(RUNTIME_BINDING), 'protocol_sha256': PROTOCOL_SHA}


def test_pure_manifest_has_exact_source_request_loss_hashes_and_independent_qa_classification(monkeypatch):
    def forbidden(*args, **kwargs): pytest.fail('pure manifest must not construct any provider/image inspector')
    monkeypatch.setattr('utopia.optimization.native_factory.LocalQwenNativeFactory', forbidden)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor', forbidden)
    arguments = inputs(); original = deepcopy(arguments)
    value = preparation.build_manifest(**arguments)
    assert value['schema'] == 'scienceutopia.native-authoring-ir-technical-qa.v14'
    assert value['classification'] == 'actual-ui-native-authoring-ir-engineering-qa-v14'
    assert value['source_commit'] == SOURCE and value['protocol_sha256'] == PROTOCOL_SHA
    assert value['request_sha256'] == digest(value['request'])
    expected_plan = make_search_plan(value['request'], source_commit=SOURCE, provider_binding=PROVIDER)
    assert value['search_plan'] == expected_plan and value['plan_sha256'] == digest(expected_plan)
    assert value['operator_config'] == {'provider_binding': PROVIDER}
    assert value['runtime_seed_binding'] == RUNTIME_BINDING
    assert value['population'] == {'authors': 5, 'conference_setting': 1}
    assert value['native_experiment_binding'] == {'request_sha256': digest(value['request']),
        'loss_spec': arguments['loss_spec']}
    assert value['separate_from_closed_a1'] is True
    assert value['success_or_novelty_required'] is False and value['same_society_adoption'] is False
    # This is a declaration about generation/native inference, NOT a claim
    # that the production preparation CLI makes zero HTTP or metadata reads.
    assert value['no_calls_during_preparation'] is True
    assert 'content_sha256' not in value  # CLI seals this after pure construction.
    assert arguments == original and preparation.build_manifest(**arguments) == value


def test_loss_float_tokens_and_exact_hashes_are_preserved_without_numeric_normalization():
    arguments = inputs(); value = preparation.build_manifest(**arguments)
    loss = value['request']['loss_spec']
    assert loss == arguments['loss_spec']
    assert loss['id'] == 'native-joint-v5-throughput'
    assert type(loss['per_run']['intercept']) is float
    assert type(loss['per_run']['terms'][0]['coefficient']) is float
    assert type(loss['across_seeds']['dispersion_weight']) is float
    wire = json.dumps(value['request'], allow_nan=False)
    assert '"coefficient": -1.0' in wire
    assert digest(json.loads(wire)) == value['request_sha256']
    normalized = deepcopy(value['request'])
    normalized['loss_spec']['per_run']['terms'][0]['coefficient'] = -1
    assert normalized == value['request']  # Numeric equality is weaker than exact JSON binding.
    assert digest(normalized) != value['request_sha256']
    assert digest(value['native_experiment_binding']['loss_spec']) == digest(arguments['loss_spec'])


def test_exact_two_slot_four_post_budget_no_replacement_or_success_condition():
    value = preparation.build_manifest(**inputs()); request = value['request']
    assert request['schema'] == 'scienceutopia.native-search-request.v14'
    assert request['method'] == 'blackbox' and request['native_budget'] == 2
    assert request['seed'] == request['initial_system']['initial_state']['seed'] == 42
    assert request['years'] == 2
    assert request['designer'] == {'model': 'qwen3:8b', 'max_attempts': 2, 'max_tokens': 4096}
    assert value['search_plan']['stage_counts'] == [1, 1]
    assert value['search_plan']['generator_calls'] == 2
    assert value['search_plan']['maximum_designer_provider_attempts'] == 4
    assert value['budget'] == {'scheduled_native_slots': 2, 'free_generations': 2,
        'maximum_generation_POSTs': 4, 'maximum_digest_preflight_GETs': 4, 'replacement_policy': 'none'}
    # The four preflight GETs here belong to at most four generation attempts;
    # production preparation's own model-tag/image/corpus inspection is separate.
    assert value['budget']['maximum_generation_POSTs'] == request['native_budget'] * request['designer']['max_attempts']


def test_manifest_copies_operator_inputs_without_shared_mutable_aliases():
    arguments = inputs(); original = deepcopy(arguments)
    value = preparation.build_manifest(**arguments)
    value['request']['loss_spec']['per_run']['terms'][0]['coefficient'] = -99.
    value['request']['initial_system']['metadata']['scripted-mutation'] = True
    value['operator_config']['provider_binding']['dataset_identity']['scripted-mutation'] = True
    value['runtime_seed_binding']['python_hash_probe'] = 999
    assert arguments == original
    assert value['native_experiment_binding']['loss_spec'] == original['loss_spec']
    assert value['search_plan']['request']['loss_spec'] == original['loss_spec']


@pytest.mark.parametrize('source', ['main', 'a' * 7, '', 'g' * 40])
def test_manifest_rejects_unpinned_source(source):
    arguments = inputs(); arguments['source_commit'] = source
    with pytest.raises(ValueError, match='source'):
        preparation.build_manifest(**arguments)


@pytest.mark.parametrize('existing_kind', ['directory', 'file'])
def test_cli_refuses_existing_destination_before_provider_or_image_construction(tmp_path, monkeypatch, existing_kind):
    output = tmp_path / 'frozen-qa'
    if existing_kind == 'directory':
        output.mkdir(); sentinel = output / 'manifest.json'
    else:
        sentinel = output
    sentinel.write_text('SCRIPTED frozen content must remain exact')
    before = sentinel.read_bytes()
    constructions = []
    def forbidden(*args, **kwargs):
        constructions.append('unexpected provider/image/writer construction')
        pytest.fail('existing destination must fail before metadata inspection, generation or native inference')
    monkeypatch.setattr(preparation, 'pinned_revision', lambda root: SOURCE)
    monkeypatch.setattr(preparation, 'write_json_atomic', forbidden)
    monkeypatch.setattr('utopia.optimization.native_factory.LocalQwenNativeFactory', forbidden)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor', forbidden)
    monkeypatch.setattr(sys, 'argv', ['prepare_native_authoring_ir_qa_v14.py',
        '--output', str(output), '--data-cache', str(tmp_path / 'not-opened-cache')])
    with pytest.raises(ValueError, match='fresh prospective QA output directory'):
        preparation.main()
    assert constructions == [] and sentinel.read_bytes() == before
    assert not (tmp_path / 'not-opened-cache').exists()
