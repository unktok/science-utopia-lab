"""Retained comparison is not proof of a new compile, render or visual review."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def evidence():
    return json.loads((ROOT / 'research/results/priority-subset-comparison-preparation-v1.json').read_text())


def test_actual_historical_control_matches_receipt_but_keeps_execution_unverified():
    prep = evidence(); record = prep['corrected_actual_control']; path = ROOT / record['report']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record['report_file_sha256']
    report = checked(json.loads(path.read_text()))
    original = checked(json.loads((ROOT / 'paper/integrated-priority-method-build-v1.json').read_text()))
    assert report['content_sha256'] == record['report_content_sha256']
    assert report['original_receipt_content_sha256'] == original['content_sha256']
    assert report['page_sha256'] == original['visual_review']['page_sha256']
    assert report['prepared_pdf_sha256'] == original['pdf_sha256'] and report['artifact_comparison_passed']
    assert (report['input_files'], report['literal_dependencies'], report['pages'], report['word_tags_checked']) == (86, 83, 111, 51578)
    assert all(not report[k] for k in ('actual_rebuild_execution_verified', 'fresh_visual_review_verified',
        'prepared_pdf_to_text_render_binding_verified', 'numerical_reproduction_verified', 'publication_ready'))


def test_pre_fix_checks_and_failed_real_cli_are_not_relabelled_as_success():
    prep = evidence(); failure = prep['failed_actual_control']
    assert failure['original_handle'] == 20727 and failure['exit_code'] == 1
    assert not failure['report_written'] and not failure['old_artifacts_or_scientific_run_changed']
    assert 'Relative build root' in failure['cause']
    for row, count in zip(prep['checks'], (23, 26), strict=True):
        path = ROOT / row['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['file_sha256']
        cases = ET.parse(path).getroot().findall('.//testcase')
        assert len(cases) == count == row['tests']
        assert not any(c.find(tag) is not None for c in cases for tag in ('error', 'failure', 'skipped'))
    assert all(not prep[k] for k in ('new_PDF_compile_or_render', 'fresh_visual_review_complete',
        'minimal_subset_rebuild_execution_verified', 'numerical_reproduction_verified', 'publication_ready'))


def test_rebuild_instructions_keep_command_provenance_and_visual_inspection_separate():
    doc = (ROOT / 'docs/paper-rebuild-bundle.md').read_text()
    assert 'compiler,' in doc and 'extraction or rendering execution' in doc
    assert 'separate actual' in doc and 'fresh PNG inspection' in doc
    assert 'Real build/render still waits for inference' in doc
