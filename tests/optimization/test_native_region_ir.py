"""Explicit developer QA graphs; these fixtures are not model-invention evidence."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_free_source import recorded_selection
from tests.optimization.test_native_region_design import fixture_manifest
from tests.optimization.test_native_region_proposer import Model
from tests.optimization.test_native_world import loss_spec
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_region_ir import boundary_contract, compile_region_ir, lower_region_ir
from utopia.optimization.native_region_proposer_v5 import NativeRegionIRProposer, _prior_generated_regions
from utopia.system.design_patch import apply_design_patch


def fixture_ir():
    manifest = fixture_manifest()
    aliases = {'qa-evidence-commons': 'world.review', 'qa-decision-assembly': 'assembly'}
    nodes = []
    for node in manifest['nodes']:
        inputs = {}
        for port in node['inputs']:
            sources = []
            for edge in manifest['connections']:
                if (edge['target_mechanism'], edge['target_port']) == (node['mechanism_id'], port['port_id']):
                    source = edge['source_mechanism']
                    sources.append('node:' + aliases[source] + ':' + edge['source_port'] if source in aliases
                        else 'boundary:' + edge['source_port'])
            inputs[port['port_id']] = {'sources': sources, 'required': port['required'], 'schema': node['input_schemas'][port['port_id']]}
        outputs = {p['port_id']: {'channel': p['channel'], 'artifact_type': p['artifact_type'],
            'required': p['required'], 'schema': node['output_schemas'][p['port_id']]} for p in node['outputs']}
        nodes.append({'id': aliases[node['mechanism_id']], 'inputs': inputs, 'outputs': outputs,
            'parameters': node['parameters'], 'python_code': node['python_code'], 'state_schema': node['state_schema']})
    return {'rationale': 'Explicit QA algorithm and graph; not model-generated', 'nodes': nodes,
        'exports': {'after': ['node:assembly:ready'], 'decisions': ['node:assembly:verdicts']}}


def test_prior_generated_source_visible_with_loss_even_if_not_current_best():
    source = 'def step(context):\n    return context\n'
    system = {'metadata': {'native_design_region': {'node_ids': ['generated-local']}},
        'mechanisms': [{'mechanism_id': 'generated-local', 'parameters': {'code_artifact': {'source': source}}},
            {'mechanism_id': 'host', 'parameters': {'secret_original_source': 'MUST_NOT_APPEAR'}}],
        'connections': [{'source_mechanism': 'host', 'target_mechanism': 'generated-local'}],
        'schedules': [{'mechanism_id': 'generated-local', 'phase': 140}]}
    history = [{'suggestion': {'candidate': system, 'proposal_index': i},
        'observation': {'loss': i * 10, 'status': 'complete'}} for i in range(3)]
    view = _prior_generated_regions(history)
    assert [r['index'] for r in view['regions']] == [1, 2]
    assert [r['actual_loss'] for r in view['regions']] == [10, 20]
    assert view['source_visibility_notice']['older_generated_sources_omitted'] == 1
    assert view['regions'][-1]['region']['mechanisms'][0]['parameters']['code_artifact']['source'] == source
    assert 'MUST_NOT_APPEAR' not in json.dumps(view)


def test_scoped_host_names_free_protocol_source_and_explicit_wires(recorded_selection):
    campaign, _, executor, _ = recorded_selection
    value = fixture_ir()
    manifest = lower_region_ir(campaign.initial, value, removed_nodes=['world.selection'])
    assert [n['python_code'] for n in manifest['nodes']] == [n['python_code'] for n in value['nodes']]
    assert [n['phase'] for n in manifest['nodes']] == [133, 146]
    assert len(manifest['connections']) == 5
    assert manifest['nodes'][0]['mechanism_id'].startswith('generated-')
    assert manifest['nodes'][0]['mechanism_id'].endswith('.world.review')
    assert lower_region_ir(campaign.initial, json.loads(json.dumps(value, sort_keys=True)),
        removed_nodes=['world.selection']) == manifest
    patch, child = compile_region_ir(campaign.initial, value, removed_nodes=['world.selection'], image_id=executor.image_id)
    assert apply_design_patch(campaign.initial, patch) == child
    assert 'world.review' in {n.mechanism_id for n in child.mechanisms}
    assert 'world.selection' not in {n.mechanism_id for n in child.mechanisms}


@pytest.mark.parametrize('mutation,match', [
    (lambda v: v['exports'].pop('after'), 'required property'),
    (lambda v: v['exports'].update(after=['boundary:next']), 'exports must'),
    (lambda v: v['nodes'][0]['inputs']['evidence'].update(sources=['boundary:missing']), 'unknown explicit boundary'),
    (lambda v: v['nodes'][0]['inputs']['evidence'].update(sources=['node:assembly:ready']), 'chosen node array order'),
    (lambda v: v['exports'].update(decisions=['node:assembly:ready']), 'disagrees with native boundary'),
    (lambda v: v['nodes'][1].update(id='world.review'), 'duplicate scoped'),
    (lambda v: v['nodes'][0]['inputs']['evidence'].update(sources=['boundary:world', 'boundary:next']), 'merged sources'),
])
def test_no_missing_connections_unknown_refs_or_type_repairs(recorded_selection, mutation, match):
    campaign, _, _, _ = recorded_selection
    value = fixture_ir()
    mutation(value)
    with pytest.raises(Exception, match=match):
        lower_region_ir(campaign.initial, value, removed_nodes=['world.selection'])


def test_durable_generation_probe_resume_and_objective_binding(recorded_selection, tmp_path):
    campaign, _, executor, provider = recorded_selection
    draft = fixture_ir()
    model = Model(draft)
    proposer = NativeRegionIRProposer(model, executor, removed_nodes=['world.selection'],
        context_provider=provider, receipts=tmp_path / 'ir')
    args = campaign.initial, campaign.state['records'], 1, loss_spec()
    patch = proposer(*args)
    assert proposer(*args) == patch and len(model.calls) == 1
    receipt = json.loads((tmp_path / 'ir/region-1-0.json').read_text())
    assert receipt['generated'] == draft and receipt['loss'] is None
    assert len(receipt['runs']) == 6
    assert len(model.calls[0]['prompt'].encode()) < 15000
    assert json.loads(model.calls[0]['prompt'])['loss_spec'] == loss_spec()
    assert 'incumbent_generated_region' not in json.loads(model.calls[0]['prompt'])
    changed = deepcopy(loss_spec())
    changed['version'] = 'another-objective'
    with pytest.raises(ValueError, match='prompt/binding changed'):
        proposer(*args[:3], changed)


def test_repair_preserves_raw_ir_and_hash_chain(recorded_selection, tmp_path):
    campaign, _, executor, provider = recorded_selection
    valid = fixture_ir()
    invalid = deepcopy(valid)
    invalid['exports']['decisions'] = ['node:assembly:ready']
    model = Model(invalid, valid)
    proposer = NativeRegionIRProposer(model, executor, removed_nodes=['world.selection'],
        context_provider=provider, receipts=tmp_path / 'ir')
    args = campaign.initial, campaign.state['records'], 1, loss_spec()
    proposer(*args)
    first = json.loads((tmp_path / 'ir/region-1-0.json').read_text())
    second = json.loads((tmp_path / 'ir/region-1-1.json').read_text())
    assert first['generated'] == invalid and first['loss'] is None
    assert second['previous_receipt_sha256'] == first['receipt_sha256']
    assert first['error'] in model.calls[1]['prompt']
    proposer(*args)
    assert len(model.calls) == 2
    first['error'] = 'tampered'
    (tmp_path / 'ir/region-1-0.json').write_text(json.dumps(first))
    with pytest.raises(ValueError, match='binding/hash changed'):
        proposer(*args)


def test_interrupt_reuses_saved_generation_without_new_query(recorded_selection, tmp_path):
    campaign, _, executor, provider = recorded_selection
    class Interrupt:
        image_id = executor.image_id
        def execute(self, *args): raise KeyboardInterrupt('test interrupt')
    model = Model(fixture_ir())
    options = dict(removed_nodes=['world.selection'], context_provider=provider, receipts=tmp_path / 'ir')
    args = campaign.initial, campaign.state['records'], 1, loss_spec()
    with pytest.raises(KeyboardInterrupt):
        NativeRegionIRProposer(model, Interrupt(), **options)(*args)
    assert NativeRegionIRProposer(model, executor, **options)(*args)
    assert len(model.calls) == 1


def test_second_joint_generation_replaces_previous_region_not_original_host_id(recorded_selection, tmp_path):
    campaign, factory, executor, provider = recorded_selection
    draft = fixture_ir()
    model = Model(draft)
    proposer = NativeRegionIRProposer(model, executor, removed_nodes=['world.selection'],
        context_provider=provider, receipts=tmp_path / 'first')
    patch = proposer(campaign.initial, campaign.state['records'], 1, loss_spec())
    record = campaign.advance(simulation_factory=factory, proposer=lambda *args: patch)
    parent = apply_design_patch(campaign.initial, patch)
    revised = deepcopy(draft)
    revised['rationale'] = 'Explicit QA second structural revision'
    revised['nodes'][0]['id'] = 'new-commons'
    revised['nodes'][1]['inputs']['dossier']['sources'] = ['node:new-commons:packets']
    bad = deepcopy(revised)
    bad['nodes'][1]['python_code'] = bad['nodes'][1]['python_code'].replace(
        "'paper_id': p['paper_id']", "'paper_id': p['paper_id'] + '-invented'")
    next_model = Model(bad, revised)
    next_proposer = NativeRegionIRProposer(next_model, executor, removed_nodes=['world.selection'],
        context_provider=provider, receipts=tmp_path / 'second')
    next_patch = next_proposer(parent, campaign.state['records'], 2, loss_spec())
    child = apply_design_patch(parent, next_patch)
    assert not set(parent.metadata['native_design_region']['node_ids']) & set(child.metadata['native_design_region']['node_ids'])
    assert json.loads(next_model.calls[0]['prompt'])['observed_feedback'][-1]['loss'] == record['observation']['loss']
    incumbent = json.loads(next_model.calls[0]['prompt'])['incumbent_generated_region']
    assert {n['mechanism_id'] for n in incumbent['mechanisms']} == set(parent.metadata['native_design_region']['node_ids'])
    assert sorted(n['parameters']['code_artifact']['source'] for n in incumbent['mechanisms']) == sorted(n['python_code'] for n in draft['nodes'])
    assert len(incumbent['connections']) == 5 and len(incumbent['schedules']) == 2
    prior = json.loads(next_model.calls[0]['prompt'])['previous_generated_candidates']['regions']
    assert prior[-1]['actual_loss'] == record['observation']['loss']
    assert prior[-1]['region']['mechanisms'] == incumbent['mechanisms']
    assert len(next_model.calls) == 2
    assert 'each real native paper exactly once' in next_model.calls[1]['prompt']
