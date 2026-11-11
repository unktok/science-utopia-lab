import json
import math
from pathlib import Path

import pytest

from scripts.reports.native_resource_support_summary_v1 import compact
from scripts.reports.native_resource_support_v1 import snapshot
from tests.reports.test_native_resource_support_v1 import state
from utopia.system.design_patch import digest


def fixture():
    annual=[]
    for year in (1,2,3,4):
        s=state();s['year']=year;annual.append({**snapshot(s),'checkpoint_sha256':'a'*64})
    r={'schema':'scienceutopia.native-year-end-resource-support.v1','worlds':[
        {'identity':'SCRIPTED','role':'SCRIPTED','seed':1,'annual':annual}],
        'source_commit':'c'*40,'input_full_audit_content_sha256':'b'*64,'input_full_audit_file_sha256':'d'*64,
        'analysis_adapter_sha256':'e'*64,'summary':{'complete_worlds':1,'skipped_worlds':0,
            'annual_boundaries':4,'actor_boundaries':8,'active_actor_boundaries':4,
            'minimum_observed_year_end_actor_resources':0.,'maximum_observed_year_end_actor_resources':20.,
            'year_end_active_author_distribution':{'1':4},'recorded_initial_funding_distribution':{'100.0':8}},
        'scope':{'new_model_calls':0},'skipped_worlds':[]}
    r['content_sha256']=digest(r);return r


def test_portable_vectors_preserve_literal_zero_and_inactive_states():
    r=fixture();d=compact(json.dumps(r).encode())
    for row in d['per_year']:
        assert row['actor_boundaries']==2 and row['active_actor_boundaries']==1 and row['minimum_actor_resources']==0
    assert all(sorted(row['resources'])==[0.,20.] for row in d['worlds'][0]['annual'])
    assert d['scope']['new_model_calls']==0


@pytest.mark.parametrize('change',['order','actor-identity','duplicate-actor','aggregate'])
def test_changed_time_or_actor_vector_correspondence_is_not_packed(change):
    r=fixture()
    if change=='order':r['worlds'][0]['annual'].reverse()
    elif change=='actor-identity':r['worlds'][0]['annual'][1]['actors'][0]['actor_id_sha256']='f'*64
    elif change=='duplicate-actor':r['worlds'][0]['annual'][0]['actors'][1]['actor_id_sha256']=r['worlds'][0]['annual'][0]['actors'][0]['actor_id_sha256']
    else:r['summary']['minimum_observed_year_end_actor_resources']=999
    r['content_sha256']=digest({k:v for k,v in r.items() if k!='content_sha256'})
    with pytest.raises(ValueError):compact(json.dumps(r).encode())


def test_all_retained_numeric_vectors_rebuild_yearly_counts_and_join_old_final_measurements():
    from utopia.optimization.native_numeric_designer import checked
    root=Path(__file__).resolve().parents[2]
    data=checked(json.loads((root/'research/data/native-resource-support-v1/summary.json').read_text()))
    old=checked(json.loads((root/'research/data/pre-scale-search-v1/report.json').read_text()))
    assert data['input_full_audit_content_sha256']==old['audit_sha256']
    worlds={w['identity']:w for w in old['worlds'] if w['status']=='complete'}
    assert set(worlds)=={w['identity'] for w in data['worlds']} and len(worlds)==44
    for w in data['worlds']:
        n=len(w['actor_id_sha256s']);assert n==5
        assert [y['year'] for y in w['annual']]==[1,2,3,4]
        assert all(len(y[key])==n for y in w['annual'] for key in
            ('resources','is_active','initial_funding','project_start_year','project_end_year'))
        last=w['annual'][-1];metrics=worlds[w['identity']]['measurement']['metrics']
        assert sum(last['is_active'])==metrics['native.final_active_authors']['value']
        assert math.isclose(math.fsum(last['resources']),metrics['native.final_author_resources']['value'],abs_tol=1e-12)
    for row in data['per_year']:
        annual=[w['annual'][row['year']-1] for w in data['worlds']]
        assert sum(len(a['resources']) for a in annual)==row['actor_boundaries']
        assert sum(sum(a['is_active']) for a in annual)==row['active_actor_boundaries']
        assert min(v for a in annual for v in a['resources'])==row['minimum_actor_resources']
        assert max(v for a in annual for v in a['resources'])==row['maximum_actor_resources']
