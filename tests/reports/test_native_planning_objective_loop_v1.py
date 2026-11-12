"""SCRIPTED finite controller/budget checks; not local-model design evidence."""
from pathlib import Path

import pytest

from scripts import run_native_planning_objective_loop_v1 as driver
from scripts.run_native_catalog_actuation_v1 import build_plan as catalog_plan
from tests.reports.test_native_capacity_objective_loop_v1 import plan as capacity_plan
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_bounded_staged_designer import CompletionUnknown
from utopia.optimization.common_content_observer import ObserverCompletionUnknown
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest


def seal(value):
    value.pop('content_sha256', None); value['content_sha256'] = digest(value); return value


def plan(tmp_path, monkeypatch, image_override=None):
    operator = capacity_plan(tmp_path / 'operator', monkeypatch, image_override=image_override)
    support = tmp_path / 'support'; support.mkdir(parents=True)
    driver.save(support / 'plan.json', {'bank_file_sha256': operator['component_bank_file_sha256']})
    driver.save(support / 'summary.json', {'status': 'closed', 'observations': [{'original_result_matches': True}] * 12})
    operator['component_support'] = {'directory': str(support),
        'plan_file_sha256': driver.file_sha256(support / 'plan.json'),
        'summary_file_sha256': driver.file_sha256(support / 'summary.json')}
    real = driver.read
    def read(path):
        if Path(path) == driver.ROOT / driver.BANK_MANIFEST:
            return {'bank_file_sha256': operator['component_bank_file_sha256'],
                'bank_content_sha256': operator['component_bank']['content_sha256']}
        return real(path)
    monkeypatch.setattr(driver, 'read', read)
    audit = seal({'SCRIPTED': 'original catalog closure is mocked'})
    original = seal(catalog_plan(operator, audit, source='d' * 40, origin={'SCRIPTED': True}))
    origin = {'run': str(tmp_path / 'origin'), 'SCRIPTED': 'not real original attestation'}
    p = seal(driver.build_plan(operator, original, audit, source='c' * 40, backend=operator['backend'],
        observer_backend={**{k: operator['scientist'][k] for k in ('model', 'model_digest')}, 'ollama_version': 'SCRIPTED'},
        origin=origin))
    return p, operator, original, audit


def test_same_world_old_TU_new_authority_eight_strong_controls_and_exact_finite_budget(tmp_path, monkeypatch):
    p, operator, original, _ = plan(tmp_path, monkeypatch)
    assert p['initial_system'] == original['jobs'][0]['system']
    assert p['world']['world_conditions'] == operator['world']['world_conditions']
    assert p['objectives'] == ['throughput', 'content-utility'] and p['generations'] == 3
    assert p['losses']['content-utility']['per_run']['terms'] == [
        {'metric_id': 'native.common_content_utility_sum', 'slice_id': None, 'coefficient': -1.}]
    assert len(p['reference_order']) == 8 and len(p['schedule']) == 6
    assert p['budget']['native_worlds_upper_bound'] == 14 and p['budget']['readiness_sessions'] == 7
    assert p['budget']['observer_POSTs_upper_bound'] == p['observer_contract']['maximum_posts'] == 1500
    assert p['post_edit_contract']['maximum_probe_attempts'] == 64
    assert p['development_seed_reused'] and not p['held_out_evaluation']
    assert not p['P_is_an_objective_or_constraint'] and not p['old_losses_reused_as_development_observations']
    assert not p['budget']['replace_failed_slots']


def test_literal_prepared_plan_rebuild_rejects_changed_scope_budget_or_rule(tmp_path, monkeypatch):
    p, operator, original, audit = plan(tmp_path, monkeypatch); root = tmp_path / 'prepared'
    driver.save(root / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    monkeypatch.setattr(driver, 'origin_evidence', lambda origin: (operator, original, audit))
    monkeypatch.setattr(driver, 'pinned_revision', lambda root: p['source_commit'])
    assert driver.require_plan(root) == p
    p['budget']['proposal_POSTs_per_session'] = 17
    other = tmp_path / 'changed'; driver.save(other / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    with pytest.raises(ValueError, match='reconstruction'): driver.require_plan(other)


def setup(tmp_path, monkeypatch):
    p, _, _, _ = plan(tmp_path, monkeypatch); root = tmp_path / 'run'; root.mkdir()
    origin = Path(p['origin']['run']); origin.mkdir(); (origin / 'writer.lock').touch()
    monkeypatch.setattr(driver, 'require_environment', lambda: None)
    monkeypatch.setattr(driver, 'require_plan', lambda root: p)
    contexts = []
    def context(pairs, **kw):
        contexts.append(clone(pairs)); return seal({'SCRIPTED': 'not actual native reference receipts'})
    monkeypatch.setattr(driver, 'build_context', context)
    # Real journal/slot logic, explicitly without mocked-reference validation.
    def campaign(root, p, objective, context=None, *, prototype=False):
        path = root / 'initial-readiness/campaign' if prototype else root / 'search' / objective / 'campaign'
        return NativeAdaptiveDesignCampaign(path, initial_system=SystemSpec.from_dict(p['initial_system']),
            loss_spec=p['losses'][objective], seeds=[driver.SEED], world_binding=p['world'], strategies=p['strategies'],
            mode='blackbox', seed=p['optimizer_seed'], design_space=p['design_space'])
    monkeypatch.setattr(driver, 'campaign', campaign)
    monkeypatch.setattr(driver, 'factory_for', lambda *a: lambda *a: pytest.fail('generation null must not dispatch science'))
    return root, p, contexts


def test_initial_gate_eight_references_six_nulls_seven_gates_and_no_reference_fallback(tmp_path, monkeypatch):
    root, p, contexts = setup(tmp_path, monkeypatch); events, requests = [], []
    monkeypatch.setattr(driver, 'observe', lambda root, p, label, observer: events.append('reference') or {'SCRIPTED': label})
    def readiness(root, p, **kw):
        events.append('readiness'); requests.append(clone(kw['request'])); return tmp_path / 'SCRIPTED-cert'
    monkeypatch.setattr(driver, 'readiness', readiness)
    def execute(*a, **kw):
        events.append('proposal'); assert kw['seconds'] == 1800 and kw['post_edit_bank'] == p['component_bank']
        return {'generation_failure': 'SCRIPTED known non-submission'}
    monkeypatch.setattr(driver, 'execute', execute); driver.run(root)
    assert events[:9] == ['readiness'] + ['reference'] * 8
    assert events.count('readiness') == 7 and events.count('proposal') == 6
    assert [len(r['history']) for r in requests] == [0, 0, 0, 1, 1, 2, 2]
    assert len(contexts) == 1 and len(contexts[0]) == 8
    selected = driver.read(root / 'selection.json')
    assert not selected['baseline_fallback'] and all(v['system'] is None for v in selected['selected'].values())
    assert driver.read(root / 'terminal.json')['status'] == 'closed'
    assert driver.read(root / 'observer-audit.json')['dispatch_intents'] == 0
    with pytest.raises(ValueError, match='no redispatch'): driver.run(root)


@pytest.mark.parametrize('failure', ['initial', 'reference', 'critic-unknown', 'designer-unknown'])
def test_failed_or_unknown_stages_stop_without_later_scientific_dispatch(tmp_path, monkeypatch, failure):
    root, _, _ = setup(tmp_path, monkeypatch); events = []
    def readiness(*a, **kw):
        events.append('readiness')
        if failure == 'initial': raise ValueError('SCRIPTED failed initial readiness')
        return tmp_path / 'SCRIPTED-cert'
    def observe(*a):
        events.append('reference')
        if failure == 'reference': raise ValueError('SCRIPTED failed reference')
        if failure == 'critic-unknown': raise ObserverCompletionUnknown('SCRIPTED unknown observer dispatch')
        return {'SCRIPTED': 'reference'}
    def execute(*a, **kw):
        events.append('proposal'); raise CompletionUnknown('SCRIPTED uncertain designer')
    monkeypatch.setattr(driver, 'readiness', readiness); monkeypatch.setattr(driver, 'observe', observe)
    monkeypatch.setattr(driver, 'execute', execute)
    with pytest.raises((ValueError, ObserverCompletionUnknown, CompletionUnknown)): driver.run(root)
    assert driver.read(root / 'terminal.json')['status'] == 'stopped'
    assert not (root / 'selection.json').exists()
    assert events.count('proposal') <= 1
    if failure == 'initial': assert events == ['readiness']
