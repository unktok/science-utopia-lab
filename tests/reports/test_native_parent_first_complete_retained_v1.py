"""Partial live record retention, not a substitute for the final native audit."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked


ROOT = Path(__file__).resolve().parents[2]


def test_first_complete_own_record_is_a_tie_not_gain_or_closed_study():
    r = checked(json.loads((ROOT / 'research/results/native-parent-presentation-first-complete-own-v1.json').read_text()))
    assert r['partial_live_study_not_final_audit'] and r['worker_submitted'] and r['status'] == 'complete'
    assert r['arm'] == 'content-utility-literal' and r['generation'] == 0
    assert len(r['reference_scores']) == 8
    best = min(x['scores']['content-utility'] for x in r['reference_scores'])
    assert best == r['assigned_loss'] == r['best_fresh_reference_assigned_loss']
    assert r['own_improvement_over_best_fresh_reference'] == 0
    assert r['cross_scores']['throughput'] == -18 and r['accepted_decisions'] == 18
    assert r['changed_paths_from_that_reference'] == ['/mechanisms/6/parameters/code_artifact/source']
    assert r['earlier_T_control_observation']['status'] == 'failed'
    assert r['earlier_T_control_observation']['loss'] is None
    assert not r['source_repaired'] and not r['failed_slot_refilled']
    assert not r['scientific_gain_demonstrated'] and not r['publication_ready']


def test_failed_readonly_metadata_observer_never_attests_effective_35b_context():
    r = checked(json.loads((ROOT / 'research/results/native-parent-backend-context-metadata-v1.json').read_text()))
    assert r['observed_exit_code'] == 1 and r['ended']['status'] == 'stopped'
    assert r['ended']['error_type'] == 'TimeoutError' and r['ended']['polls'] == 1
    assert r['model_alias_declares_num_ctx'] == r['started']['alias_num_ctx'] == 65536
    assert not r['effective_35B_context_observed'] and not r['inference_that_earlier_inputs_were_truncated']
    assert r['new_model_calls'] == 0 and not r['backend_reconfigured'] and not r['original_science_restarted']
