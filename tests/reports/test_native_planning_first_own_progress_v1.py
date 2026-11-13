"""A partial actual observation must not become a closed study or gain claim."""
import json
from pathlib import Path

from scripts.check_repository_docs import check
from utopia.optimization.native_numeric_designer import checked

ROOT=Path(__file__).resolve().parents[2]


def receipt():
    return checked(json.loads((ROOT/'research/results/native-planning-first-own-progress-v1.json').read_text()))


def test_first_actual_observation_ties_fresh_strong_controls():
    r=receipt(); own=r['first_own']; refs=r['fresh_reference_throughput']
    assert r['scientific_source_commit']=='8cd61578b94d86dd0cf2ff3b0e581d9a2698fc0f'
    assert own['objective']=='throughput' and own['generation']==0 and own['status']=='complete'
    assert own['valid_runs']==1 and own['world_seed']==61001
    assert own['loss']==-18. and own['accepted_decision_records']==18
    assert [v['loss'] for v in refs]==[-12.,-18.,-18.,-12.,-12.,-18.,-18.,0.]
    assert r['first_own_minus_best_reference_loss']==own['loss']-min(v['loss'] for v in refs)==0


def test_source_edit_is_not_structural_change_or_final_scientific_closure():
    r=receipt(); own=r['first_own']
    assert own['literal_changed_paths_from_parent']==['/mechanisms/7/parameters/code_artifact/source']
    assert own['parent_system_sha256']!=own['candidate_system_sha256']
    assert not own['connections_changed'] and not own['schedules_changed']
    assert r['next_stage_at_observation']['active']=='content-utility:g0'
    assert r['next_stage_at_observation']['stage']=='readiness'
    assert not any(r[k] for k in ('study_normal_terminal_present','final_study_audit_completed',
        'final_selection_made','new_inference_by_snapshot','loss_or_candidate_changed_by_snapshot',
        'beneficial_invention_or_causal_effect_claimed','publication_ready'))


def test_partial_observation_links_are_portable():
    result=check(ROOT,documents=('research/INDEX.md','research/STATUS.md',
        'research/components/native-planning-objective-loop-v1.md',
        'research/logbook/2026-11-13-planning-first-completed-design.md'),manifest=None)
    assert result['status']=='passed',result['errors']
