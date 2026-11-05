"""SCRIPTED staged scheduling/consent checks; no actual local model calls."""
import importlib.util
from pathlib import Path

import pytest

from tests.optimization.test_native_search_v14 import BINDING, REVISION, FailedFactory, definition
from tests.optimization.test_native_search_v14 import request as legacy_request
from utopia.optimization.native_search_v14 import make_search_plan as legacy_plan
from utopia.optimization.native_search_v15 import NativeStagedSearchController, NativeStagedSearchQueue, make_search_plan, validate_search_request
from utopia.system.design_patch import digest


def request(method='blackbox', budget=2):
    value = legacy_request(method, budget)
    value['schema'] = 'scienceutopia.native-search-request.v15'
    value['designer'] = {'model': 'qwen3:8b', 'max_steps': 16, 'max_tokens': 2048}
    return value


@pytest.mark.parametrize('change', [
    lambda r: r['designer'].update(max_steps=0), lambda r: r['designer'].update(max_steps=65),
    lambda r: r['designer'].update(max_steps=True), lambda r: r['designer'].update(max_attempts=2),
    lambda r: r['designer'].update(model='stronger-hidden-provider'),
    lambda r: r.update(command='host command'), lambda r: r.update(schema='legacy'),
    lambda r: r.update(seed=701), lambda r: r.update(native_budget=9),
])
def test_staged_request_rejects_ambiguous_or_unbounded_settings(change):
    value = request(); change(value)
    with pytest.raises((ValueError, KeyError, TypeError)):
        validate_search_request(value)


def test_explicit_step_budget_counts_actual_model_calls_not_legacy_generations():
    plan = make_search_plan(request(), source_commit=REVISION, provider_binding=BINDING)
    assert plan['schema'] == 'scienceutopia.native-search-plan.v15'
    assert plan['stage_counts'] == [1, 1]
    assert plan['generator_calls'] == 2 and plan['maximum_designer_provider_attempts'] == 32
    assert plan['request']['designer'] == {'model': 'qwen3:8b', 'max_steps': 16, 'max_tokens': 2048}
    nested = make_search_plan(request('nested-lr', 4), source_commit=REVISION, provider_binding=BINDING)
    assert nested['stage_counts'] == [2, 1, 1] and nested['maximum_designer_provider_attempts'] == 32
    with pytest.raises(ValueError, match='exactly four'):
        validate_search_request(request('nested-lr', 2))
    old = legacy_plan(legacy_request(), source_commit=REVISION, provider_binding=BINDING)
    assert old['maximum_designer_provider_attempts'] == 4


def test_staged_controller_reuses_existing_native_campaign_and_exact_budget(tmp_path):
    plan = make_search_plan(request(), source_commit=REVISION, provider_binding=BINDING)
    controller = NativeStagedSearchController(tmp_path, plan=plan, plan_sha256=digest(plan))
    calls = []
    while not controller.complete:
        controller.advance(simulation_factory=FailedFactory(calls), generator=definition)
    progress = controller.projection(search_id='SCRIPTED', status='complete')
    assert progress['schema'] == 'scienceutopia.native-search-progress.v15'
    assert len(calls) == 2 and len(set(calls)) == 2
    assert progress['budget'] == {'scheduled': 2, 'consumed': 2, 'native_observations': 2, 'remaining': 0}
    assert all(row['observation']['loss'] is None for row in progress['observations'])
    reopened = NativeStagedSearchController(tmp_path, plan=plan, plan_sha256=digest(plan))
    assert reopened.projection(search_id='SCRIPTED', status='complete') == progress
    with pytest.raises(ValueError, match='already exhausted'):
        reopened.advance(simulation_factory=FailedFactory(calls), generator=definition)


def test_prospective_driver_freezes_all_loss_and_step_budgets_before_calls():
    path = Path(__file__).resolve().parents[2] / 'scripts/run_native_staged_search_v15.py'
    spec = importlib.util.spec_from_file_location('staged_driver_test', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    plan = module.build_plan(source_commit=REVISION, initial_system=request()['initial_system'],
        provider_binding=BINDING, runtime_seed_binding={'python_hash_seed_environment': '42'})
    assert plan['budget']['scheduled_native_slots'] == 4
    assert plan['budget']['maximum_generation_POSTs'] == 32
    assert [run['id'] for run in plan['runs']] == ['throughput', 'efficiency']
    assert plan['runs'][0]['request']['loss_spec']['per_run']['terms'][0]['coefficient'] == -1.0
    assert all(run['request']['designer']['max_steps'] == 8 for run in plan['runs'])
    assert all(run['request']['designer']['max_tokens'] == 8192 for run in plan['runs'])
    assert all(run['plan_sha256'] == digest(run['runtime_plan']) for run in plan['runs'])
    assert plan['budget']['maximum_designer_digest_preflight_GETs'] == 32
    assert plan['budget']['per_generation_tool_steps'] == 8
    assert plan['budget']['per_call_output_tokens'] == 8192
    assert plan['designer_decoding']['planner']['think'] is True
    assert plan['designer_decoding']['planner']['temperature'] == .6
    assert plan['designer_decoding']['editor']['think'] is False
    assert plan['designer_decoding']['editor']['temperature'] == .2
    assert plan['classification'] == 'actual-local-qwen-native-function-feedback-development-v26'
    assert plan['engineering_revision'] == 'v26-a1'
    assert plan['protocol'] == 'research/protocols/campaigns/native-function-feedback-v26-a1.md'


def test_staged_queue_observes_exact_journals_and_cold_resume_without_redispatch(tmp_path):
    from tests.optimization.test_native_search_generator_v14 import Model
    from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator
    from utopia.runtime.checkpointing import PortableStop
    q = NativeStagedSearchQueue(tmp_path, provider_binding=BINDING)
    body = request()
    with pytest.raises(ValueError, match='compute consent'):
        q.submit(body, confirmed_request_sha256='wrong', source_commit=REVISION)
    submitted = q.submit(body, confirmed_request_sha256=digest(body), source_commit=REVISION)
    assert submitted['authoring_trace']['generations'] == []
    assert not submitted['live_progress']['warnings']
    calls, models = [], []
    def builder(root, current, binding):
        model = Model([{'tool': 'finish', 'rationale': 'SCRIPTED explicit retention'}])
        models.append(model)
        return StagedVocabularyGenerator(model, root / 'authoring', image_id=binding['image_id'],
            provider_binding=binding, max_steps=current['designer']['max_steps'],
            max_tokens=current['designer']['max_tokens'])
    def stop(_):
        raise PortableStop('SCRIPTED committed stage restart')
    with pytest.raises(PortableStop):
        q.run_one(lambda *a: FailedFactory(calls), generator_builder=builder,
            source_commit=REVISION, after_stage=stop)
    partial = q.get(submitted['search_id'])
    assert partial['budget']['consumed'] == 1
    assert not partial['live_progress']['warnings']
    assert partial['live_progress']['designer']['attempts_completed'] == 1
    reopened = NativeStagedSearchQueue(tmp_path, provider_binding=BINDING)
    result = reopened.run_one(lambda *a: FailedFactory(calls), generator_builder=builder, source_commit=REVISION)
    assert result['status'] == 'complete' and result['budget']['consumed'] == 2
    assert len(calls) == len(set(calls)) == 2
    assert not result['live_progress']['warnings']
    assert len(result['authoring_trace']['generations']) == 2
    assert result['live_progress']['designer']['attempts_started'] == 2
    assert result['live_progress']['designer']['attempts_completed'] == 2
    assert reopened.run_one(lambda *a: pytest.fail('no factory'),
        generator_builder=lambda *a: pytest.fail('no author'), source_commit=REVISION) is None
