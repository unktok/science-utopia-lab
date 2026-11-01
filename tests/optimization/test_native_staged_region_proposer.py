"""Scripted original-native/Docker software QA, not model invention evidence."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from tests.optimization.test_native_free_source import recorded_selection
from tests.optimization.test_native_region_ir import fixture_ir
from tests.optimization.test_native_region_proposer import Model
from tests.optimization.test_native_world import loss_spec
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_region_ir import boundary_contract
from utopia.optimization.native_staged_region_proposer import (
    NativeStagedRegionProposer, STRUCTURE_ONLY, attach_sources, graph_plan_errors,
    _payload_prompt_view, source_artifact_errors, staged_plan_schema, staged_source_schema,
)
from utopia.system import SystemSpec
from utopia.system.code_mechanisms import sha
from utopia.system.native_kernel import legacy_world_system
from utopia.system.native_selection_slot import selection_source_slot


def drafts():
    original = fixture_ir()
    plan = deepcopy(original)
    sources = {'sources': {n['id']: n.pop('python_code') for n in plan['nodes']}}
    return original, plan, sources


def test_plan_has_no_python_and_sources_cannot_change_chosen_interfaces():
    original, plan, sources = drafts()
    parent = selection_source_slot(legacy_world_system(), image_id='sha256:' + 'a' * 64)
    schema = staged_plan_schema(boundary_contract(parent, ['world.selection']))
    Draft202012Validator(schema).validate(plan)
    assert list(Draft202012Validator(schema).iter_errors(original))
    assert attach_sources(plan, sources['sources']) == original
    wrong = deepcopy(sources)
    wrong['sources']['extra-interface'] = 'def step(context): pass'
    assert list(Draft202012Validator(staged_source_schema(plan)).iter_errors(wrong))
    assert not graph_plan_errors(parent, plan, removed_nodes=['world.selection'], image_id='sha256:' + 'a' * 64)


def test_collect_independent_graph_and_source_errors_without_execution():
    _, plan, sources = drafts()
    parent = selection_source_slot(legacy_world_system(), image_id='sha256:' + 'a' * 64)
    plan['nodes'][1]['inputs']['dossier']['sources'] = ['node:missing:output']
    plan['exports']['decisions'] = ['node:assembly:outputs']
    errors = graph_plan_errors(parent, plan, removed_nodes=['world.selection'], image_id='sha256:' + 'a' * 64)
    assert len(errors) == 2 and any('missing:output' in e for e in errors) and any('assembly:outputs' in e for e in errors)
    sources['sources'] = {key: 'def broken(' for key in sources['sources']}
    errors = source_artifact_errors(plan, sources)
    assert len(errors) == 2


def test_prompt_projection_retains_deep_list_and_score_shapes():
    value = {'boundary_inputs': {'world': [{'payload': {'conferences': {'conferences': [
        {'submitted_papers': [{'id': 'actual-paper'}],
         'reviews': {'actual-paper': [{'overall_score': 3}]}}]}}}]}}
    assert _payload_prompt_view(value) == value
    conference = value['boundary_inputs']['world'][0]['payload']['conferences']['conferences'][0]
    conference['submitted_papers'] = [{'id': str(i)} for i in range(8)]
    conference['reviews']['actual-paper'] = [{'overall_score': i} for i in range(8)]
    before = sha(value)
    result = _payload_prompt_view(value)
    projected = result['boundary_inputs']['world'][0]['payload']['conferences']['conferences'][0]
    assert isinstance(result['boundary_inputs']['world'], list)
    assert isinstance(projected['submitted_papers'], list) and len(projected['submitted_papers']) == 5
    assert isinstance(projected['reviews']['actual-paper'], list)
    assert [r['overall_score'] for r in projected['reviews']['actual-paper']] == list(range(5))
    assert sha(value) == before


def test_staged_bounded_repairs_exact_source_real_docker_and_native_resume(recorded_selection, tmp_path):
    campaign, factory, executor, provider = recorded_selection
    original, plan, sources = drafts()
    bad_plan = deepcopy(plan)
    bad_plan['exports'].pop('after')
    bad_sources = deepcopy(sources)
    bad_sources['sources']['assembly'] = 'def wrong_entry(context): pass'
    model = Model(bad_plan, plan, bad_sources, sources)
    class GuardExecutor:
        image_id = executor.image_id
        calls = []
        def execute(self, artifact, context):
            assert artifact['source'] != STRUCTURE_ONLY
            self.calls.append((artifact['source'], context['period']))
            return executor.execute(artifact, context)
    guard = GuardExecutor()
    proposer = NativeStagedRegionProposer(model, guard, removed_nodes=['world.selection'],
        context_provider=provider, receipts=tmp_path / 'staged', max_attempts=3)
    args = campaign.initial, deepcopy(campaign.state['records']), 1, loss_spec()
    before = sha(provider('world.selection', campaign.initial, campaign.state['records']))
    patch = proposer(*args)
    assert len(model.calls) == 4 and len(guard.calls) == 12
    assert proposer(*args) == patch and len(model.calls) == 4 and len(guard.calls) == 12
    assert before == sha(provider('world.selection', campaign.initial, campaign.state['records']))
    first = json.loads((tmp_path / 'staged/plan-1-0.json').read_text())
    accepted_plan = json.loads((tmp_path / 'staged/plan-1-1.json').read_text())
    first_source = json.loads((tmp_path / 'staged/region-1-0.json').read_text())
    final = json.loads((tmp_path / 'staged/region-1-1.json').read_text())
    assert accepted_plan['status'] == 'structural-plan-passed-not-executed'
    assert 'patch' not in accepted_plan and 'candidate_fingerprint' not in accepted_plan
    assert accepted_plan['previous_receipt_sha256'] == first['receipt_sha256']
    assert first_source['previous_receipt_sha256'] == accepted_plan['receipt_sha256']
    assert final['previous_receipt_sha256'] == first_source['receipt_sha256']
    assert final['complete_generated_ir'] == original and final['loss'] is None
    assert first_source['binding']['plan_receipt_sha256'] == accepted_plan['receipt_sha256']
    source_prompt = json.loads(model.calls[2]['prompt'])
    assert len(source_prompt['actual_native_boundary_examples']) == 6
    assert source_prompt['chosen_graph_plan'] == plan
    assert 'submitted_papers is a LIST' in source_prompt['python_contract']
    assert 'source_mechanism' not in json.dumps(source_prompt['actual_native_boundary_examples'])
    assert 'incumbent_generated_region' not in source_prompt
    assert 'phase' in first['binding'] and first['binding']['plan_attempts'] == 3
    record = campaign.advance(simulation_factory=factory, proposer=lambda *args: patch)
    assert record['observation']['status'] == 'complete'
    parent = SystemSpec.from_dict(record['suggestion']['candidate'])
    revised = Model(plan, sources)
    next_proposer = NativeStagedRegionProposer(revised, executor,
        removed_nodes=['world.selection'], context_provider=provider, receipts=tmp_path / 'next')
    assert next_proposer(parent, campaign.state['records'], 2, loss_spec())
    second_prompt = json.loads(revised.calls[0]['prompt'])
    assert second_prompt['incumbent_generated_region']
    assert sources['sources']['assembly'] in revised.calls[0]['prompt'].replace('\\n', '\n').replace('\\"', '"')
    assert second_prompt['observed_feedback'][-1]['loss'] == record['observation']['loss']
    first['errors'] = ['tampered']
    (tmp_path / 'staged/plan-1-0.json').write_text(json.dumps(first))
    with pytest.raises(ValueError, match='binding/hash changed'):
        proposer(*args)


def test_interrupt_reuses_both_saved_phases_without_extra_model_call(recorded_selection, tmp_path):
    campaign, _, executor, provider = recorded_selection
    _, plan, sources = drafts()
    class Interrupt:
        image_id = executor.image_id
        def execute(self, *args):
            raise KeyboardInterrupt('scripted process interruption')
    model = Model(plan, sources)
    kwargs = dict(removed_nodes=['world.selection'], context_provider=provider, receipts=tmp_path / 'resume')
    args = campaign.initial, campaign.state['records'], 1, loss_spec()
    with pytest.raises(KeyboardInterrupt):
        NativeStagedRegionProposer(model, Interrupt(), **kwargs)(*args)
    assert NativeStagedRegionProposer(model, executor, **kwargs)(*args)
    assert len(model.calls) == 2
    changed = deepcopy(loss_spec())
    changed['version'] = 'different-objective'
    with pytest.raises(ValueError, match='prompt/binding changed'):
        NativeStagedRegionProposer(model, executor, **kwargs)(*args[:3], changed)


def test_plan_budget_exhaustion_never_generates_source_or_executes_placeholder(recorded_selection, tmp_path):
    campaign, _, executor, provider = recorded_selection
    _, plan, _ = drafts()
    plan['exports'].pop('after')
    model = Model(plan, plan, plan)
    class NoExecute:
        image_id = executor.image_id
        def execute(self, *args):
            raise AssertionError('no execution during invalid graph plan')
    proposer = NativeStagedRegionProposer(model, NoExecute(), removed_nodes=['world.selection'],
        context_provider=provider, receipts=tmp_path / 'budget')
    with pytest.raises(ValueError, match='bounded region technical drafts exhausted'):
        proposer(campaign.initial, campaign.state['records'], 1, loss_spec())
    assert len(model.calls) == 3 and not list((tmp_path / 'budget').glob('region-*.json'))


def test_source_budget_is_separate_bounded_and_never_replans(recorded_selection, tmp_path):
    campaign, _, executor, provider = recorded_selection
    _, plan, sources = drafts()
    sources['sources'] = {key: 'def invalid(' for key in sources['sources']}
    model = Model(plan, sources, sources, sources)
    class NoExecute:
        image_id = executor.image_id
        def execute(self, *args):
            raise AssertionError('invalid Python must not execute')
    proposer = NativeStagedRegionProposer(model, NoExecute(), removed_nodes=['world.selection'],
        context_provider=provider, receipts=tmp_path / 'source-budget')
    args = campaign.initial, campaign.state['records'], 1, loss_spec()
    with pytest.raises(ValueError, match='bounded region technical drafts exhausted'):
        proposer(*args)
    assert len(model.calls) == 4
    assert len(list((tmp_path / 'source-budget').glob('plan-1-*.json'))) == 1
    assert len(list((tmp_path / 'source-budget').glob('region-1-*.json'))) == 3
    with pytest.raises(ValueError, match='bounded region technical drafts exhausted'):
        proposer(*args)
    assert len(model.calls) == 4
