"""Actual initial control evidence is not a free-design or scientific claim."""
import json
from pathlib import Path

from scripts.check_repository_docs import check
from utopia.optimization.native_numeric_designer import checked

ROOT=Path(__file__).resolve().parents[2]


def test_both_actual_initial_calibrations_keep_source_complete_envelopes_and_scoped_capacity():
    path=ROOT/'research/results/native-parent-presentation-initial-readiness-verification-v1.json'
    proof=checked(json.loads(path.read_text()))
    launch=checked(json.loads((ROOT/'research/results/native-parent-presentation-launch-verification-v1.json').read_text()))
    assert proof['scientific_source_commit']==launch['scientific_source_commit']
    assert proof['plan_content_sha256']==launch['plan_content_sha256']
    assert proof['plan_file_sha256']==launch['plan_file_sha256']
    assert proof['actual_progress_at_observation']['stage']=='references'
    assert set(proof['presentations'])=={'control','literal'}
    for mode,maximum in [('control',23156),('literal',27727)]:
        row=proof['presentations'][mode]
        assert row['cases']==row['known_complete_HTTP_envelopes']==row['reported_prompt_counts']==28
        assert row['all_controls_passed'] and row['cold_public_worker_replay_matches']
        assert row['maximum_reported_prompt_eval_count']==maximum
        assert row['reserved_output_tokens']==8192 and row['context_tokens']==40960
        assert row['maximum_observed_prompt_plus_reserved_fits']
    assert proof['cold_backend_is_frozen_metadata_not_fresh_service_attestation']
    assert not any(proof[k] for k in ('new_model_calls','new_code_executions','new_native_worlds',
        'scientific_gain_demonstrated','independent_optimizer_replication','held_out_evaluation','publication_ready'))
    assert not launch['two_initial_actual_readiness_passes_claimed']


def test_new_comparator_notes_are_portable_and_do_not_claim_a_dispatched_numeric_study():
    result=check(ROOT,documents=(
        'research/publication/native-parameter-baseline-preparation-v1.md',
        'research/logbook/2026-11-14-native-parameter-preparation.md'),manifest=None)
    assert result['status']=='passed',result['errors']
