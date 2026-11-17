"""SCRIPTED finite study contracts, not actual model/native effectiveness."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from scripts import run_native_literal_feedback_comparison_v1 as driver
from tests.reports.test_native_corrected_choice_search_v1 import seal
from tests.reports.test_native_topic_free_plan_v1 import plan as free_plan
from utopia.optimization.native_component_parameter_context_v1 import OPTION, SCOPE
from utopia.optimization.native_literal_change_feedback_v1 import OPTION as CHANGE_OPTION, VIEW
from utopia.optimization.native_staged_author_v15 import build_prompt, initial_draft
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING


def plan(tmp_path, monkeypatch):
    old, original = free_plan(tmp_path, monkeypatch)
    p = driver.build_plan(original, {'content_sha256': 'SCRIPTED-upstream'},
        source=old['source_commit'], origin={'SCRIPTED': True}, backend=old['backend'],
        observer_backend=old['observer_contract']['backend'],
        bank=seal({**old['component_bank'], OPTION: SCOPE}),
        evidence={**old['component_evidence'], 'parameter_context_scope': SCOPE},
        sources=old['original_native_sources'])
    return seal(p), old


def test_finite_same_world_losses_authority_and_budget_not_forced_novelty(tmp_path, monkeypatch):
    p, old = plan(tmp_path, monkeypatch)
    assert driver.open_institutions(p)
    assert p['losses'] == old['losses'] and p['scientist'] == old['scientist']
    assert p['world']['world_conditions'] == old['world']['world_conditions']
    assert p['scientist_transport'] == old['scientist_transport']
    assert p['designer'] == old['designer'] and p['design_space'] == old['design_space']
    assert p['generations'] == 2 and p['replication_seeds'] == [79011]
    assert len(p['schedule']) == 8 and len(driver.history_keys(p)) == 4
    assert p['schedule'][4:] == [{**s, 'generation': 1} for s in p['schedule'][:4][::-1]]
    assert p['budget']['candidate_slots'] == 8 and p['budget']['native_worlds_upper_bound'] == 11
    assert p['budget']['readiness_sessions'] == 10
    assert p['budget']['designer_POSTs_upper_bound'] == 10*40+8*16 == 528
    assert p['budget']['component_probes_upper_bound'] == 8*64 == 512
    assert not p['budget']['replace_failed_slots'] and not p['held_out_evaluation']
    assert not p['literal_feedback_contract']['veto_on_finish']
    assert not p['comparison']['forced_change_or_gain']
    assert driver.initial_readiness_jobs(p) == [
        ((arm, 0, driver.OBJECTIVES[0]), driver.Path('initial-readiness')/arm) for arm in driver.ARMS]


def test_real_campaign_requests_change_only_declared_information_and_binding_not_rng_or_loss(tmp_path, monkeypatch):
    p, _ = plan(tmp_path, monkeypatch)
    for objective in driver.OBJECTIVES:
        requests = []
        for arm in driver.ARMS:
            c = driver.campaign(tmp_path/'campaigns', p, (arm,0,objective))
            body = c._request([], c._validate(), 1)
            assert body['loss_spec'] == p['losses'][objective]
            requests.append(body)
        a, b = deepcopy(requests)
        assert CHANGE_OPTION not in a['strategy_provenance']
        assert b['strategy_provenance'].pop(CHANGE_OPTION) == driver.contract()
        assert a.pop('binding_sha256') != b.pop('binding_sha256')
        assert a == b  # Includes exact generation RNG, native world, parent and all other context.
        for body, enabled in zip(requests, (False, True)):
            prompt = build_prompt(body, initial_draft(body), [], image_id=p['designer']['image_id'],
                binding_sha256='d'*64, settings={'max_steps':16, 'conversation_profile':BOUNDED_AUTHORING})
            assert (VIEW in json.loads(prompt)) == enabled


@pytest.mark.parametrize('own_status,own_loss,origin', [
    ('complete',-9.,'reference'), ('complete',-10.,'reference'),
    ('complete',-11.,'own'), ('failed',None,'reference')])
def test_both_selection_banks_preserve_ties_nulls_and_all_own_outcomes(
        tmp_path, monkeypatch, own_status, own_loss, origin):
    p, _ = plan(tmp_path, monkeypatch)
    ref = {'status':'complete','loss':-10.,'suggestion_id':'SCRIPTED-ref','candidate':{'SCRIPTED':'ref'}}
    own = {'status':own_status,'loss':own_loss,'suggestion_id':'SCRIPTED-own','candidate':{'SCRIPTED':'own'}}
    monkeypatch.setattr(driver.preceding, 'objective_view', lambda *a: {'observations':[{'observation':ref}]})
    monkeypatch.setattr(driver, 'campaign', lambda *a,**kw: SimpleNamespace(state={
        'pending':None,'records':[{'observations':[deepcopy(own)]},{'observations':[]}]}))
    result = driver.selection(tmp_path, p, {})
    for key in driver.history_keys(p):
        primary = result['selected'][key[0]]['0'][key[2]]
        secondary = result['own_only_selected'][key[0]]['0'][key[2]]
        assert primary['selected_origin'] == origin and secondary['loss'] == own_loss
        assert secondary['completed_submissions'] == int(own_status == 'complete')
        if own_status == 'failed': assert secondary['selected_id'] is secondary['system'] is None
    assert not result['baseline_fallback']


@pytest.mark.parametrize('error', [ValueError('SCRIPTED calibration failed'), KeyboardInterrupt('SCRIPTED unknown')])
def test_initial_readiness_failure_retains_stop_and_never_redispatches(tmp_path, monkeypatch, error):
    p, _ = plan(tmp_path/'plan', monkeypatch)
    root = tmp_path/'run'; root.mkdir(); origin = tmp_path/'origin'; origin.mkdir()
    (origin/'writer.lock').touch(); p['origin'] = {'run':str(origin)}
    monkeypatch.setattr(driver,'require_plan',lambda root:p)
    monkeypatch.setattr(driver.free.base,'require_environment',lambda:None)
    monkeypatch.setattr(driver,'campaign',lambda *a,**kw:SimpleNamespace(_request=lambda *a:{'SCRIPTED':True},_validate=lambda:None))
    calls = []
    class Author:
        def calibrate(self, request): calls.append(request); raise error
    monkeypatch.setattr(driver,'designer_for',lambda *a:Author())
    monkeypatch.setattr(driver,'evaluate_native_suggestion',lambda *a,**kw:pytest.fail('no native after failed readiness'))
    with pytest.raises(type(error)): driver.run(root)
    terminal = driver.read(root/'terminal.json')
    assert terminal['status'] == 'stopped' and terminal['consumed_slots'] == 0 and terminal['observations'] == 0
    with pytest.raises(ValueError,match='no redispatch'): driver.run(root)
    assert len(calls) == 1
