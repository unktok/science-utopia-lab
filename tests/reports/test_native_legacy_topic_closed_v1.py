"""Actual real-control retention, distinct from SCRIPTED capability proofs."""
import json
from pathlib import Path
from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]


def test_actual_paired_control_readout_is_bound_without_invention_or_optimization_claim():
    r=checked(json.loads((ROOT/'research/results/native-legacy-topic-pilot-closed-v1.json').read_text()))
    for name,sha in r['retained_files'].items(): assert file_sha256(ROOT/name)==sha
    assert r['original_writer_exit_code']==r['original_closure_exit_code']==0
    assert r['terminal']['status']=='closed' and r['terminal']['completed_jobs']==2
    assert r['two_original_source_audits_identical'] and r['two_original_costs_identical']
    assert r['same_cold_initial_physical_society'] and r['paired_readout_exit_codes']==[0,0]
    core,broad=r['rows']
    assert [w['collected_activity_cost'] for w in r['rows']]==[200.,200.]
    assert [w['scores']['throughput'] for w in r['rows']]==[-20.,-36.]
    assert [w['outside_core_assignments'] for w in r['rows']]==[0,18]
    assert core['original_duration_counts']=={'2':10}
    assert broad['original_duration_counts']=={'1':16,'2':2}
    assert r['content_overlap_counts']=={'common':0,'left_only':20,'right_only':36}
    assert r['exact_left_minus_right_utility']=={'numerator':-40,'denominator':3}
    assert r['scientist_completed_responses']==306 and r['designer_generation_POSTs']==0
    assert r['common_content_observer']['physical_requests']==168
    assert r['scientist_provider_usage']['total_tokens']['recorded_sum']==458048
    assert all(row['costs_by_category']=={'annual_research_cost':50.,'production_submission_cost':0.,
        'resubmission_cost':0.,'funding_application_cost':0.} for annual in
        r['original_resource_instrument_categories'].values() for row in annual)
    assert not r['automatic_invention'] and not r['new_optimization_study'] and not r['held_out_evaluation']
    assert not r['historical_losses_or_selection_changed'] and not r['publication_ready']
