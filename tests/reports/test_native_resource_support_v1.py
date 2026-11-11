from copy import deepcopy

import pytest

from scripts.reports.native_resource_support_v1 import snapshot


def state():
    actors=[{'id':str(i),'can_author':True,'resources':value,'is_active':value>0,
        'initial_funding':100.,'project_start_year':1,'project_end_year':2} for i,value in enumerate([20.,0.])]
    return {'year':2,'ecosystem_data':{'agents':actors+[{'id':'agency','can_author':False}]},
        'portable':{'agent_states':{a['id']:{'state':deepcopy(a)} for a in actors}}}


def test_literal_stock_and_inactivity_are_preserved_not_repaired():
    a=state();before=deepcopy(a);r=snapshot(a)
    assert a==before and r['year_end_minimum_actor_resources']==0
    assert r['year_end_active_authors']==1 and r['year_end_total_resources']==20
    assert all(len(v['actor_id_sha256'])==64 for v in r['actors'])


@pytest.mark.parametrize('change',['portable','nan','boolean-resource','activity-string','duplicate','no-authors'])
def test_changed_or_ambiguous_restoration_is_not_a_valid_stock(change):
    a=state();actor=a['ecosystem_data']['agents'][0]
    if change=='portable':a['portable']['agent_states']['0']['state']['resources']=999
    elif change=='nan':actor['resources']=float('nan')
    elif change=='boolean-resource':actor['resources']=True
    elif change=='activity-string':actor['is_active']='true'
    elif change=='duplicate':a['ecosystem_data']['agents'].append(deepcopy(actor))
    else:a['ecosystem_data']['agents']=[]
    with pytest.raises(ValueError):snapshot(a)
