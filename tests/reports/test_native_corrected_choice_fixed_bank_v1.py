"""SCRIPTED frozen policies and labels; no unused-seed validation or execution."""
from copy import deepcopy
import pytest

from scripts import native_corrected_choice_fixed_bank_v1 as bank
from scripts import native_priority_fixed_bank_v1 as old_bank
from tests.reports.test_native_corrected_choice_readout_v1 import fixture,seal


def inputs(*,null=False):
    p,a,slots,refs=fixture(delta=1.,null_free=null)
    for e in slots:
        for key in ('suggestion','observation'):
            if e[key] is not None:e[key]['candidate']['initial_state']={'seed':61001}
        e['parent_system']['initial_state']={'seed':61001}
    for r in refs.values():r['candidate']['initial_state']={'seed':61001}
    for w in a['worlds']:w['system']['initial_state']={'seed':61001}
    for field in ('selected','own_only_selected'):
        for method in a['selection'][field].values():
            for history in method.values():
                for row in history.values():
                    if row['system'] is not None:row['system']['initial_state']={'seed':61001}
    p['initial_system']=deepcopy(refs[p['reference_order'][0]]['candidate']);p=seal(p)
    a['plan_sha256']=p['content_sha256'];a['selection']=seal(a['selection']);a=seal(a)
    return p,a,slots,refs


def test_all15_labels_keep_returned_references_distinct_from_own_programs():
    args=inputs();result=bank.freeze_bank(*args);draft=bank.planned_jobs(result,[83003,83011])
    assert len(result['entries'])==15
    primary=[e for e in result['entries'] if e.get('selection_scope')=='best-known']
    own=[e for e in result['entries'] if e.get('selection_scope')=='own-only']
    assert len(primary)==len(own)==6 and all(e['selected_origin']=='reference' for e in primary)
    assert all(e['selected_origin']=='own' for e in own)
    assert draft['planned_physical_worlds']==2 and all(len(j['labels'])==15 for j in draft['jobs'])
    assert not draft['dispatchable'] and not draft['seed_usage_validated']
    with pytest.raises(ValueError,match='legacy own-only'):old_bank.freeze_bank(*args)


def test_absent_own_label_is_not_a_returned_reference_or_an_evaluation_job():
    result=bank.freeze_bank(*inputs(null=True));draft=bank.planned_jobs(result,[83003])
    assert len(result['entries'])==15 and len(result['missing_own_selections'])==1
    assert len(draft['jobs'][0]['labels'])==14 and result['missing_own_selections']==draft['missing_own_selections']


@pytest.mark.parametrize('problem',['drop','order','origin','own-reference','claim','missing-primary','reference-own-cell'])
def test_corrupt_or_promoted_endpoint_bank_cannot_make_a_job_draft(problem):
    result=bank.freeze_bank(*inputs())
    if problem=='drop':result['entries'].pop()
    elif problem=='order':result['entries'][-1],result['entries'][-2]=result['entries'][-2],result['entries'][-1]
    elif problem=='origin':result['entries'][-1]['selected_origin']='reference'
    elif problem=='own-reference':result['entries'][3]['role']='own-only-selection'
    elif problem=='claim':result['seed_usage_validated']=True
    elif problem=='reference-own-cell':result['entries'][3]['selected_cell_id']='SCRIPTED-mislabelled-own'
    else:
        result['entries'][3].update(system=None,selection_available=False,selected_origin=None,selected_id=None,selected_cell_id=None)
    with pytest.raises(ValueError):bank.planned_jobs(seal(result),[83003])


@pytest.mark.parametrize('seeds',[[],[61001],[True],[83003,83003],[[]],[-1]])
def test_seed_drafts_do_not_claim_unusedness_or_silently_replace_conditions(seeds):
    with pytest.raises(ValueError):bank.planned_jobs(bank.freeze_bank(*inputs()),seeds)
