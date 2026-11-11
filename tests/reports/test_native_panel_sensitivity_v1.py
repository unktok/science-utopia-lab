"""Exact finite subset calculations, not counterfactual native evaluations."""
import math

import pytest

from scripts.reports.native_panel_sensitivity_v1 import fixed_world,panel_readouts


def test_exact_uniform_subset_expectation_retains_full_panel_mean_and_variance():
    r=panel_readouts([1,3,5]);assert r['original_mean']==3
    one,two,three=r['subsets']
    assert one['subsets']==3 and one['minimum']==1 and one['maximum']==5
    assert one['uniform_variance']==pytest.approx(8/3)
    assert two['minimum']==2 and two['maximum']==4 and two['uniform_variance']==pytest.approx(2/3)
    assert three['minimum']==three['maximum']==3 and three['uniform_variance']==0


@pytest.mark.parametrize('bad', [[True],[None],['4'],[math.nan],[math.inf],(1,2),[1]*17])
def test_missing_invalid_or_unbounded_panels_are_not_coerced_or_imputed(bad):
    with pytest.raises(ValueError):panel_readouts(bad)


def test_empty_reviews_do_not_fabricate_a_quality_readout():
    assert panel_readouts([])=={'reviews':0,'original_mean':None,'subsets':[]}


def test_readout_changes_neither_acceptance_nor_actual_review_cost():
    def decision(outcome,scores,year):
        return {'decision':outcome,'reviews':[{'overall_score':v} for v in scores],'year':year}
    papers=[{'id':'SCRIPTED-a','review_history':[decision('reject',[1,1,1],1),decision('accept',[1,3,5],2)]},
        {'id':'SCRIPTED-b','review_history':[decision('accept',[],1)]}]
    r=fixed_world(papers)
    assert r['accepted_decisions']==2 and r['unreviewed_accepted_decisions']==1
    assert r['actual_review_records']==6 and r['original_Q']==3
    assert r['conditional_one_review_readout_Q_range']==[1,5]
    assert r['conditional_E_readout_range_same_actual_R']==[-2,2]
    assert papers[0]['review_history'][0]['decision']=='reject'
