from copy import deepcopy
import pytest
from scripts.reports.native_control_summary import summarize,plot
from utopia.system.design_patch import digest


def fixture():
    rows=[{'name':n,'slot':i,'status':'complete','cross_scores':{k:0. for k in ['throughput','efficiency','selective']}}
        for i,n in enumerate(['legacy','open-seed','open-rank-rate','open-accept-all','open-reject-all',
            'open-score-3','open-score-4','open-no-review-accept-all'])]
    d={'schema':'scienceutopia.native-benchmark-controls.v2.audit','source_commit':'a'*40,'plan_sha256':'b'*64,
        'rows':rows,'proofs':{r['name']:{'measurement':{'metrics':{}},'response_proof':{
            'researcher_responses':1,'wire_requests':1},'code_proof':{'recorded_executions':0}} for r in rows},
        'best':{k:{'loss':0.,'all_tied_names':[r['name'] for r in rows]} for k in ['throughput','efficiency','selective']},
        'writer':{'started':{'started_utc':'2026-11-07T00:00:00+00:00'},
            'ended':{'ended_utc':'2026-11-07T00:00:10+00:00'}}}
    d['content_sha256']=digest(d);return d


def test_projection_is_exact_and_hash_bound_without_invented_scientific_outcomes(tmp_path):
    d=fixture();before=deepcopy(d);s=summarize(d)
    assert d==before and s['completed']==8 and s['wall_seconds']==10
    assert s['best']==d['best'] and s['costs']['scientist_responses']['known_sum']==8
    plot(s,tmp_path/'figures')
    assert (tmp_path/'figures'/'manifest.json').exists()
    with pytest.raises(ValueError,match='fresh'):plot(s,tmp_path/'figures')
    d['rows'][0]['cross_scores']['throughput']=-999.
    with pytest.raises(ValueError,match='identity|content'):summarize(d)


def test_nulls_and_unknown_costs_remain_missing_not_numerical_penalties():
    d=fixture();d.pop('content_sha256')
    d['rows'][0].update(status='failed',cross_scores={k:None for k in ['throughput','efficiency','selective']})
    d['proofs']['legacy']={};d['content_sha256']=digest(d)
    s=summarize(d)
    assert s['rows'][0]['metrics'] is None and s['rows'][0]['cross_scores']['throughput'] is None
    assert s['costs']['scientist_responses']=={'known_sum':7,'unknown_rows':['legacy']}
