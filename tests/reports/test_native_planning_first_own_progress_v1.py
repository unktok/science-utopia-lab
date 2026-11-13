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


def test_first_pair_keeps_both_assigned_ties_and_different_parents():
    r=checked(json.loads((ROOT/'research/results/native-planning-first-pair-progress-v1.json').read_text()))
    assert r['scientific_source_commit']=='8cd61578b94d86dd0cf2ff3b0e581d9a2698fc0f'
    t,u=r['own']
    assert [w['objective'] for w in r['own']]==['throughput','content-utility']
    assert t['scores']=={'throughput':-18.,'content-utility':-10.333333333333332}
    assert u['scores']=={'throughput':-18.,'content-utility':-13.333333333333332}
    assert t['parent_matching_reference_ids']==['reference-advice-reserve21-all']
    assert u['parent_matching_reference_ids']==['reference-assignment-reserve21-no-review-all']
    for w in r['own']:
        assert w['status']=='complete' and w['generation']==0 and w['world_seed']==61001
        best=min(v['scores'][w['objective']] for v in r['fresh_reference_cross_scores'])
        assert w['assigned_loss']==best==w['parent_scores'][w['objective']]
        assert w['assigned_loss_minus_best_fresh_reference']==0
        assert not w['connections_changed'] and not w['schedules_changed']
    assert t['scores']['content-utility']-t['parent_scores']['content-utility']==1.
    assert len(r['fresh_reference_cross_scores'])==8
    assert r['next_stage_at_observation']['active']=='content-utility:g1'
    assert not any(r[k] for k in ('first_editing_parents_identical','own_edits_improved_assigned_parent_loss',
        'study_normal_terminal_present','final_study_audit_completed','final_selection_made',
        'new_inference_by_snapshot','loss_or_candidate_changed_by_snapshot',
        'beneficial_invention_or_causal_effect_claimed','publication_ready'))


def test_reference_minima_overlap_despite_different_objective_conditioned_parents():
    r=checked(json.loads((ROOT/'research/results/native-planning-first-pair-progress-v1.json').read_text()))
    refs=r['fresh_reference_cross_scores']
    minima={o:{v['identity'] for v in refs if v['scores'][o]==min(w['scores'][o] for w in refs)}
            for o in ('throughput','content-utility')}
    common='reference-assignment-reserve21-no-review-all'
    assert len(minima['throughput'])==4 and minima['content-utility']=={common}
    assert minima['throughput'] & minima['content-utility']=={common}
    t,u=r['own']
    assert t['parent_matching_reference_ids'][0] in minima['throughput']
    assert u['parent_matching_reference_ids'][0] in minima['content-utility']
    assert t['parent_matching_reference_ids']!=u['parent_matching_reference_ids']
