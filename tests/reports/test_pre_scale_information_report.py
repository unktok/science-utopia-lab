"""Synthetic projection cases, not actual M observations."""
from copy import deepcopy

import pytest

from scripts.reports.pre_scale_information_v1 import summarize,SEEDS,CONDITIONS,METRICS
from utopia.system.design_patch import digest


def fixture():
    rows=[]
    for seed in SEEDS:
        for i,c in enumerate(CONDITIONS):
            a,q,r=2+i,10+i,9
            values={'A':a,'Q':q,'R':r,'active':5,'resources':100,'deliveries':i*5}
            measurement={'metrics':{METRICS[k]:{'status':'measured','value':v} for k,v in values.items()}}
            rows.append({'id':c+'-s'+str(seed),'condition':c,'seed':seed,
                'scores':{'throughput':-a,'efficiency':-q+.5*r,'selective':4*a-q+.1*r},
                'measurement':measurement,'actual_inputs':{'first_direction_input_year':None if i==0 else 4,
                    'completed_dossier_inputs':[]},'physical_proof':{'status':'complete','seed':seed,'years':4,
                    'annual_checkpoints':[{'interval_llm_elapsed_seconds':1.} for _ in range(4)],
                    'response_proof':{'researcher_responses':4,'wire_requests':4},
                    'code_proof':{'recorded_executions':4}}})
    data={'schema':'scienceutopia.pre-scale-information-audit.v1','source_commit':'a'*40,
        'plan_sha256':'b'*64,'rows':rows};data['content_sha256']=digest(data)
    return data


def rehash(value):
    value.pop('content_sha256');value['content_sha256']=digest(value);return value


def test_every_seed_difference_and_measured_consumer_year_is_retained():
    data=fixture();original=deepcopy(data);r=summarize(data)
    assert data==original and len(r['rows'])==12 and len(r['paired_differences'])==9
    assert {x['first_direction_input_year'] for x in r['rows']}=={None,4}
    assert all(x['loss_difference_from_disconnected']['throughput']<0 for x in r['paired_differences'])
    assert all(x['cost_components']['scientist_call_seconds']==4. for x in r['rows'])
    assert r['new_model_calls']==0 and not r['scientific_goal_complete']


@pytest.mark.parametrize('problem',['missing','duplicate','bad-score','missing-metric','bool-metric','negative-time'])
def test_missing_or_inconsistent_raw_values_cannot_become_complete_results(problem):
    data=fixture()
    if problem=='missing':data['rows'].pop()
    if problem=='duplicate':data['rows'].append(deepcopy(data['rows'][0]))
    if problem=='bad-score':data['rows'][0]['scores']['efficiency']=100
    if problem=='missing-metric':data['rows'][0]['measurement']['metrics'][METRICS['Q']]['status']='unavailable'
    if problem=='bool-metric':data['rows'][0]['measurement']['metrics'][METRICS['Q']]['value']=True
    if problem=='negative-time':data['rows'][0]['physical_proof']['annual_checkpoints'][0]['interval_llm_elapsed_seconds']=-1
    with pytest.raises(ValueError):summarize(rehash(data))
