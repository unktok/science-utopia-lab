"""SCRIPTED scalar/protocol checks, not native scientific observations."""
from pathlib import Path

import pytest

from scripts import run_native_parameter_comparator_v1 as driver
from tests.reports.test_native_planning_objective_loop_v1 import plan as old_plan, seal
from utopia.optimization.blackbox import Observation
from utopia.optimization.common_content_observer import ObserverCompletionUnknown
from utopia.system import SystemSpec
from utopia.system.design_patch import clone


def plan(tmp_path, monkeypatch, image_override=None):
    original, _, _, _ = old_plan(tmp_path, monkeypatch, image_override)
    pairs = []
    for i, (label, candidate) in enumerate(original['reference_systems'].items()):
        # Force different declared initial parents without simulating science.
        count = 20 if i == 1 else 10
        utility = 20 if i == 6 else 10
        pairs.append({'suggestion': {'suggestion_id': 'reference-' + label,
            'candidate': clone(candidate), 'proposal_index': 0, 'phase': 'developer-reference',
            'based_on_observation_id': None}, 'observation': Observation(
                'observation-reference-' + label, 'reference-' + label, clone(candidate), 'complete', -count,
                {'system_fingerprint': SystemSpec.from_dict(candidate).fingerprint,
                 'measurements': [{'run_id': 'SCRIPTED-' + label, 'metrics': {
                    'native.accepted_decisions': {'status': 'measured', 'value': count},
                    'native.common_content_utility_sum': {'status': 'measured', 'value': utility}}}]}).to_dict()})
    context = seal({'pairs': pairs, 'SCRIPTED': 'unit scalar values, no original native evidence'})
    monkeypatch.setattr(driver, 'validate_context', lambda context, **kw: clone(context))
    audit = seal({'schema': 'scienceutopia.native-planning-objective-loop-audit.v1',
        'source_commit': original['source_commit'], 'SCRIPTED': 'not an original cold audit'})
    origin = {'run': str(tmp_path / 'closed-original'), 'source': str(tmp_path),
        'source_commit': original['source_commit'], 'audit_files': {}}
    p = seal(driver.build_plan(original, audit, context, source='c' * 40, origin=origin,
        observer_backend=original['observer_contract']['backend'],
        native_sources={'original_source': original['source_commit'], 'SCRIPTED': True}))
    return p, original, audit, context


def test_same_common_parents_literal_numeric_space_and_six_new_world_budget(tmp_path, monkeypatch):
    p, original, _, _ = plan(tmp_path, monkeypatch)
    assert p['anchors']['throughput']['reference_suggestion']['suggestion_id'] == 'reference-advice-reserve21-all'
    assert p['anchors']['content-utility']['reference_suggestion']['suggestion_id'] == 'reference-assignment-reserve21-no-review-all'
    assert p['budget']['reused_reference_worlds'] == 8 and p['budget']['new_reference_worlds'] == 0
    assert p['budget']['candidate_slots'] == p['budget']['native_worlds_upper_bound'] == 6
    assert p['world']['world_conditions'] == original['world']['world_conditions']
    assert p['losses'] == original['losses'] and p['posthoc_comparator_design']
    assert p['optimizer']['initial_random'] == 1 and p['optimizer_seed'] == 68011
    assert p['budget']['designer_generation_POSTs'] == 0 and not p['budget']['replace_failed_slots']
    assert not p['held_out_evaluation'] and not p['independent_optimizer_replications']
    for a in p['anchors'].values():
        assert a['space_binding']['design_space']['numeric_coordinates'] == [{
            'mechanism_id': 'developer-liquidity-director', 'path': '/parameters/reserve_units',
            'integer': True, 'lower': 1, 'upper': 60}]


def test_no_other_family_fallback_when_best_anchor_has_no_numeric_reserve(tmp_path, monkeypatch):
    _, original, audit, context = plan(tmp_path, monkeypatch)
    context['pairs'][4]['observation']['metadata']['measurements'][0]['metrics']['native.accepted_decisions']['value'] = 100
    with pytest.raises(ValueError, match='existing literal numeric field'):
        driver.build_plan(original, audit, seal(context), source='c' * 40, origin={},
            observer_backend=original['observer_contract']['backend'],
            native_sources={'original_source': original['source_commit']})


def setup(tmp_path, monkeypatch):
    p, _, _, _ = plan(tmp_path, monkeypatch)
    Path(p['origin']['run']).mkdir(); (Path(p['origin']['run']) / 'writer.lock').touch()
    root = tmp_path / 'numeric'; root.mkdir()
    monkeypatch.setattr(driver, 'require_environment', lambda: None)
    monkeypatch.setattr(driver, 'require_plan', lambda root: p)
    monkeypatch.setattr(driver, 'factory_for', lambda *a: pytest.fail('SCRIPTED evaluator must not create a real world'))
    return root, p


@pytest.mark.parametrize('failed', [False, True])
def test_six_consumed_slots_cold_scalar_replay_and_own_only_selection(tmp_path, monkeypatch, failed):
    root, p = setup(tmp_path, monkeypatch); calls = []
    monkeypatch.setattr(driver, 'factory_for', lambda *a: None)
    def evaluate(suggestion, **kw):
        calls.append(suggestion)
        return Observation('observation-' + suggestion.suggestion_id, suggestion.suggestion_id,
            suggestion.candidate, 'failed' if failed else 'complete', None if failed else -3.,
            {'measurements': [], 'SCRIPTED': 'not a native trajectory'})
    monkeypatch.setattr(driver, 'evaluate_native_suggestion', evaluate)
    driver.run(root)
    assert len(calls) == 6 and driver.read(root / 'terminal.json')['status'] == 'closed'
    selected = driver.read(root / 'selection.json')
    for objective in p['objectives']:
        o = driver.optimizer_for(p, objective)
        for g in range(3):
            directory = root / 'search' / objective / ('generation-' + str(g))
            s = o.ask()[0]
            assert driver.read(directory / 'started.json')['suggestion'] == s.to_dict()
            o.tell([Observation.from_dict(driver.read(directory / 'observation.json'))])
            restored = driver.read(directory / 'optimizer-after-tell.json'); restored.pop('content_sha256')
            assert restored == o.state_dict()
        row = selected['selected'][objective]
        assert row['completed_submissions'] == (0 if failed else 3)
        assert (row['selected_id'] is None) == failed
        assert len(row['all_tied_ids']) == (0 if failed else 3)
        if not failed:
            assert row['selected_id'] == driver.read(root / 'search' / objective / 'generation-0/started.json')['suggestion']['suggestion_id']
    assert not selected['baseline_fallback']
    with pytest.raises(ValueError, match='no redispatch'): driver.run(root)


def test_unknown_native_dispatch_stops_consumed_study_without_refill(tmp_path, monkeypatch):
    root, _ = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(driver, 'factory_for', lambda *a: None)
    def unknown(*a, **kw): raise ObserverCompletionUnknown('SCRIPTED unknown dispatch')
    monkeypatch.setattr(driver, 'evaluate_native_suggestion', unknown)
    with pytest.raises(ObserverCompletionUnknown): driver.run(root)
    terminal = driver.read(root / 'terminal.json')
    assert terminal['status'] == 'stopped' and terminal['consumed_slots'] == 1
    assert terminal['completed_observations'] == 0 and not (root / 'selection.json').exists()
    assert len(list(root.glob('search/*/generation-*/started.json'))) == 1
    with pytest.raises(ValueError, match='no redispatch'): driver.run(root)


def test_plan_cold_reconstruction_binds_origin_source_objective_and_full_range(tmp_path, monkeypatch):
    p, original, audit, context = plan(tmp_path, monkeypatch)
    root = tmp_path / 'prepared'; driver.save(root / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    monkeypatch.setattr(driver, 'pinned_revision', lambda root: p['source_commit'])
    monkeypatch.setattr(driver, 'origin_evidence', lambda origin: (original, audit))
    monkeypatch.setattr(driver, 'context_for', lambda *a: context)
    monkeypatch.setattr(driver, 'unchanged_native_sources', lambda source: p['original_native_sources'])
    assert driver.require_plan(root) == p
    changed = clone(p); changed['optimizer_seed'] += 1
    driver.save(tmp_path / 'changed/plan.json', {k: v for k, v in changed.items() if k != 'content_sha256'})
    with pytest.raises(ValueError, match='reconstruction'): driver.require_plan(tmp_path / 'changed')
