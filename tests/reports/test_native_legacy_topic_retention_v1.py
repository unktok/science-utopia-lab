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
