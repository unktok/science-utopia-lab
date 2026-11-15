"""Retained software evidence; not real-Qwen scientific observations."""
import hashlib
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def test_actual_native_software_source_and_data_are_retained_without_science_claim():
    r = checked(json.loads((ROOT/'research/results/native-legacy-topic-software-retention-v1.json').read_text()))
    for name, sha in r['retained_files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == sha
    for name, sha in r['source_sha256s'].items():
        raw = subprocess.check_output(['git', 'show', r['source_commit'] + ':' + name], cwd=ROOT)
        assert hashlib.sha256(raw).hexdigest() == sha
    assert r['exit_code'] == 0 and r['original_session'] == 20671
    assert r['scientist_fixture_calls'] == 300
    core, related = r['worlds']
    assert core['policy'] == 'core-only' and core['effects'] == 14 and core['outside_core_effects'] == 0
    assert related['policy'] == 'core-plus-related' and related['effects'] == 20
    assert related['outside_core_effects'] == 16
    assert r['cold_physical_proofs_per_world'] == 2 and r['corrupted_witness_cases_per_world'] == 4
    assert all(w['double_physical_proof_equal'] for w in r['worlds'])
    assert all(w['resource_metric'] == {'status': 'measured', 'value': 200.} for w in r['worlds'])
    assert r['new_real_model_calls'] == 0 and r['original_corpus_and_HTTP_are_scripted']
    assert not r['real_model_feasibility_demonstrated'] and not r['automatic_invention_demonstrated']
    assert not r['loss_or_historical_selection_changed'] and not r['publication_ready']


def test_actual_new_workflow_witness_source_has_its_own_completed_construction():
    old = checked(json.loads((ROOT/'research/results/native-legacy-topic-software-retention-v1.json').read_text()))
    r = checked(json.loads((ROOT/'research/results/native-legacy-topic-software-retention-v2.json').read_text()))
    assert r['source_commit'].startswith('14c1caab') and r['original_session'] == 9901
    assert r['previous_retention_content_sha256'] == old['content_sha256']
    assert r['previous_record_not_overwritten'] and r['source_commit'] != old['source_commit']
    for name, sha in r['retained_files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == sha
    for name, sha in r['source_sha256s'].items():
        raw = subprocess.check_output(['git', 'show', r['source_commit'] + ':' + name], cwd=ROOT)
        assert hashlib.sha256(raw).hexdigest() == sha
    assert r['exit_code'] == 0 and r['actual_workflow_interval_effects_per_world'] == 48
    for w in r['worlds']:
        p = w['actual_workflow_interval']
        assert p['schema'] == 'scienceutopia.native-workflow-interval.v5'
        assert p['scope'] == 'fixed-native-effects-legacy-topic-workflow-v5'
        assert p['effect_witnesses'] == 48 and p['native_effects_per_year'] == 12
        assert not p['cold_audit_replaced'] and w['double_physical_proof_equal']
    assert r['scientist_fixture_calls'] == 300 and r['new_real_model_calls'] == 0
    assert not r['real_model_feasibility_demonstrated'] and not r['publication_ready']


def test_cold_software_initial_societies_are_equal_without_equating_raw_checkpoints():
    r = checked(json.loads((ROOT/'research/results/native-legacy-topic-software-retention-v2.json').read_text()))
    p = checked(json.loads((ROOT/'research/results/native-legacy-topic-software-initial-identities-v1.json').read_text()))
    assert p['retention_content_sha256'] == r['content_sha256']
    assert p['source_commit'] == r['source_commit']
    assert p['original_helper_sha256'] == r['source_sha256s'][p['original_helper_file']]
    assert p['same_initial_physical_society'] and len(p['worlds']) == 2
    assert len({w['physical_initial_identity'] for w in p['worlds']}) == 1
    assert len({w['sha256'] for w in p['worlds']}) == 2
    assert p['new_real_model_calls'] == p['new_worlds'] == 0 and not p['publication_ready']
