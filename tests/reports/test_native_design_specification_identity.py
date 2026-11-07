"""SCRIPTED grouping QA only; no real study audit, model or world execution."""
from copy import deepcopy

import pytest

from scripts.reports import native_design_benchmark as report
from tests.reports.test_native_design_benchmark_report import fixture,hashed


ASSIGNMENTS={'T':{'objective':'throughput'},'C':{'objective':'selective'}}


def row(identity,arm,fingerprint,status='complete',loss=-7.,physical=True):
    return {'row_id':identity,'run':'SCRIPTED-run','arm':arm,'system_fingerprint':fingerprint,
        'status':status,'own_loss':loss,'physical_forward_completed':physical}


def test_same_specification_is_grouped_without_hiding_failed_or_missing_loss_rows():
    rows=[row('unsubmitted','T','placeholder-seed','generation-failure',None,False),
        row('t','T','A'),row('c-failed','C','A','technical-failure',None,False),
        row('c-unavailable','C','B','loss-unavailable',None,True),
        row('t-b','T','B'),row('failed-only','T','C','technical-failure',None,False)]
    before=deepcopy(rows);s=report.specification_identity_summary(rows,ASSIGNMENTS)
    assert rows==before and s==report.specification_identity_summary(rows,ASSIGNMENTS)
    assert s['candidate_slots']==6 and s['submitted_candidate_slots']==5
    assert s['generation_failure_slots_without_candidate']==1
    assert s['unsubmitted_row_ids']==['unsubmitted']
    assert s['distinct_submitted_system_fingerprints']==3
    assert s['repeated_known_fingerprint_slots']==2
    assert s['identity_inventory_complete'] and s['unknown_fingerprint_slots']==0
    assert s['distinct_systems_with_physical_forward_proof']==2
    a,b,c=s['groups']
    assert a['row_ids']==['t','c-failed'] and a['objectives']==['selective','throughput']
    assert a['status_counts']=={'complete':1,'technical-failure':1}
    assert a['rows_with_physical_forward_proof']==1 and a['assigned_loss_available_slots']==1
    assert b['rows_with_physical_forward_proof']==2 and b['assigned_loss_available_slots']==1
    assert c['rows_with_physical_forward_proof']==0
    assert s['counts_are_not_inventions_or_independent_samples']
    assert not s['scores_costs_and_selection_deduplicated']


@pytest.mark.parametrize('rows',[[],[row('u','T','seed','generation-failure',None,False)]])
def test_no_submitted_candidate_does_not_fabricate_an_initial_policy(rows):
    s=report.specification_identity_summary(rows,ASSIGNMENTS)
    assert s['submitted_candidate_slots']==0 and s['groups']==[]
    assert s['distinct_submitted_system_fingerprints']==0
    assert s['distinct_systems_with_physical_forward_proof']==0


@pytest.mark.parametrize('mutate',[
    lambda r:r.update(system_fingerprint=None),
    lambda r:r.update(system_fingerprint=''),
    lambda r:r.update(status=[]),
    lambda r:r.update(physical_forward_completed='unknown'),
    lambda r:r.update(arm='undeclared'),
    lambda r:r.update(status='generation-failure'),
    lambda r:r.update(own_loss=True),
])
def test_malformed_identity_or_contradictory_forward_is_not_silently_counted(mutate):
    r=row('a','T','A');mutate(r)
    with pytest.raises(ValueError):report.specification_identity_summary([r],ASSIGNMENTS)


def test_duplicate_row_ids_are_not_extra_proposals():
    r=row('a','T','A')
    with pytest.raises(ValueError,match='unique'):
        report.specification_identity_summary([r,deepcopy(r)],ASSIGNMENTS)


def test_closed_fixture_adds_identity_inventory_without_deduplicating_any_evidence():
    plan,audit=fixture()
    for run in audit['runs'].values():
        for arm in run.values():
            arm['observations'][2]['status']='generation-failure'
            # A synthetic diagnostic placeholder must not become a candidate.
            arm['observations'][2]['system_fingerprint']='SCRIPTED-unused-initial'
    hashed(audit);before=deepcopy(audit)
    result=report.project(plan,audit,expected_source=plan['source_commit'])
    assert audit==before and len(result['all_candidate_rows'])==120
    identity=result['development_specification_identity']
    assert identity['generation_failure_slots_without_candidate']==30
    assert identity['submitted_candidate_slots']==90
    assert identity['distinct_submitted_system_fingerprints']==1
    assert identity['repeated_known_fingerprint_slots']==89
    assert identity['groups'][0]['slot_count']==90
    assert len(result['evaluation'])==6 and result['logical_evaluation_labels']==19
    assert result['selection']['selected']==audit['selection']['selected']
    assert result['search_arms']['run-00']['throughput:random']['native_costs']=={
        k:audit['runs']['run-00']['throughput:random'][k] for k in
        ['physical_native_worlds','physical_world_directory_count','physical_researcher_responses',
         'physical_wire_requests','recorded_code_executions_including_partial',
         'completed_researcher_model_call_seconds']}


def test_post_generation_draw_failure_has_unknown_identity_not_a_phantom_duplicate():
    rows=[row('known','T','A'),
        row('no-spec-1','T',None,'technical-failure',None,False),
        row('no-spec-2','C',None,'technical-failure',None,False)]
    s=report.specification_identity_summary(rows,ASSIGNMENTS)
    assert s['submitted_candidate_slots']==3 and s['known_fingerprint_slots']==1
    assert s['unknown_fingerprint_slots']==2 and not s['identity_inventory_complete']
    assert s['unknown_fingerprint_row_ids']==['no-spec-1','no-spec-2']
    assert s['distinct_submitted_system_fingerprints']==1
    assert s['repeated_known_fingerprint_slots']==0
    assert s['groups'][0]['row_ids']==['known']


def test_closed_projection_retains_legitimate_uninstantiated_draw_failure():
    plan,audit=fixture()
    audit['runs']['run-00']['throughput:parameters']['observations'][2]['system_fingerprint']=None
    hashed(audit)
    result=report.project(plan,audit,expected_source=plan['source_commit'])
    assert len(result['all_candidate_rows'])==120
    identity=result['development_specification_identity']
    assert identity['known_fingerprint_slots']==119 and identity['unknown_fingerprint_slots']==1
    assert identity['unknown_fingerprint_row_ids']==['run-00:throughput:parameters:g2']
    assert identity['repeated_known_fingerprint_slots']==118
    assert result['all_candidate_rows'][2]['own_loss'] is None
