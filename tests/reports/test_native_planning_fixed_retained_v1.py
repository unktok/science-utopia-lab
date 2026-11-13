"""Historical software preparation is not a real fixed-policy evaluation."""
import hashlib
import json
from pathlib import Path
import subprocess

from scripts.check_repository_docs import check
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def receipt():
    return checked(json.loads((ROOT / 'research/results/native-planning-fixed-preparation-v1.json').read_text()))


def test_committed_software_evidence_keeps_its_actual_source_and_limits():
    r = receipt(); source = r['implementation_source_commit']
    assert source == 'f5e9d1fef88afa4b36b34fcac07a9d01b56554b1'
    for path, expected in r['source_files_sha256'].items():
        body = subprocess.check_output(['git', 'show', source + ':' + path], cwd=ROOT)
        assert hashlib.sha256(body).hexdigest() == expected
    assert [(q['tests'], q['failures'], q['errors']) for q in r['qa']] == [
        (53, 0, 0), (59, 0, 0), (17, 0, 0), (98, 0, 0), (1, 0, 0)]
    assert [q['final_exit_zero_observed'] for q in r['qa']] == [True, False, True, True, True]


def test_sixteen_world_connected_proof_does_not_select_scientific_seeds():
    r = receipt(); full = r['full_path']; boundary = r['scientific_boundary']
    assert full['SCRIPTED_HTTP_corpus_origin_seed_inventory_and_load_attestations']
    assert not full['real_Qwen_scientific_results']
    assert full['native_worlds'] == 16 and full['annual_checkpoints'] == 64
    assert full['identical_original_audit_invocations'] == 2
    assert full['logical_rows'] == 20 and full['paired_differences'] == 32
    assert full['null_own_logical_rows'] == 2 and full['cost_projection_calls_match']
    for kind, count in [('scores', 8), ('choices', 3), ('effects', 3), ('requests', 2)]:
        export = full['exports'][kind]
        assert export['two_exports_match'] and len(export['files']) == count
        assert export['cold_CLI'] == (kind != 'scores')
    assert not any(boundary.values())


def test_active_orientation_and_new_notes_have_portable_links():
    result = check(ROOT, documents=('RESEARCH.md', 'research/INDEX.md', 'research/STATUS.md',
        'research/program-map.md', 'research/components/native-planning-fixed-evaluation-v1.md',
        'research/logbook/2026-11-13-planning-fixed-evaluation.md'), manifest=None)
    assert result['status'] == 'passed', result['errors']
