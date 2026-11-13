"""Retain the real pre-science interruption separately from scripted QA."""
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def receipt(name):
    return checked(json.loads((ROOT / 'research/results' / name).read_text()))


def test_original_launch_does_not_promote_scripted_worlds_to_actual_readiness():
    r = receipt('native-planning-objective-launch-verification-v1.json')
    assert r['scientific_source_commit'] == '8cd61578b94d86dd0cf2ff3b0e581d9a2698fc0f'
    assert r['start']['plan_sha256'] == r['plan_content_sha256']
    assert r['scientific_worlds_upper_bound'] == 14
    assert r['reference_worlds'] == 8 and r['own_candidate_slots'] == 6
    assert not r['P_is_an_objective_or_constraint']
    assert not r['initial_real_designer_readiness_pass_claimed']
    assert not r['SCRIPTED_test_worlds_are_actual_model_results']
    assert r['qa'][-1]['tests'] == 75 and r['qa'][-1]['failures'] == 0
    assert r['qa'][-2]['tests'] == 1 and r['qa'][-2]['seconds'] > 200
    assert sum(q['failures'] for q in r['qa']) == 2
    for path in ('scripts/run_native_planning_objective_loop_v1.py',
                 'research/protocols/campaigns/native-planning-objective-loop-v1.md'):
        assert subprocess.check_output(['git', 'show', r['scientific_source_commit'] + ':' + path], cwd=ROOT) == (ROOT / path).read_bytes()


def test_termination_is_not_a_loss_or_a_successful_certificate():
    r = receipt('native-planning-prestudy-stop-verification-v1.json')
    launch = receipt('native-planning-objective-launch-verification-v1.json')
    assert r['plan_content_sha256'] == launch['plan_content_sha256']
    assert r['terminal']['status'] == 'stopped'
    assert r['terminal']['stage'] == 'initial-readiness'
    assert r['terminal']['complete_references'] == r['scientific_worlds_started'] == r['own_proposals_started'] == 0
    assert r['http_records'] == r['completed_response_records'] + r['unknown_response_records'] == 24
    assert r['completed_response_records'] == r['completed_calibration_steps'] == 23
    assert r['last_dispatch']['http']['completion_unknown']
    assert r['last_dispatch']['http']['error_type'] == 'ConnectionError'
    assert r['last_dispatch']['timeout_seconds'] == [10, 900]
    assert r['reported_known_token_totals'] == {'prompt_eval_count': 433056, 'eval_count': 1038, 'prompt_eval_cached_count': 6721}
    assert 'SIGINT or SIGTERM' in r['local_service_evidence']['app_exact_line']
    assert any('500' in s and '16:30:42' in s for s in r['local_service_evidence']['server_exact_lines'])
    assert any('Listening' in s and '16:30:43.853' in s for s in r['local_service_evidence']['server_exact_lines'])
    assert not any(r[k] for k in ('readiness_pass_claimed', 'selection_exists', 'retry_or_output_salvage_performed', 'publication_ready', 'new_model_calls'))
