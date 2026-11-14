"""Retained full integration evidence is not another experiment or model run."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def record():
    return checked(json.loads((ROOT/'research/results/native-open-workflow-staged-native-software-v1.json').read_text()))


def test_real_bounded_native_handoff_remains_explicitly_scripted():
    r = record()
    assert r['exit_code']==0 and r['actual_test_session']==21902
    assert r['native_software_worlds']==10 and r['annual_checkpoints']==40
    assert r['real_component_probes']==48 and r['real_component_probe_results']=={'raised':24,'returned':24}
    assert r['actual_model_calls']==0 and not r['actual_scientific_gain_claimed']
    assert not r['real_backend_calibration_passed'] and not r['free_model_construction_or_optimization_run_started']
    assert not r['measured_real_backend_token_capacity'] and not r['publication_ready']


def test_complete_role_counts_and_deliberate_nulls_are_not_hidden():
    r = record(); d,f = (r['runs'][name] for name in ('development','fixed'))
    assert d['scripted_auxiliary_intents_by_role']=={
        'editor-readiness':200,'load-designer':13,'load-scientist':7,'staged-proposal':41}
    assert f['scripted_auxiliary_intents_by_role']=={'load-scientist':3}
    assert d['scripted_scientist_responses']+f['scripted_scientist_responses']==1000
    assert d['scripted_critic_requests']+f['scripted_critic_requests']==78
    assert d['verification']['known_invalid_slots_preserved']==1
    assert f['verification']['known_nulls_preserved']==1
    assert f['verification']['fixed_selection_unchanged']
    assert d['verification']['active_authored_scientist_input_change']['full_scientist_inputs_changed']
    assert d['verification']['maximum_actual_wire_utf8_bytes']==150126


def test_original_failed_attempts_and_matching_double_exports_stay_distinct():
    r = record()
    assert set(r['preserved_failed_software_attempts'])=={'a1','a2'}
    assert all(v['original_outputs_preserved'] for v in r['preserved_failed_software_attempts'].values())
    for run in r['runs'].values():
        assert len(run['audit_files'])==len(run['cost_files'])==2
        assert len(set(run['audit_files'].values()))==len(set(run['cost_files'].values()))==1
        assert run['cost_content_sha256']==run['verification']['matching_cost_content_sha256']


def prepared():
    return checked(json.loads((ROOT/'research/results/native-open-staged-institution-prepared-v1.json').read_text()))


def test_real_plan_preparation_is_not_relabelled_as_model_dispatch():
    r=prepared()
    assert r['prepare_exit_code']==0 and len(r['source_commit'])==40
    assert r['designer_mode']=='open-institutions-staged-tests-v1'
    assert r['budget']['candidate_slots']==6 and r['budget']['native_worlds_upper_bound']==8
    assert not r['real_writer_started'] and r['actual_model_POSTs']==0
    assert not r['actual_backend_calibration_passed'] and not r['publication_ready']


def test_failed_resource_checks_preserve_thresholds_and_other_projects():
    r=prepared();rows=r['resource_observations']
    assert len(rows)==4 and all(not v['ready'] and not v['ended_ready_record_exists'] for v in rows)
    assert all(v['declared_cpu_ceiling']==250 for v in rows)
    assert all(v['declared_minimum_free_plus_inactive_bytes']==38*1024**3 for v in rows)
    assert not r['resource_thresholds_changed'] and not r['other_projects_stopped_or_modified']
    assert not r['previous_scientific_records_changed']
