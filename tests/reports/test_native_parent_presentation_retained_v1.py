"""Retained QA and real-launch scopes stay distinct; no current live claim."""
import hashlib
import json
from pathlib import Path
import subprocess

from scripts.check_repository_docs import check
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def receipt():
    return checked(json.loads((ROOT/'research/results/native-parent-presentation-launch-verification-v1.json').read_text()))


def test_successful_exact_path_QA_does_not_promote_scripted_calls_to_scientific_results():
    r = receipt()
    assert r['scientific_source_commit'] == '30e3f5faa0b72af8c861a320f6c88a47c9e03168'
    attempts = r['qa_attempts']
    assert [a['observed_exit_code'] for a in attempts] == [0,0,1,0]
    assert attempts[0]['tests'] == 83 and attempts[1]['tests'] == 1
    assert attempts[2]['tests'] == attempts[2]['failures'] == 1
    assert attempts[-1]['source_commit'] == r['scientific_source_commit']
    assert attempts[-1]['tests'] == 1 and not attempts[-1]['failures'] and not attempts[-1]['errors']
    assert 600 < attempts[-1]['seconds'] < 900
    assert r['qa_successful_native_worlds'] == 20 and r['qa_successful_annual_checkpoints'] == 80
    assert r['qa_successful_raw_files'] == 2524
    assert r['qa_uses_SCRIPTED_HTTP_corpus_process_launch_and_role_attestation']
    assert not r['qa_is_actual_backend_readiness_or_scientific_gain']
    assert r['failed_first_QA_junit_retained']
    assert not r['failed_first_QA_temporary_fixture_still_present']
    assert r['successful_QA_fixture_copied_before_temporary_retention_cleanup']
    assert r['qa_literal_first_planner_slots'] == r['qa_control_first_planner_slots'] == 6
    assert {k:len(v) for k,v in r['qa_repeated_exports'].items()} == {
        'scores':7,'choices':3,'effects':3,'requests':2}


def test_real_launch_is_finite_and_pending_readiness_snapshot_is_not_rewritten():
    r = receipt()
    assert r['start']['plan_sha256'] == r['plan_content_sha256']
    assert r['writer_pid'] == r['start']['pid'] == 11716 and r['writer_session'] == 75671
    assert r['objectives'] == ['throughput','content-utility'] and r['presentations'] == ['control','literal']
    assert r['own_histories'] == 4 and r['own_candidate_slots'] == 12
    assert r['common_references'] == 8 and r['native_worlds_upper_bound'] == 20
    assert r['budget']['readiness_sessions'] == 14 and r['budget']['initial_readiness_sessions'] == 2
    assert r['budget']['designer_http_timeout_seconds'] == [10,900]
    assert r['actual_progress_at_receipt']['stage'] == 'initial-readiness'
    assert r['actual_progress_at_receipt']['active'] == 'control'
    assert not r['two_initial_actual_readiness_passes_claimed']
    assert all(v['all_controls_passed'] is None for v in r['initial_real_readiness_at_receipt'].values())
    assert set(r['continuations']) == {'analysis','scores','choices','effects','requests'}
    assert not any(r[k] for k in ('held_out_evaluation','independent_optimizer_replication',
                                  'scientific_gain_demonstrated','publication_ready','model_calls_by_receipt_generation'))
    body = subprocess.check_output(['git','show',r['scientific_source_commit']+':'+r['protocol']],cwd=ROOT)
    assert hashlib.sha256(body).hexdigest() == r['protocol_sha256']
    assert body == (ROOT/r['protocol']).read_bytes()


def test_new_orientation_links_exist_and_keep_technical_and_scientific_scopes_distinct():
    result = check(ROOT,documents=(
        'research/components/native-parent-presentation-loop-v1.md',
        'research/protocols/campaigns/native-parent-presentation-loop-v1.md',
        'research/publication/native-parent-presentation-study-v1.md',
        'research/logbook/2026-11-14-parent-presentation-launch.md'),manifest=None)
    assert result['status'] == 'passed', result['errors']
