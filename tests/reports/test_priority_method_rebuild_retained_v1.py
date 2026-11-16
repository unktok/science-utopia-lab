"""Tracked staging evidence is not an executed rebuild or scientific replication."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def evidence():
    return json.loads((ROOT / 'research/results/integrated-priority-rebuild-subset-preparation-v1.json').read_text())


def test_source_only_checks_are_retained_and_not_new_inference_or_rebuild():
    r = evidence(); qa = r['qa']
    path = ROOT / qa['junit']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == qa['junit_file_sha256']
    cases = ET.parse(path).getroot().findall('.//testcase')
    assert len(cases) == qa['tests'] == 38
    assert not any(c.find(tag) is not None for c in cases for tag in ('failure', 'error', 'skipped'))
    assert qa['exit_code'] == qa['failures'] == qa['errors'] == qa['skipped'] == 0
    assert qa['deselected'] == 20
    assert all(not r[k] for k in ('new_PDF_rebuild_performed', 'new_render_or_visual_review_performed',
        'current_corrected_methods_or_results_included', 'original_pdf_or_receipt_overwritten',
        'published_or_uploaded', 'independent_scientific_replication', 'publication_ready'))
    assert all(r[k] == 0 for k in ('new_model_calls', 'new_native_worlds', 'new_generated_code_executions'))


def test_policy_and_unchanged_reviewed_artifact_have_literal_original_bindings():
    r = evidence(); stage = r['successful_staging']
    receipt_path = ROOT / 'paper/integrated-priority-method-build-v1.json'
    receipt = checked(json.loads(receipt_path.read_text()))
    assert hashlib.sha256(receipt_path.read_bytes()).hexdigest() == r['original_receipt_file_sha256']
    assert hashlib.sha256((ROOT / receipt['pdf']).read_bytes()).hexdigest() == r['original_reviewed_pdf_sha256'] == receipt['pdf_sha256']
    policy_path = ROOT / stage['policy']
    assert hashlib.sha256(policy_path.read_bytes()).hexdigest() == stage['policy_file_sha256']
    policy = json.loads(policy_path.read_text())
    assert len(policy['files']) == stage['input_files'] == 86
    assert stage['literal_dependencies'] == 83 and stage['source_still_clean']
    assert stage['all_staged_bytes_match_exact_commit'] and stage['all_manifest_hashes_verified']
    assert stage['limited_text_scan_findings'] == 0
    assert receipt['source_commit'] == r['original_build_source_commit']
    assert receipt['pages'] == 111 and not receipt['minimal_source_subset_rebuild_verified']


def test_live_instructions_do_not_transfer_old_proof_or_claim_a_compiled_new_pdf():
    doc = (ROOT / 'docs/paper-rebuild-bundle.md').read_text()
    assert 'Latest reviewed artifact:111-page' in doc
    assert '86 exact files/83 literal dependencies' in doc
    assert 'minimal-input PDF rebuild remains unverified' in doc
    assert 'Preserved104-page' in doc
    assert 'cached/' in doc and 'untrusted Tectonic' in doc
