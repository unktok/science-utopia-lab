"""Prospective preference semantics, not scientific optimization evidence."""
from pathlib import Path

import pytest

from utopia.optimization.loss import load_loss_spec,evaluate_loss

PATH=Path(__file__).resolve().parents[2]/'research/objectives/losses/native-common-content-utility-v1.json'


@pytest.mark.parametrize('utility',[-1.,0.,2.333333333333333])
def test_exact_predeclared_common_utility_is_the_only_loss_term(utility):
    spec=load_loss_spec(PATH)
    result=evaluate_loss(spec,[{'run_id':'SCRIPTED-contract-check','metrics':{
        'native.common_content_utility_sum':{'status':'measured','value':utility}}}])
    assert result['status']=='complete' and result['loss']==-utility
    assert len(spec['per_run']['terms'])==1 and spec['per_run']['intercept']==0
    assert spec['across_seeds']['dispersion_weight']==0


def test_unavailable_common_measurement_never_acquires_zero_or_a_penalty():
    result=evaluate_loss(load_loss_spec(PATH),[{'run_id':'SCRIPTED-missing','metrics':{
        'native.common_content_utility_sum':{'status':'unavailable','value':None}}}])
    assert result['status']=='insufficient_valid_runs' and result['loss'] is None
