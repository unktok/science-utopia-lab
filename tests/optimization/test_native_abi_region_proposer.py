"""ABI prompt software QA; no local LLM calls or source-body repair."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_free_source import recorded_selection
from tests.optimization.test_native_region_proposer import Model
from tests.optimization.test_native_staged_region_proposer import drafts
from tests.optimization.test_native_world import loss_spec
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_abi_region_proposer import (
    ABI_SCHEMA, NativeABIRegionProposer, mechanical_input_access_paths, per_node_execution_input_examples)
from utopia.optimization.native_staged_region_proposer import SCHEMA, NativeStagedRegionProposer
from utopia.system.code_mechanisms import sha


def external_examples():
    return [{'period': 1, 'boundary_inputs': {
        'world': [{'payload': {'schema': 'scienceutopia.native-world-observation.v1',
            'conferences': {'conferences': [{'conference_id': 'actual-conf',
                'submitted_papers': [{'id': 'actual-paper'}],
                'reviews': {'actual-paper': [{'overall_score': 3}]}}]}},
            'actor_ids': [], 'artifact_ids': [], 'emitted_period': 1}],
        'next': [{'payload': {'year': 1}, 'actor_ids': [], 'artifact_ids': [], 'emitted_period': 1}]}}]


def test_flat_per_node_actual_external_inputs_and_internal_schema_only():
    _, plan, _ = drafts()
    examples = external_examples()
    before = sha({'plan': plan, 'examples': examples})
    projected = per_node_execution_input_examples(plan, examples)
    producer, consumer = projected
    assert producer['node_id'] == 'world.review'
    first = producer['period_examples'][0]
    assert set(first['context_snippet']['inputs']) == {'evidence'}
    assert first['context_snippet']['inputs']['evidence'] == examples[0]['boundary_inputs']['world']
    assert first['input_evidence']['evidence']['status'] == 'actual-external-projection'
    world = first['context_snippet']['inputs']['evidence'][0]['payload']
    assert isinstance(world['conferences'], dict) and isinstance(world['conferences']['conferences'], list)
    assert isinstance(world['conferences']['conferences'][0]['submitted_papers'], list)
    assert isinstance(world['conferences']['conferences'][0]['reviews']['actual-paper'], list)
    second = consumer['period_examples'][0]
    assert set(second['context_snippet']['inputs']) == {'trigger'}
    assert 'dossier' not in second['context_snippet']['inputs']  # NOT fabricated as [].
    assert second['internal_inputs_schema_only']['dossier']['status'] == 'schema-only-not-an-observation'
    assert second['internal_inputs_schema_only']['dossier']['source_output_schemas'][0]['reference'] == 'node:world.review:packets'
    assert sha({'plan': plan, 'examples': examples}) == before
    paths = mechanical_input_access_paths(plan)
    assert paths['world.review']['evidence']['envelope_list'] == "context['inputs']['evidence']"
    assert paths['assembly']['dossier']['first_payload_if_nonempty'] == "context['inputs']['dossier'][0]['payload']"


def test_mixed_inputs_remain_explicitly_partial_and_actual_empty_values_stay_empty():
    _, plan, _ = drafts()
    plan['nodes'][0]['outputs']['packets']['artifact_type'] = 'native-world-observation'
    plan['nodes'][1]['inputs']['dossier']['sources'].append('boundary:world')
    examples = external_examples()
    examples[0]['boundary_inputs']['next'] = []
    consumer = per_node_execution_input_examples(plan, examples)[1]['period_examples'][0]
    assert consumer['context_snippet']['inputs']['trigger'] == []
    assert consumer['input_evidence']['dossier']['status'] == 'partial-actual-external-projection-internal-unobserved'
    assert consumer['context_snippet']['inputs']['dossier'] == examples[0]['boundary_inputs']['world']
    assert consumer['internal_inputs_schema_only']['dossier']['source_output_schemas']


def test_override_only_draft_preserves_plan_prompt_and_rebinds_both_phases(tmp_path):
    _, plan, sources = drafts()
    model = Model(plan, sources)
    class NoExecution:
        def execute(self, *args): raise AssertionError('prompt-only unit QA must never execute')
    proposer = NativeABIRegionProposer(model, NoExecution(), removed_nodes=['world.selection'],
        context_provider=None, receipts=tmp_path, max_attempts=2)
    assert issubclass(NativeABIRegionProposer, NativeStagedRegionProposer)
    assert set(NativeABIRegionProposer.__dict__) - {'__module__', '__doc__'} == {'_draft'}
    binding = {'schema': SCHEMA, 'max_prompt_utf8_bytes': 60000}
    plan_prompt = {'phase': 'plan', 'loss_spec': loss_spec()}
    before = sha({'binding': binding, 'prompt': plan_prompt})
    _, plan_receipt = proposer._draft(binding=binding, phase='plan', index=1, attempt=0,
        schema={'type': 'object'}, prompt=plan_prompt, previous_hash=None)
    assert sha({'binding': binding, 'prompt': plan_prompt}) == before
    assert json.loads(model.calls[0]['prompt']) == plan_prompt
    source_prompt = {'chosen_graph_plan': plan, 'actual_native_boundary_examples': external_examples()}
    original = sha(source_prompt)
    options = dict(binding=binding, phase='source', index=1, attempt=0, schema={'type': 'object'},
        prompt=source_prompt, previous_hash=plan_receipt['receipt_sha256'])
    _, source_receipt = proposer._draft(**options)
    assert sha(source_prompt) == original
    assert plan_receipt['binding']['schema'] == source_receipt['binding']['schema'] == ABI_SCHEMA
    assert source_receipt['generated'] == sources
    rendered = json.loads(model.calls[1]['prompt'])
    assert rendered['chosen_graph_plan'] == plan
    assert rendered['native_world_payload_container_paths']['conference_list']['path'] == "payload['conferences']['conferences']"
    assert 'context[\'inputs\'][NODE_ID][PORT]' in rendered['execution_input_abi_clarification']
    assert proposer._draft(**options)[1] == source_receipt and len(model.calls) == 2


def test_actual_native_probes_exact_source_repair_and_durable_resume(recorded_selection, tmp_path):
    campaign, _, executor, provider = recorded_selection
    original, plan, sources = drafts()
    bad = deepcopy(sources)
    bad['sources']['assembly'] = bad['sources']['assembly'].replace(
        "context['inputs']['dossier']", "context['inputs']['assembly']['dossier']")
    model = Model(plan, bad, sources)
    proposer = NativeABIRegionProposer(model, executor, removed_nodes=['world.selection'],
        context_provider=provider, receipts=tmp_path / 'abi', max_attempts=3)
    args = campaign.initial, campaign.state['records'], 1, loss_spec()
    before = sha(provider('world.selection', campaign.initial, campaign.state['records']))
    patch = proposer(*args)
    assert proposer(*args) == patch and len(model.calls) == 3
    assert sha(provider('world.selection', campaign.initial, campaign.state['records'])) == before
    plan_receipt = json.loads((tmp_path / 'abi/plan-1-0.json').read_text())
    first = json.loads((tmp_path / 'abi/region-1-0.json').read_text())
    final = json.loads((tmp_path / 'abi/region-1-1.json').read_text())
    assert {r['binding']['schema'] for r in (plan_receipt, first, final)} == {ABI_SCHEMA}
    assert first['generated'] == bad and first['status'] == 'invalid-technical-source'
    assert first['loss'] is None and 'KeyError' in '\n'.join(first['errors'])
    assert final['previous_receipt_sha256'] == first['receipt_sha256']
    assert first['previous_receipt_sha256'] == plan_receipt['receipt_sha256']
    assert final['complete_generated_ir'] == original and len(final['runs']) == 6
    source_prompt = json.loads(model.calls[1]['prompt'])
    assert len(source_prompt['per_node_execution_input_examples'][0]['period_examples']) == 6
    assert source_prompt['mechanical_input_access_paths']['assembly']['dossier']['envelope_list'] == "context['inputs']['dossier']"
    changed = deepcopy(loss_spec())
    changed['version'] = 'changed'
    with pytest.raises(ValueError, match='prompt/binding changed'):
        proposer(*args[:3], changed)
