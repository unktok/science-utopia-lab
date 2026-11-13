"""SCRIPTED finite slots, exact planning treatment and no hidden replacement."""
from pathlib import Path

import pytest

from scripts import run_native_parent_presentation_loop_v1 as driver
from tests.reports.test_native_planning_objective_loop_v1 import plan as original_plan, seal
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_bounded_staged_designer import CompletionUnknown
from utopia.optimization.native_parent_evidence_v46 import OPTION, MODE
from utopia.system import SystemSpec
from utopia.system.design_patch import clone


def plan(tmp_path, monkeypatch, image_override=None):
    _, operator, original, audit = original_plan(tmp_path, monkeypatch, image_override)
    origin = {'run': str(tmp_path/'origin'), 'SCRIPTED': 'catalog origin primitive mocked'}
    p = seal(driver.build_plan(operator, original, audit, source='c'*40,
        backend=operator['backend'], observer_backend={**{k:operator['scientist'][k]
            for k in ('model','model_digest')}, 'ollama_version':'SCRIPTED'}, origin=origin))
    return p, operator, original, audit


def test_exact_four_histories_same_world_losses_authority_and_finite_schedule(tmp_path, monkeypatch):
    p, operator, _, _ = plan(tmp_path, monkeypatch)
    assert p['world']['world_conditions'] == operator['world']['world_conditions']
    assert p['objectives'] == ['throughput','content-utility']
    assert p['arm_order'] == list(driver.ARM_ORDER) and len(p['arms']) == 4
    assert [s['arm'] for s in p['schedule']] == list(driver.ARM_ORDER)+list(driver.ARM_ORDER[::-1])+list(driver.ARM_ORDER)
    assert p['budget']['native_worlds_upper_bound'] == 20 and p['budget']['candidate_slots'] == 12
    assert p['budget']['readiness_sessions'] == 14 and p['budget']['initial_readiness_sessions'] == 2
    assert p['budget']['designer_http_timeout_seconds'] == [10,900]
    assert p['observer_contract']['maximum_posts'] == p['budget']['observer_POSTs_upper_bound'] == 3000
    assert p['post_edit_contract']['maximum_probe_attempts'] == 64
    control = p['strategies_by_presentation']['control']
    literal = clone(p['strategies_by_presentation']['literal'])
    assert literal['local-designer'].pop(OPTION) == MODE and literal == control
    assert not p['P_is_an_objective_or_constraint'] and not p['budget']['replace_failed_slots']
    assert not p['motivation_evidence']['reused_as_current_observation']
    assert not p['held_out_evaluation'] and not p['publication_ready']


def test_reconstruction_rejects_changed_presentation_scope_budget_or_source(tmp_path, monkeypatch):
    p, operator, original, audit = plan(tmp_path, monkeypatch)
    root = tmp_path/'prepared'
    driver.save(root/'plan.json', {k:v for k,v in p.items() if k != 'content_sha256'})
    monkeypatch.setattr(driver, 'pinned_revision', lambda root:p['source_commit'])
    monkeypatch.setattr(driver.base, 'origin_evidence', lambda origin:(operator,original,audit))
    assert driver.require_plan(root) == p
    p['budget']['candidate_slots'] = 13
    other = tmp_path/'changed'
    driver.save(other/'plan.json', {k:v for k,v in p.items() if k != 'content_sha256'})
    with pytest.raises(ValueError, match='reconstruction'):
        driver.require_plan(other)


def setup(tmp_path, monkeypatch):
    p, _, _, _ = plan(tmp_path, monkeypatch)
    root = tmp_path/'run'; root.mkdir()
    origin = Path(p['origin']['run']); origin.mkdir(); (origin/'writer.lock').touch()
    monkeypatch.setattr(driver, 'require_environment', lambda:None)
    monkeypatch.setattr(driver, 'require_plan', lambda root:p)
    monkeypatch.setattr(driver.base, 'build_context', lambda *a,**k:seal({'SCRIPTED':'reference validation mocked'}))
    def campaign(root, p, arm, context=None, *, prototype=False):
        a = p['arms'][arm]
        path = root/'initial-readiness'/a['presentation']/'campaign' if prototype else root/'search'/arm/'campaign'
        return NativeAdaptiveDesignCampaign(path, initial_system=SystemSpec.from_dict(p['initial_system']),
            loss_spec=p['losses'][a['objective']], seeds=[driver.SEED], world_binding=p['world'],
            strategies=p['strategies_by_presentation'][a['presentation']], mode='blackbox',
            seed=p['optimizer_seed'], design_space=p['design_space'])
    monkeypatch.setattr(driver, 'campaign', campaign)
    monkeypatch.setattr(driver, 'factory_for', lambda *a:lambda *a:pytest.fail('known generation null must not dispatch science'))
    return root, p


def test_two_initial_gates_eight_references_twelve_nulls_and_four_own_selections(tmp_path, monkeypatch):
    root, p = setup(tmp_path, monkeypatch)
    events, requests = [], []
    monkeypatch.setattr(driver, 'observe', lambda r,p,label,o:events.append('reference') or {'SCRIPTED':label})
    def readiness(root,p,**kw):
        events.append('readiness'); requests.append(clone(kw['request']))
        return tmp_path/'SCRIPTED-certificate'
    monkeypatch.setattr(driver, 'readiness', readiness)
    def execute(*a,**kw):
        events.append('proposal')
        assert kw['seconds'] == 1800 and kw['maximum_posts'] == 16
        assert kw['post_edit_bank'] == p['component_bank']
        return {'generation_failure':'SCRIPTED known non-submission'}
    monkeypatch.setattr(driver, 'execute', execute)
    driver.run(root)
    assert events[:10] == ['readiness']*2+['reference']*8
    assert events.count('readiness') == 14 and events.count('proposal') == 12
    assert [len(r['history']) for r in requests] == [0,0]+[0]*4+[1]*4+[2]*4
    assert [OPTION in r['strategy_provenance'] for r in requests[:2]] == [False,True]
    assert [OPTION in r['strategy_provenance'] for r in requests[2:]] == [s['presentation']=='literal' for s in p['schedule']]
    selected = driver.read(root/'selection.json')
    assert set(selected['selected']) == set(p['arms']) and not selected['baseline_fallback']
    assert all(v['system'] is None and v['loss'] is None for v in selected['selected'].values())
    assert driver.read(root/'terminal.json')['status'] == 'closed'
    with pytest.raises(ValueError,match='no redispatch'):
        driver.run(root)


@pytest.mark.parametrize('failure', ['control-initial','literal-initial','reference','designer-unknown'])
def test_failures_stop_without_unplanned_model_calls_or_reference_fallback(tmp_path, monkeypatch, failure):
    root, _ = setup(tmp_path, monkeypatch)
    events = []
    def readiness(root,p,**kw):
        events.append('readiness')
        mode = OPTION in kw['request']['strategy_provenance']
        if (failure == 'control-initial' and not mode or failure == 'literal-initial' and mode):
            raise ValueError('SCRIPTED initial readiness failed')
        return tmp_path/'SCRIPTED-certificate'
    def observe(*a):
        events.append('reference')
        if failure == 'reference': raise ValueError('SCRIPTED reference failed')
        return {'SCRIPTED':'reference'}
    def execute(*a,**kw):
        events.append('proposal'); raise CompletionUnknown('SCRIPTED unknown dispatch')
    monkeypatch.setattr(driver,'readiness',readiness)
    monkeypatch.setattr(driver,'observe',observe)
    monkeypatch.setattr(driver,'execute',execute)
    with pytest.raises((ValueError,CompletionUnknown)):
        driver.run(root)
    assert driver.read(root/'terminal.json')['status'] == 'stopped'
    assert not (root/'selection.json').exists()
    if failure == 'control-initial': assert events == ['readiness']
    if failure == 'literal-initial': assert events == ['readiness']*2
    assert events.count('proposal') <= 1
