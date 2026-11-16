"""Retained software proof, without requiring ignored native mock caches."""
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def receipt():
    return checked(json.loads((ROOT /
        'research/results/native-topic-priority-search-preparation-v1.json').read_text()))


def test_all_four_original_attempts_keep_literal_junit_bytes_and_outcomes():
    r = receipt()
    expected = [(6400, 60, 8), (2790, 60, 0), (46114, 1, 1), (70165, 1, 0)]
    for item, (handle, count, failures) in zip(r['qa'], expected, strict=True):
        p = ROOT / item['junit_file']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == item['junit_sha256']
        suite = ET.parse(p).getroot().find('testsuite')
        assert item['original_handle'] == handle
        assert int(suite.attrib['tests']) == count and int(suite.attrib['failures']) == failures
        assert int(suite.attrib['errors']) == 0 and int(suite.attrib['skipped']) == 0
        assert item['exit_code'] == int(failures > 0)


def test_actual_four_world_path_and_input_changes_are_not_claimed_as_response_gains():
    r = receipt(); worlds = r['worlds']
    assert [w['label'] for w in worlds] == ['reference', 'zero-priority', 'ask-tell-0', 'ask-tell-1']
    assert r['native_qa']['actual_mock_SDK_POSTs'] == sum(w['sequence']['wire_requests'] for w in worlds) == 652
    assert all(w['sequence']['completed_responses'] == 163 for w in worlds)
    assert all(w['physical_proof_status'] == 'complete' and w['native_assignment_count'] == 20 for w in worlds)
    assert all(w['native_collected_cost'] == {'status': 'measured', 'value': 200.} for w in worlds)
    hashes = [w['sequence']['ordered_full_request_payload_sha256'] for w in worlds]
    assert hashes[0] == hashes[1] and len(set(hashes)) == 3
    assert len({w['sequence']['ordered_literal_response_choices_sha256'] for w in worlds}) == 1
    assert r['native_qa']['paired_cold_proofs_per_world'] == 2


def test_measured_anchor_and_real_mock_loss_reach_existing_ask_tell_without_new_science_claim():
    r = receipt(); trace = r['search_trace']
    assert r['exact_zero_anchor_measured_before_warm_start']
    assert [s['actual_native_SCRIPTED_loss'] for s in trace] == [-20, -20, -20]
    assert trace[0]['next_suggestion']['phase'] == 'initial'
    assert trace[1]['next_suggestion']['phase'] == 'adaptive'
    assert trace[1]['next_suggestion']['based_on_observation_id'] == 'SCRIPTED-ask-tell-0'
    assert trace[2]['next_suggestion'] is None
    assert r['new_real_model_calls'] == r['new_critic_calls'] == 0
    for key in ('outer_scientific_study_CLI_verified', 'new_optimizer_invented',
                'free_institution_domain_narrowed', 'native_laws_or_loss_changed',
                'scientific_gain_demonstrated', 'independent_optimizer_replications', 'publication_ready'):
        assert r[key] is False
