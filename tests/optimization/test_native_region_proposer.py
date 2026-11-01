"""Scripted software QA on the original native world, NOT Qwen invention."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from tests.optimization.test_native_region_design import fixture_manifest, port
from tests.optimization.test_native_free_source import recorded_selection
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_code_trace import RecordingCodeExecutor, parent_context_provider
from utopia.optimization.native_design import NativeDesignCampaign
from utopia.optimization.native_region_design import compile_region, probe_region, probe_selection_region
from utopia.optimization.native_region_proposer import NativeRegionProposer, expand_authoring_manifest
from utopia.system import ChannelKind, MechanismFamily, MechanismSpec, PortSpec
from utopia.system.code_mechanisms import CODE_IMPLEMENTATION, CODE_SCHEMA, DockerCodeExecutor, sha
from utopia.system.native_examples import connect_native_institution
from utopia.system.native_kernel import NativeScienceKernel, WORLD_ARTIFACT, legacy_world_system


def compact(manifest):
    value = deepcopy(manifest)
    for node in value['nodes']:
        node.pop('family')
        for direction in ('inputs', 'outputs'):
            schemas = node.pop(direction[:-1] + '_schemas')
            for p in node[direction]:
                p['payload_schema'] = schemas[p['port_id']]
    return value


class Model:
    def __init__(self, *drafts):
        self.drafts, self.calls = drafts, []
    def generate(self, **kwargs):
        draft = self.drafts[len(self.calls)]
        self.calls.append(kwargs)
        return deepcopy(draft), []


def test_compact_schema_preserves_exact_python_names_and_connections():
    original = fixture_manifest()
    assert expand_authoring_manifest(compact(original)) == original
    bad = compact(original)
    bad['nodes'][0]['family'] = 'input'
    with pytest.raises(Exception, match='family'):
        expand_authoring_manifest(bad)


def test_joint_generation_stateful_native_probe_resume_and_binding(recorded_selection, tmp_path):
    campaign, _, executor, provider = recorded_selection
    draft = compact(fixture_manifest())
    model = Model(draft)
    proposer = NativeRegionProposer(model, executor, removed_nodes=['world.selection'],
        context_provider=provider, receipts=tmp_path / 'joint')
    args = campaign.initial, campaign.state['records'], 1, loss_spec()
    patch = proposer(*args)
    assert proposer(*args) == patch and len(model.calls) == 1
    value = json.loads((tmp_path / 'joint/region-1-0.json').read_text())
    assert value['loss'] is None
    assert [r['state_after']['qa-evidence-commons']['cycles'] for r in value['runs']] == list(range(1, 7))
    assert value['generated'] == draft
    parent_source = next(n.parameters['code_artifact']['source'] for n in campaign.initial.mechanisms if n.mechanism_id == 'world.selection')
    assert parent_source not in model.calls[0]['prompt']
    assert len(model.calls[0]['prompt'].encode()) < 15000
    assert model.calls[0]['max_tokens'] == 4096
    changed = deepcopy(loss_spec())
    changed['version'] = 'changed'
    with pytest.raises(ValueError, match='prompt/binding changed'):
        proposer(*args[:3], changed)


def test_second_year_failure_is_repaired_with_exact_persisted_chain(recorded_selection, tmp_path):
    campaign, _, executor, provider = recorded_selection
    valid = compact(fixture_manifest())
    bad = deepcopy(valid)
    bad['nodes'][0]['python_code'] = bad['nodes'][0]['python_code'].replace(
        "    world =", "    if context['state'].get('cycles', 0) > 0:\n        raise ValueError('QA second-year failure')\n    world =")
    model = Model(bad, valid)
    proposer = NativeRegionProposer(model, executor, removed_nodes=['world.selection'],
        context_provider=provider, receipts=tmp_path / 'repair')
    patch = proposer(campaign.initial, campaign.state['records'], 1, loss_spec())
    assert patch and len(model.calls) == 2
    first = json.loads((tmp_path / 'repair/region-1-0.json').read_text())
    second = json.loads((tmp_path / 'repair/region-1-1.json').read_text())
    assert first['status'] == 'invalid-technical-manifest' and 'second-year' in first['error']
    assert second['previous_receipt_sha256'] == first['receipt_sha256']
    assert first['generated'] == bad and second['generated'] == valid
    assert 'QA second-year failure' in model.calls[1]['prompt']
    proposer(campaign.initial, campaign.state['records'], 1, loss_spec())
    assert len(model.calls) == 2
    first['error'] = 'tampered'
    (tmp_path / 'repair/region-1-0.json').write_text(json.dumps(first))
    with pytest.raises(ValueError, match='binding/hash changed'):
        proposer(campaign.initial, campaign.state['records'], 1, loss_spec())


def test_generated_draft_survives_process_interruption_without_new_model_call(recorded_selection, tmp_path):
    campaign, _, executor, provider = recorded_selection
    class Interrupt:
        image_id = executor.image_id
        def execute(self, *args): raise KeyboardInterrupt('QA interruption after saved generation')
    model = Model(compact(fixture_manifest()))
    options = dict(removed_nodes=['world.selection'], context_provider=provider, receipts=tmp_path / 'resume')
    args = campaign.initial, campaign.state['records'], 1, loss_spec()
    with pytest.raises(KeyboardInterrupt): NativeRegionProposer(model, Interrupt(), **options)(*args)
    draft = json.loads((tmp_path / 'resume/region-1-0.json').read_text())
    assert draft['status'] == 'generated-awaiting-isolated-probe'
    assert NativeRegionProposer(model, executor, **options)(*args)
    assert len(model.calls) == 1


def test_incomplete_chronology_and_forged_receipts_fail(recorded_selection):
    campaign, _, executor, provider = recorded_selection
    _, child = compile_region(campaign.initial, fixture_manifest(), removed_nodes=['world.selection'], image_id=executor.image_id)
    records = provider('world.selection', campaign.initial, campaign.state['records'])
    with pytest.raises(ValueError, match='contiguous'):
        probe_selection_region(campaign.initial, child, records[1:], executor=executor)
    class Forged:
        def execute(self, *args):
            result = executor.execute(*args)
            result.receipt['context_sha256'] = 'forged'
            return result
    with pytest.raises(ValueError, match='receipt mismatch'):
        probe_selection_region(campaign.initial, child, records, executor=Forged())


def test_generic_probe_replaces_multiple_existing_python_nodes(recorded_selection):
    campaign, factory, executor, provider = recorded_selection
    patch, parent = compile_region(campaign.initial, fixture_manifest(), removed_nodes=['world.selection'], image_id=executor.image_id)
    campaign.advance(simulation_factory=factory, proposer=lambda *a: patch)
    removed = ['qa-evidence-commons', 'qa-decision-assembly']
    manifest = fixture_manifest()
    manifest['nodes'][0]['mechanism_id'] = 'qa-rewired-evidence'
    manifest['nodes'][1]['mechanism_id'] = 'qa-rewired-verdict'
    for edge in manifest['connections']:
        for side in ('source_mechanism', 'target_mechanism'):
            edge[side] = {'qa-evidence-commons': 'qa-rewired-evidence', 'qa-decision-assembly': 'qa-rewired-verdict'}.get(edge[side], edge[side])
    _, child = compile_region(parent, manifest, removed_nodes=removed, image_id=executor.image_id)
    records = [row for node in removed for row in provider(node, parent, campaign.state['records'])]
    result = probe_region(parent, child, records, executor=executor)
    assert len(result['runs']) == 6
    assert all(set(r['native_boundary_bundle_sha256s']) == set(removed) for r in result['runs'])
    assert result['runs'][-1]['state_after']['qa-rewired-verdict']['cycles'] == 6


def test_compiler_clears_only_removed_initial_memory(recorded_selection):
    campaign, _, executor, _ = recorded_selection
    initial = {**campaign.initial.initial_state, 'mechanism_states': {'world.selection': {'cycles': 99}, 'world.funding': {'kept': True}}}
    parent = replace(campaign.initial, initial_state=initial)
    _, child = compile_region(parent, fixture_manifest(), removed_nodes=['world.selection'], image_id=executor.image_id)
    assert child.initial_state['mechanism_states'] == {'world.funding': {'kept': True}}


def test_communication_region_rewrites_new_protocol_and_reaches_real_researcher_prompts(tmp_path, fixed_corpus):
    executor = DockerCodeExecutor()
    source = "def step(context):\n    return {'outputs': {'messages': []}, 'state': {'cycles': context['state'].get('cycles',0)+1}}\n"
    inputs = (PortSpec('observations', ChannelKind.ARTIFACT, WORLD_ARTIFACT),)
    outputs = (PortSpec('messages', ChannelKind.ARTIFACT, 'qa-notices', required=False),)
    institution = MechanismSpec('qa-old-commons', MechanismFamily.CUSTOM, CODE_IMPLEMENTATION,
        inputs=inputs, outputs=outputs, parameters={'runtime_image_id': executor.image_id, 'code_artifact': {
            'schema': CODE_SCHEMA, 'label': 'QA existing empty commons', 'source': source,
            'inputs': {'observations': {'type': 'object'}}, 'outputs': {'messages': {'type': 'object'}}, 'state_schema': {'type': 'object'}}})
    spec = connect_native_institution(legacy_world_system(), institution, researcher_output='messages')
    controller = NativeDesignCampaign(tmp_path / 'campaign', initial_system=spec,
        loss_spec=loss_spec(), seeds=[42], world_binding={'mode': 'scripted-QA-only'})
    calls = {}
    def factory(system, run_seed, run_id):
        seed()
        recorder = RecordingCodeExecutor(executor, tmp_path / 'runs' / run_id / 'code-contexts.jsonl',
            binding={'source_commit': 'QA', 'system_fingerprint': system.fingerprint, 'run_id': run_id})
        sim, wire = make_sim(tmp_path / 'runs' / run_id, native=NativeScienceKernel(system, code_executor=recorder))
        calls[run_id] = wire
        return sim
    controller.advance(simulation_factory=factory)
    producer = """def step(context):
    agents = context['inputs']['evidence'][0]['payload']['ecosystem']['agents']
    ids = [a['id'] for a in agents if a.get('can_author')]
    return {'outputs': {'packets': [{'payload': {'recipients': ids}}]}, 'state': {'cycles': context['state'].get('cycles',0)+1}}
"""
    consumer = """def step(context):
    ids = context['inputs']['dossier'][0]['payload']['recipients']
    values = [{'payload': {'notice': 'QA_JOINT_REGION_NATIVE_PROMPT', 'cycle': context['state'].get('cycles',0)+1}, 'actor_ids': [aid]} for aid in ids]
    return {'outputs': {'notices': values}, 'state': {'cycles': context['state'].get('cycles',0)+1}}
"""
    manifest = fixture_manifest()
    a, b = manifest['nodes']
    a.update(mechanism_id='qa-new-exchange', phase=190, python_code=producer,
        inputs=[port('evidence', 'artifact', WORLD_ARTIFACT)], outputs=[port('packets', 'artifact', 'qa-recipient-dossier')])
    b.update(mechanism_id='qa-new-assembly', phase=210, python_code=consumer,
        inputs=[port('dossier', 'artifact', 'qa-recipient-dossier')], outputs=[{**port('notices', 'artifact', 'qa-notices'), 'required': False}])
    for node in manifest['nodes']:
        node['input_schemas'] = {p['port_id']: {'type': 'object'} for p in node['inputs']}
        node['output_schemas'] = {p['port_id']: {'type': 'object'} for p in node['outputs']}
    def edge(a, p, b, q):
        return {'source_mechanism': a, 'source_port': p, 'target_mechanism': b, 'target_port': q, 'channel': 'artifact', 'latency': 0}
    manifest['connections'] = [edge('world.publication', 'world', 'qa-new-exchange', 'evidence'),
        edge('qa-new-exchange', 'packets', 'qa-new-assembly', 'dossier'), edge('qa-new-assembly', 'notices', 'researcher-context', 'messages')]
    provider = parent_context_provider(tmp_path / 'runs', source_commit='QA')
    model = Model(compact(manifest))
    proposer = NativeRegionProposer(model, executor, removed_nodes=['qa-old-commons'], context_provider=provider, receipts=tmp_path / 'proposals')
    result = controller.advance(simulation_factory=factory, proposer=proposer)
    assert result['observation']['status'] == 'complete'
    receipts = json.loads((tmp_path / 'proposals/region-1-0.json').read_text())
    assert [r['state_after']['qa-new-assembly']['cycles'] for r in receipts['runs']] == list(range(1, 7))
    child_run_id = result['observation']['metadata']['runs'][0]['run_id']
    actual_requests = calls[child_run_id]
    assert any(ctx[0] == 'phase1_directions' and ctx[1] == 2 and 'QA_JOINT_REGION_NATIVE_PROMPT' in json.dumps(payload)
        for (ctx, _, _), payload in actual_requests)
    actual_code = [json.loads(line) for line in (tmp_path / 'runs' / child_run_id / 'code-contexts.jsonl').read_text().splitlines()]
    for execution in receipts['runs'][0]['code_executions']:
        matches = [r for r in actual_code if r['context']['period'] == 1
            and r['receipt']['artifact_sha256'] == execution['receipt']['artifact_sha256']]
        assert len(matches) == 1
        assert matches[0]['context'] == execution['context']
        assert matches[0]['result'] == execution['result']
    assert receipts['loss'] is None  # only the separate native run observes loss
