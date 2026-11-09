"""Synthetic all-null search/explicit shared evaluation projection tests."""
from copy import deepcopy

import pytest

from scripts.reports.pre_scale_search_v1 import summarize
from scripts.audit_pre_scale_search_v1 import actual_policy_order
from scripts.run_pre_scale_search_v1 import evaluation_jobs,selection_payload,campaign
from tests.reports.test_pre_scale_search_v1 import plan,references
from utopia.system.design_patch import digest


def fixture(root):
    p=plan();references(root,p)
    def forbidden(*args):pytest.fail('a null submission cannot dispatch a world')
    for arm in p['arm_order']:
        c=campaign(root,p,'run-00',arm)
        for _ in range(2):c.advance(simulation_factory=forbidden,
            generators={p['assignments'][arm]['strategy']:lambda request:None},count=1)
    s=selection_payload(root,p,frozen_utc='SCRIPTED',campaign_loader=campaign);jobs=evaluation_jobs(p,s)
    worlds=[{'identity':j['identity'],'role':'selection-fixed-evaluation','seed':j['seed'],
        'status':'complete','scores':{'throughput':0,'efficiency':0,'selective':0},'physical_proof':{}} for j in jobs]
    a={'schema':'scienceutopia.pre-scale-search-audit.v1','source_commit':'a'*40,'plan_sha256':p['content_sha256'],
        'selection':s,'worlds':worlds,'logical_evaluation':actual_policy_order(p,s,jobs)}
    a['content_sha256']=digest(a);return a


def rehash(value):
    value.pop('content_sha256');value['content_sha256']=digest(value);return value


def test_all_null_slots_and_shared_evaluation_stay_visible_without_invented_improvement(tmp_path):
    a=fixture(tmp_path);original=deepcopy(a);r=summarize(a)
    assert a==original and len(r['search_slots'])==16
    assert r['status_counts']=={'generation-failure':16}
    assert all(x['own_loss'] is None for x in r['search_slots'])
    assert all(not x['strict_development_gain_over_initial'] for x in r['optimization_paths'].values())
    assert r['logical_evaluation_rows']==36 and r['physical_evaluation_worlds']==12
    assert len(r['paired_reference_differences'])==96
    assert all(v['scientist_call_component_seconds'] is None for v in r['worlds'])
    assert [v['row_id'] for v in r['search_slots']]==[v['row_id'] for v in a['selection']['all_rows'] if v['arm'] is not None]


def test_unavailable_initial_efficiency_is_not_imputed_or_compared_as_zero(tmp_path):
    a=fixture(tmp_path)
    next(r for r in a['selection']['all_rows'] if r['row_id']=='reference:open-seed')['cross_scores']['efficiency']=None
    for arm,v in a['selection']['selected'].items():
        if arm.startswith('efficiency:'):v['loss']=None
    r=summarize(rehash(a))
    assert all(v['strict_development_gain_over_initial'] is None for k,v in r['optimization_paths'].items()
        if k.startswith('efficiency:'))


@pytest.mark.parametrize('problem',['missing-slot','duplicate-evaluation','missing-evaluation','fabricated-loss'])
def test_inconsistent_results_cannot_be_projected(problem,tmp_path):
    a=fixture(tmp_path)
    if problem=='missing-slot':a['selection']['all_rows'].pop()
    if problem=='duplicate-evaluation':a['logical_evaluation'].append(deepcopy(a['logical_evaluation'][0]))
    if problem=='missing-evaluation':a['logical_evaluation'].pop()
    if problem=='fabricated-loss':
        next(r for r in a['selection']['all_rows'] if r['arm'] is not None)['cross_scores']['throughput']=-5
    with pytest.raises(ValueError):summarize(rehash(a))
