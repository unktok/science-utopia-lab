"""Boundary authoring software QA, never an additional live Qwen draft."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from tests.optimization.test_native_free_source import recorded_selection
from tests.optimization.test_native_region_ir import fixture_ir
from tests.optimization.test_native_region_proposer import Model
from tests.optimization.test_native_world import loss_spec
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_region_ir import boundary_contract, region_ir_schema
from utopia.optimization.native_region_proposer_v5a2 import (
    NativeBoundaryRegionProposer, boundary_examples_a2, designer_boundary_a2, scoped_authoring_schema_a2)
from utopia.system.code_mechanisms import sha
from utopia.system.native_kernel import legacy_world_system
from utopia.system.native_selection_slot import selection_source_slot


def contract_fixture():
    parent = selection_source_slot(legacy_world_system(), image_id='sha256:' + 'a' * 64)
    return boundary_contract(parent, ['world.selection'])


def test_first_node_is_external_only_but_later_free_explicit_wires_remain():
    contract = contract_fixture()
    old, amended = Draft202012Validator(region_ir_schema(contract)), Draft202012Validator(scoped_authoring_schema_a2(contract))
    valid = fixture_ir()
    amended.validate(valid)
    assert amended.schema['properties']['nodes']['prefixItems'][0]['properties']['inputs']['additionalProperties']['properties']['sources']['items']['enum'] == ['boundary:next', 'boundary:world']
    for source in ('node:world.review:packets', 'boundary:observations', 'boundary:after'):
        bad = deepcopy(valid)
        bad['nodes'][0]['inputs']['evidence']['sources'] = [source]
        assert list(amended.iter_errors(bad))
        old.validate(bad)  # Historical v5 schema has NOT silently changed.
    assert valid['nodes'][1]['inputs']['dossier']['sources'] == ['node:world.review:packets']


def test_designer_boundary_has_scoped_refs_real_types_separate_payload_schemas():
    view = designer_boundary_a2(contract_fixture())
    assert set(view['inputs']) == {'next', 'world'} and set(view['exports']) == {'after', 'decisions'}
    for alias, endpoint in view['inputs'].items():
        assert endpoint['reference'] == 'boundary:' + alias
        assert endpoint['payload_schema'] == {'type': 'object'}
        assert set(endpoint) == {'reference', 'channel', 'artifact_type', 'payload_schema'}
    for endpoint in view['exports'].values():
        assert set(endpoint) == {'channel', 'artifact_type', 'payload_schema'}
    assert 'world.review' not in json.dumps(view) and 'world.publication' not in json.dumps(view)


def test_actual_ingress_projection_is_alias_aligned_and_raw_records_unchanged(recorded_selection):
    campaign, _, _, provider = recorded_selection
    rows = provider('world.selection', campaign.initial, campaign.state['records'])
    before = sha(rows)
    examples = boundary_examples_a2(campaign.initial, ['world.selection'], rows)
    assert sha(rows) == before
    assert [e['period'] for e in examples] == list(range(1, 7))
    for example in examples:
        assert set(example['boundary_inputs']) == {'next', 'world'}
        assert example['boundary_inputs']['world'][0]['payload']['schema'] == 'scienceutopia.native-world-observation.v1'
        assert example['boundary_inputs']['next'][0]['payload']['year'] == example['period']
        encoded = json.dumps(example)
        assert 'source_mechanism' not in encoded
        assert 'world.review' not in encoded and 'world.publication' not in encoded
        assert 'observations' not in example['boundary_inputs'] and 'after' not in example['boundary_inputs']


def test_durable_a2_repair_exact_source_probe_and_resume(recorded_selection, tmp_path):
    campaign, _, executor, provider = recorded_selection
    valid = fixture_ir()
    invalid = deepcopy(valid)
    invalid['nodes'][0]['inputs']['evidence']['sources'] = ['node:world.review:packets']
    model = Model(invalid, valid)
    proposer = NativeBoundaryRegionProposer(model, executor, removed_nodes=['world.selection'],
        context_provider=provider, receipts=tmp_path / 'a2')
    args = campaign.initial, campaign.state['records'], 1, loss_spec()
    patch = proposer(*args)
    assert proposer(*args) == patch and len(model.calls) == 2
    first = json.loads((tmp_path / 'a2/region-1-0.json').read_text())
    second = json.loads((tmp_path / 'a2/region-1-1.json').read_text())
    prompt = json.loads(model.calls[0]['prompt'])
    assert first['binding']['schema'] == 'scienceutopia.native-region-proposal.v5a2'
    assert first['loss'] is None and 'node:world.review:packets' in first['error']
    assert 'boundary:next' in first['error'] and 'boundary:world' in first['error']
    assert second['previous_receipt_sha256'] == first['receipt_sha256']
    assert second['generated'] == valid and len(second['runs']) == 6
    assert first['error'] in model.calls[1]['prompt']
    assert prompt['source_reference_rules']['first_node_sources'] == ['boundary:next', 'boundary:world']
    assert set(prompt['actual_native_boundary_examples'][0]['boundary_inputs']) == {'next', 'world'}
    assert 'world.review' not in model.calls[0]['prompt'] and 'world.publication' not in model.calls[0]['prompt']
    assert prompt['return_syntax_example_NOT_algorithm']['outputs']['YOUR_OUTPUT_PORT'][0]['payload'] == {'YOUR_FIELD': 'YOUR_VALUE'}
    first['error'] = 'tampered'
    (tmp_path / 'a2/region-1-0.json').write_text(json.dumps(first))
    with pytest.raises(ValueError, match='binding/hash changed'):
        proposer(*args)


def test_durable_a2_interruption_does_not_query_again(recorded_selection, tmp_path):
    campaign, _, executor, provider = recorded_selection
    class Interrupt:
        image_id = executor.image_id
        def execute(self, *args): raise KeyboardInterrupt('QA interruption')
    model = Model(fixture_ir())
    options = dict(removed_nodes=['world.selection'], context_provider=provider, receipts=tmp_path / 'a2')
    args = campaign.initial, campaign.state['records'], 1, loss_spec()
    with pytest.raises(KeyboardInterrupt):
        NativeBoundaryRegionProposer(model, Interrupt(), **options)(*args)
    assert NativeBoundaryRegionProposer(model, executor, **options)(*args)
    assert len(model.calls) == 1
