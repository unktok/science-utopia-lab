"""Synthetic tensor-trace cases, not actual M outcomes or new simulations."""
from copy import deepcopy

import pytest
import torch

from scripts.diagnose_pre_scale_selector_v1 import selector_statistics,main
from utopia.system.native_tensor_examples import addressed_selection_program
from utopia.system.tensor_program import execute_tensor_program
from utopia.system.design_patch import digest


def fixture(*,empty=False):
    program=addressed_selection_program();state={'accepted_so_far':0.};frames=[]
    for year in range(1,5):
        raw=[] if empty else [[3.,3.],[11./3.,3.]]
        inputs={'features':torch.tensor(raw,dtype=torch.float64).reshape(-1,2)}
        out,after=execute_tensor_program(program,inputs,
            state={k:torch.tensor(v,dtype=torch.float64) for k,v in state.items()},hard=True)
        trace={'program_sha256':digest(program),'mode':'hard','inputs':{'features':raw},
            'state_before':deepcopy(state),'state_after':{k:v.detach().tolist() for k,v in after.items()},
            'outputs':{k:v.detach().tolist() for k,v in out.items()},'records':[{'synthetic':i} for i in range(len(raw))]}
        frames.append({'year':year,'trace':trace});state=trace['state_after']
    return program,frames


def test_strict_threshold_explanation_requires_actual_replayed_features_and_outputs():
    p,f=fixture();r=selector_statistics(p,f)
    assert r['feature_rows']==8 and r['score_range']==[3.,11./3.]
    assert r['selected_effective_threshold_range']==[4.,4.]
    assert r['every_observed_record_strictly_below_threshold'] and r['all_observed_accept_outputs_zero']
    assert r['recorded_accept_output_sum']==0. and r['recorded_review_count_sum']==24.


def test_empty_years_are_not_evidence_of_threshold_rejection():
    p,f=fixture(empty=True);r=selector_statistics(p,f)
    assert r['empty_record_set'] and r['score_range'] is None
    assert not r['every_observed_record_strictly_below_threshold'] and not r['all_observed_accept_outputs_zero']


@pytest.mark.parametrize('target',['outputs','state_after','state_before','year','program'])
def test_changed_trace_cannot_be_explained_as_original_behavior(target):
    p,f=fixture()
    if target=='outputs':f[0]['trace']['outputs']['accept'][0]=1.
    if target=='state_after':f[0]['trace']['state_after']['accepted_so_far']=1.
    if target=='state_before':f[1]['trace']['state_before']['accepted_so_far']=1.
    if target=='year':f[1]['year']=3
    if target=='program':f[0]['trace']['program_sha256']='0'*64
    with pytest.raises(ValueError):selector_statistics(p,f)


def test_running_study_is_rejected_before_any_diagnostic_worker(tmp_path,monkeypatch):
    monkeypatch.setattr('sys.argv',['diagnostic','--run',str(tmp_path),'--audit',str(tmp_path/'audit.json'),
        '--output',str(tmp_path/'result.json'),'--frozen-source',str(tmp_path)])
    monkeypatch.setattr('subprocess.run',lambda *a,**kw:pytest.fail('must not run a partial-study diagnostic'))
    with pytest.raises(ValueError,match='closed study/full audit'):main()
