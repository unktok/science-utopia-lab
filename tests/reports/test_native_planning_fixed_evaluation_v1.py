"""SCRIPTED fixed-selection planning evaluation, not real unused-seed results."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_planning_fixed_evaluation_v1 as module
from scripts import finish_native_planning_fixed_evaluation_v1 as finish
from tests.reports.test_native_planning_objective_loop_v1 import plan as original_plan
from tests.reports.test_native_objective_fixed_evaluation_v1 import seal
from tests.reports.test_native_capacity_fixed_evaluation_v1 import usage
from utopia.optimization.common_content_observer import CommonContentObserver, ObserverCompletionUnknown
from utopia.system.design_patch import clone


def evidence(tmp_path, monkeypatch, *, seeds=None, image_override=None):
    original, _, _, _ = original_plan(tmp_path, monkeypatch, image_override=image_override)
    seeds = [72101, 72107] if seeds is None else seeds
    system = original['initial_system']
    worlds = [{'identity': 'SCRIPTED-first', 'role': 'search:throughput', 'status': 'complete',
               'system': clone(system), 'scores': {'throughput': -2., 'content-utility': -1.}},
              {'identity': 'SCRIPTED-second', 'role': 'search:throughput', 'status': 'complete',
               'system': clone(system), 'scores': {'throughput': -2., 'content-utility': -1.}}]
    selection = seal({'plan_sha256': original['content_sha256'], 'baseline_fallback': False,
        'held_out_evaluation': False, 'frozen_utc': '2026-11-13T00:00:00+00:00', 'selected': {
            'throughput': {'loss': -2., 'completed_submissions': 2, 'all_tied_ids': ['SCRIPTED-first', 'SCRIPTED-second'],
                           'selected_id': 'SCRIPTED-first', 'system': clone(system)},
            'content-utility': {'loss': None, 'completed_submissions': 0, 'all_tied_ids': [],
                                'selected_id': None, 'system': None}}})
    audit = seal({'schema': 'scienceutopia.native-planning-objective-loop-audit.v1',
        'source_commit': original['source_commit'], 'plan_sha256': original['content_sha256'],
        'closure': {'terminal': {'status': 'closed'}}, 'source_proof': {'status': 'verified-exact-source-closure'},
        'selection': selection, 'worlds': worlds, 'authoring': [{'SCRIPTED': 'original closure mocked'}] * 6,
        'initial_readiness': {'SCRIPTED': 'not actual model readiness'},
        'new_model_calls': 0, 'new_code_executions': 0, 'held_out_evaluation': False})
    p = module.build_plan(original, audit, source='e' * 40, origin={'SCRIPTED': 'not real origin'},
        usages=[usage(seeds)], seeds=seeds, observer_backend=original['observer_contract']['backend'])
    return original, audit, seal(p)


def test_all_eight_controls_literal_own_ties_and_same_scientific_observer(tmp_path, monkeypatch):
    original, audit, p = evidence(tmp_path, monkeypatch)
    assert p['fixed_selection'] == audit['selection'] and p['losses'] == original['losses']
    assert len(p['reference_systems']) == 8 and len(p['jobs']) == 16
    assert p['evaluation']['maximum_physical_worlds'] == 20
    assert p['world']['world_conditions'] == original['world']['world_conditions']
    ignore = ('source_commit', 'content_sha256', 'maximum_posts')
    assert {k: v for k, v in p['observer_contract'].items() if k not in ignore} == {
        k: v for k, v in original['observer_contract'].items() if k not in ignore}
    assert original['observer_contract']['maximum_posts'] == 1500 and p['observer_contract']['maximum_posts'] == 3000
    assert not p['budget']['replace_failed_slots'] and p['budget']['designer_generation_POSTs'] == 0
    chosen = [j for j in p['jobs'] if 'selected:throughput' in j['labels']]
    assert len(chosen) == 2 and all('reference:cut-reserve21-all' in j['labels'] for j in chosen)
    assert all('selected:content-utility' not in j['labels'] for j in p['jobs'])
    with pytest.raises(ValueError): module.fixed_selection(original, audit)  # No implicit old-study alias.


@pytest.mark.parametrize('change', ['source', 'stopped', 'fallback', 'tie', 'system', 'judge',
                                  'used', 'errors', 'empty', 'four', 'bool', 'development', 'duplicate', 'negative'])
def test_changed_selection_measurement_and_unused_scope_rejected(tmp_path, monkeypatch, change):
    original, audit, _ = evidence(tmp_path, monkeypatch); seeds = [72101, 72107]
    u = usage(seeds); backend = original['observer_contract']['backend']
    if change == 'source': audit['source_commit'] = 'f' * 40
    elif change == 'stopped': audit['closure']['terminal']['status'] = 'stopped'
    elif change == 'fallback': audit['selection']['baseline_fallback'] = True
    elif change == 'tie': audit['selection']['selected']['throughput']['all_tied_ids'].pop()
    elif change == 'system': audit['selection']['selected']['throughput']['system']['initial_state']['SCRIPTED'] = True
    elif change == 'judge': backend = {**backend, 'ollama_version': 'SCRIPTED changed'}
    elif change == 'used': u['prior_matching_runs'] = [{'SCRIPTED': True}]
    elif change == 'errors': u['errors'] = [{'SCRIPTED': 'unknown journal'}]
    elif change == 'empty': seeds = []
    elif change == 'four': seeds = [72101, 72103, 72107, 72109]
    elif change == 'bool': seeds = [True]
    elif change == 'development': seeds = [61001]
    elif change == 'duplicate': seeds = [72101, 72101]
    else: seeds = [-1]
    seal(audit['selection']); seal(audit); u['seeds'] = seeds; seal(u)
    with pytest.raises(ValueError):
        module.build_plan(original, audit, source='e' * 40, origin={}, usages=[u], seeds=seeds, observer_backend=backend)


def setup(tmp_path, monkeypatch):
    _, _, p = evidence(tmp_path / 'input', monkeypatch)
    root = tmp_path / 'evaluation'; root.mkdir(); origin = tmp_path / 'origin'; origin.mkdir()
    (origin / 'writer.lock').touch(); inventory = tmp_path / 'inventory'; inventory.mkdir()
    u = usage(p['evaluation']['seeds']); u['root'] = str(inventory); seal(u)
    p['origin'] = {'run': str(origin)}; p['evaluation']['seed_usage'] = [u['content_sha256']]; seal(p)
    module.save(root / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    module.save(root / 'seed-usage-00.json', {k: v for k, v in u.items() if k != 'content_sha256'})
    monkeypatch.setattr(module, 'require_environment', lambda: None)
    monkeypatch.setattr(module, 'require_plan', lambda root: p)
    monkeypatch.setattr(module, 'usage_inventory', lambda *a: u)
    monkeypatch.setattr(module, 'LocalObserverBackend', lambda **k: None)
    return root, p, u


def test_all_jobs_and_known_nulls_close_without_design_or_refill(tmp_path, monkeypatch):
    root, p, _ = setup(tmp_path, monkeypatch); calls = []
    def observe(root, p, job, observer):
        calls.append(clone(job))
        module.save(root / 'evaluation' / job['identity'] / 'observation.json',
                    {'status': 'failed' if len(calls) == 1 else 'complete', 'SCRIPTED': 'not native outcomes'})
    monkeypatch.setattr(module, 'observe', observe)
    module.run(root)
    assert calls == p['jobs'] and module.read(root / 'terminal.json')['completed_jobs'] == 16
    assert module.read(root / 'terminal.json')['status'] == 'closed'
    assert module.read(root / 'observer-audit.json') == CommonContentObserver(root / 'observer', p['observer_contract'], backend=None).audit()
    with pytest.raises(ValueError, match='consumed'): module.run(root)


def test_unknown_completion_stops_and_later_seeds_are_not_dispatched(tmp_path, monkeypatch):
    root, _, _ = setup(tmp_path, monkeypatch); calls = []
    def observe(*args): calls.append(1); raise ObserverCompletionUnknown('SCRIPTED unresolved')
    monkeypatch.setattr(module, 'observe', observe)
    with pytest.raises(ObserverCompletionUnknown): module.run(root)
    assert calls == [1] and module.read(root / 'terminal.json')['status'] == 'stopped'
    assert module.read(root / 'terminal.json')['completed_jobs'] == 0


def test_new_seed_consumption_blocks_before_start_and_inference(tmp_path, monkeypatch):
    root, _, u = setup(tmp_path, monkeypatch); u['valid'] = False; seal(u)
    monkeypatch.setattr(module, 'observe', lambda *a: pytest.fail('seed proof must stop before science'))
    with pytest.raises(ValueError, match='consumed after preparation'): module.run(root)
    assert not (root / 'started.json').exists()


def test_fixed_evaluation_finish_uses_exact_new_schema_and_original_auditor(monkeypatch):
    seen = {}; monkeypatch.setattr(finish, 'finish', lambda args, **kw: seen.update(kw)); finish.run(SimpleNamespace())
    assert seen['plan_schema'] == 'scienceutopia.native-planning-fixed-evaluation.v1.plan'
    assert seen['audit_module'] == 'scripts.audit_native_planning_fixed_evaluation_v1'
