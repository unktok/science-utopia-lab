"""Conditional calendar arithmetic and actual retained pilot, no world execution."""
import json
from pathlib import Path
import pytest
from utopia.utils.data_utils import file_sha256

from scripts.reports import native_topic_calendar_envelope_v1 as reader
from utopia.system.native_catalog_planning import catalog_contract
from utopia.system.design_patch import clone
from utopia.system.runtime import GraphRuntimeError

ROOT=Path(__file__).resolve().parents[2]


def test_original_retained_founder_catalog_relaxation_matches_observed_capacity():
    report=reader.checked(json.loads((ROOT/'research/data/native-legacy-topic-pilot-v1/report.json').read_text()))
    plan={'world':{'years':4,'world_conditions':{'papers_per_project':2}},'content_sha256':'SCRIPTED-plan-not-a-new-world'}
    result=reader.analyze(report,plan,catalog_contract())
    assert [r['conditional_new_paper_slots'] for r in result['rows']]==[20,36]
    assert [r['conditional_completed_project_slots'] for r in result['rows']]==[10,18]
    assert all(r['observed_acceptance_equals_conditional_paper_slots'] for r in result['rows'])
    assert [a['minimum_original_duration'] for a in result['rows'][1]['authors']]==[1,1,2,1,1]
    assert not result['full_design_domain_optimality_proved']
    assert result['new_model_calls']==result['new_native_worlds']==0


@pytest.mark.parametrize('years,papers',[(True,2),(0,2),(4,False),(4,-1),(2.5,2)])
def test_invalid_calendar_never_coerces_to_a_scientific_bound(years,papers):
    with pytest.raises(ValueError,match='positive integer'):
        reader.capacity([],catalog_contract(),years=years,papers_per_project=papers,related=True)


def test_actual_catalog_identity_and_duplicate_authors_are_not_silently_repaired():
    catalog=catalog_contract(); actor={'id':'SCRIPTED','expertise':[catalog['directions'][0]['topic']]}
    with pytest.raises(ValueError,match='unique original author'):
        reader.capacity([actor,actor],catalog,years=4,papers_per_project=2,related=False)
    changed=clone(catalog); changed['directions'][0]['years']=0
    with pytest.raises(GraphRuntimeError,match='catalog identity'):
        reader.capacity([actor],changed,years=4,papers_per_project=2,related=True)


def test_floor_is_optimistic_capacity_not_a_claim_of_feasible_funding_or_acceptance():
    catalog=catalog_contract()
    topic=next(d['topic'] for d in catalog['directions'] if d['years']==2)
    result=reader.capacity([{'id':'SCRIPTED','expertise':[topic]}],catalog,
                           years=3,papers_per_project=2,related=False)
    assert result['conditional_completed_project_slots']==1
    assert result['conditional_new_paper_slots']==2


def test_retained_paired_light_exports_are_not_new_native_or_global_optimality_evidence():
    receipt=json.loads((ROOT/'research/results/native-topic-calendar-envelope-retention-v1.json').read_text())
    for name,expected in receipt['retained_files_sha256'].items(): assert file_sha256(ROOT/name)==expected
    report=reader.checked(json.loads((ROOT/'research/data/native-topic-calendar-envelope-v1/report.json').read_text()))
    assert receipt['original_export_exit_codes']==[0,0] and receipt['all_three_export_files_identical']
    assert report['analysis_source_commit']==receipt['analysis_source_commit']
    assert len(report['original_primitive_files_sha256'])==8
    assert [r['observed_unique_accepted_papers'] for r in report['rows']]==[20,36]
    assert not report['full_design_domain_optimality_proved']
    assert not report['original_cold_audits_reexecuted']
    assert not receipt['active_scientific_conditions_changed'] and not receipt['publication_ready']
