"""Scripted orchestration checks, never new LLM or scientific evidence."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_institution_loop_v1 as driver
from tests.optimization.test_native_numeric_designer import PROVIDER, BACKEND
from utopia.optimization.native_bounded_staged_designer import CompletionUnknown
from utopia.optimization.native_design_space import require_candidate_in_space
from utopia.optimization.native_numeric_designer import save
from utopia.system import SystemSpec
from utopia.system.design_patch import digest


def plan():
    scientist = {**deepcopy(PROVIDER), 'model':'qwen3:8b',
        'model_digest':'500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41'}
    p = driver.build_plan(source='a'*40,
        operator={'scientist':scientist,'designer':PROVIDER,'data_cache':'/SCRIPTED/no-data'},
        backend=BACKEND, seed_usage=[{'valid':True,'errors':[], 'prior_matching_runs':[],
                                     'content_sha256':'b'*64}])
    return {**p, 'content_sha256':digest(p)}


def test_finite_pilot_preserves_original_losses_new_rights_and_nonclaim_boundaries():
    p = plan()
    assert len(p['schedule']) == 12 and len(p['reference_order']) == 8
    assert p['budget']['native_worlds_upper_bound'] == 8+12+33
    assert not p['budget']['replace_failed_slots']
    assert all(b['strategies']['local-designer']['causal_design_presentation']=='inline'
               for b in p['campaign_bindings']['run-00'].values())
    assert all(b['design_space']['world_law_scope']=='fixed-native-production-review-routing-v2'
               for b in p['campaign_bindings']['run-00'].values())
    assert not p['claims']['graph_syntax_necessary'] and not p['claims']['method_superiority']
    anchor = SystemSpec.from_dict(p['reference_systems']['open-seed'])
    domain = p['campaign_bindings']['run-00']['efficiency:code-and-graph']['design_space']
    for label in ('routed-one-accept-all','routed-two-accept-all','routed-one-reject-all'):
        require_candidate_in_space(anchor,SystemSpec.from_dict(p['reference_systems'][label]),domain)
    assert p['losses']['efficiency']['per_run']['terms'][1]['coefficient'] == .5


@pytest.mark.parametrize('count', [True, -1, 65, 1.0])
def test_reference_builder_does_not_coerce_invalid_counts(count):
    from utopia.optimization.native_review_routing_controls import routed_control
    from tests.optimization.test_native_causal_design import anchor
    with pytest.raises(ValueError):
        routed_control(anchor(),reviewers_per_paper=count,snapshot_phase=85,producer_phase=87)


def setup(root, monkeypatch):
    p=plan();save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    monkeypatch.setattr(driver,'require_environment',lambda:None)
    monkeypatch.setattr(driver,'require_plan',lambda root:p)
    return p


def test_unknown_readiness_stops_before_any_world_and_run_cannot_refill(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch)
    monkeypatch.setattr(driver,'readiness',lambda *a,**k:(_ for _ in ()).throw(CompletionUnknown('SCRIPTED missing final reply')))
    monkeypatch.setattr(driver,'observe',lambda *a:pytest.fail('unknown completion cannot start world'))
    with pytest.raises(CompletionUnknown):driver.run(tmp_path)
    assert driver.read(tmp_path/'terminal.json')['status']=='stopped'
    with pytest.raises(ValueError,match='immutable'):driver.run(tmp_path)


def test_all_generation_nulls_are_charged_then_selection_is_frozen_before_evaluation(tmp_path,monkeypatch):
    p=setup(tmp_path,monkeypatch); calibrations=[]; worlds=[]
    monkeypatch.setattr(driver,'readiness',lambda *a,**k:calibrations.append(k['numeric']) or tmp_path/'SCRIPTED-cert')
    monkeypatch.setattr(driver,'load_local_role',lambda *a,**k:None)
    monkeypatch.setattr(driver,'NumericDesigner',lambda *a,**k:lambda request:None)
    monkeypatch.setattr(driver,'BoundedStagedDesigner',lambda *a,**k:lambda request:None)
    monkeypatch.setattr(driver,'LocalRoleBoundNativeFactory',lambda *a,**k:None)
    def observe(cell,p,identity,system,seed,role):
        if role=='selection-fixed-evaluation':
            assert (tmp_path/'selection.json').exists() and (tmp_path/'evaluation-plan.json').exists()
        measurements=[{'run_id':'SCRIPTED','metrics':{k:{'status':'measured','value':0} for k in
            ('native.accepted_decisions','native.accepted_peer_score_sum','native.review_records')}}]
        result={'candidate':system,'status':'complete','loss':0,
            'metadata':{'technical_failures':[],'runs':[{'run_id':'SCRIPTED'}],'measurements':measurements}}
        save(cell/'observation.json',result);worlds.append((role,seed));return result
    monkeypatch.setattr(driver,'observe',observe)
    driver.run(tmp_path)
    assert driver.read(tmp_path/'terminal.json')['status']=='closed'
    selected=driver.read(tmp_path/'selection.json')
    assert len(selected['all_rows'])==20
    assert sum(r['status']=='generation-failure' for r in selected['all_rows'])==12
    assert all(r['selected_row_id']=='reference:open-seed' for r in selected['selected'].values())
    assert calibrations.count(False)==9 and calibrations.count(True)==5
    jobs=driver.read(tmp_path/'evaluation-plan.json')['jobs']
    assert len(jobs)==18 and set(j['seed'] for j in jobs)==set(driver.EVALUATION_SEEDS)
    assert len(worlds)==8+18 # invalid proposal causes no invented native execution


def test_numeric_readiness_creates_fresh_parent_before_calibration(tmp_path,monkeypatch):
    p=plan();target=tmp_path/'new-parent'
    def calibration(root,parameters,request_factory):
        import fcntl
        assert root.is_dir()
        with (tmp_path/'inference.lock').open('a') as competitor:
            with pytest.raises(BlockingIOError):
                fcntl.flock(competitor,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert all(request_factory(o)['strategy_provenance']['causal_design_presentation']=='inline'
                   for o in driver.OBJECTIVES)
        save(root/'numeric-readiness/certificate.json',{'passed':True})
    monkeypatch.setattr(driver,'numeric_calibration',calibration)
    driver.readiness(tmp_path,p,request={},numeric=True,target=target)
