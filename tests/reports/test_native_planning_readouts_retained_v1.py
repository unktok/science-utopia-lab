"""Source-bound software proof and actual waiting reader, not real study scores."""
import hashlib
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def test_preparation_keeps_launcher_failure_and_correct_full_path_verification():
    r = checked(json.loads((ROOT / 'research/results/native-planning-objective-readouts-preparation-v1.json').read_text()))
    assert r['analysis_source_commit'] == '780aa95bf456ead4f011501223390612d18264d0'
    assert [(q['tests'], q['failures']) for q in r['qa']] == [(34, 0), (1, 1), (1, 0), (93, 0)]
    assert 'fresh audit outside scientific source/raw required' in r['qa'][1]['failed_cases'][0]['message']
    full = r['full_path']
    assert full['actual_native_worlds_with_SCRIPTED_HTTP'] == 14 and full['saved_annual_boundaries'] == 56
    assert full['identical_original_cold_audits'] == full['identical_full_report_exports'] == 2
    assert full['cost_projections'] == 1 and len(full['report_files']) == 7
    assert (full['reference_rows'], full['own_slot_rows']) == (8, 6)
    start = checked(r['actual_reader_started'])
    assert start['analysis_source_commit'] == r['analysis_source_commit'] and r['actual_reader_session'] == 23077
    assert not start['new_inference_allowed'] and not start['retry_failed_stages']
    assert not full['scientific_model_results_claimed'] and not r['actual_study_completed_report_claimed']
    assert not r['new_inference_or_retry'] and not r['publication_ready']
    for name, expected in r['source_files_sha256'].items():
        blob = subprocess.check_output(['git', 'show', r['analysis_source_commit'] + ':' + name], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == expected
