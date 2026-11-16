"""Document retention is not a new scientist run or optimizer replication."""
import hashlib
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def read(name):
    return checked(json.loads((ROOT / name).read_text()))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_current_reviewed_pdf_and_earlier_artifacts_are_literal():
    r = read('paper/integrated-consumer-source-build-v1.json')
    assert sha(ROOT / r['output']) == r['pdf_sha256']
    assert (r['pages'], r['figures'], r['tables'], r['cited_references']) == (104, 52, 49, 32)
    assert all(sha(ROOT / n) == s for n, s in r['preserved_files'].items())
    assert all(sha(ROOT / n) == s for n, s in r['literal_dependency_file_sha256'].items())
    assert all(sha(ROOT / n) == s for n, s in r['new_evidence_file_sha256'].items())


def test_review_is_bound_to_built_source_not_later_editorial_head():
    r = read('paper/integrated-consumer-source-build-v1.json')
    source = r['source_commit']
    assert source == '2d19cc966790ff0c2402b6889485ba58f32a49cd'
    for key in ('source_files', 'figure_files', 'support_files'):
        hashes = {n: hashlib.sha256(subprocess.check_output(
            ['git', 'show', source + ':' + n], cwd=ROOT)).hexdigest()
            for n in r[key]['files']}
        body = json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()
        assert hashlib.sha256(body).hexdigest() == r[key]['manifest_sha256']


def test_two_builds_visual_coverage_and_known_diagnostics_are_not_conflated():
    r = read('paper/integrated-consumer-source-build-v1.json')
    b, v = r['build'], r['visual_review']
    assert b['native_build_handles'] == [36830, 28222] and b['exit_codes'] == [0, 0]
    assert b['text_identical'] and len(set(b['log_sha256'])) == 1
    assert b['rendered_page_identity_verified'] and b['bbox_word_tags_accounted'] == 47619
    assert b['off_page_text_words'] == b['overfull_underfull_or_undefined_diagnostics'] == 0
    assert b['strict_XML_diagnostic'] and not b['pdfplumber_available']
    assert v['pages_reviewed'] == list(range(1, 105))
    assert len(v['page_png_sha256']) == 104 and len(v['contact_sheet_sha256']) == 9
    assert v['detail_pages_reviewed'] == [1, 4, 81, 82, 83, 84, 91, 92, 93]
    assert len(v['detail_png_sha256']) == 9 and not v['clipped_or_overlapping_content_observed']


def test_scientific_limits_and_unperformed_rebuild_are_explicit():
    r = read('paper/integrated-consumer-source-build-v1.json')
    s = r['scientific_scope']
    assert (s['own_slots'], s['own_complete_worlds'], s['runtime_nulls']) == (8, 7, 1)
    assert s['four_selected_own_systems_tie_strong_visible_reference']
    for key in ('new_wiring_observed', 'new_best_known_institution_demonstrated',
                'source_information_causal_comprehension_effect_demonstrated',
                'independent_optimizer_replication', 'new_unused_evaluation'):
        assert s[key] is False
    assert s['new_scientific_model_calls_by_manuscript_work'] == 0
    assert not r['publication_ready'] and not r['clean_machine_build']
    assert not r['new_paper_rebuild_subset_verified']


def test_old_100_page_subset_proof_keeps_its_narrower_identity_and_review_scope():
    r = read('research/results/integrated-terminal-rebuild-subset-verification-v1.json')
    old = read('paper/integrated-terminal-cost-build-v1.json')
    assert r['original_reviewed_pdf_sha256'] == old['pdf_sha256']
    assert sha(ROOT / r['original_receipt_file']) == r['original_receipt_file_sha256']
    assert r['subset_files_verified_before_and_after_build'] == 82
    assert r['literal_dependency_count'] == 79
    assert r['build_exit_code'] == r['render_exit_code'] == 0
    assert r['default_pdftotext_identical'] and r['all_pages_identical_to_previous_all_page_review']
    assert r['page_png_sha256'] == old['visual_review']['page_png_sha256']
    assert r['fresh_visual_review_page_count'] == len(r['fresh_visual_review_pages']) == 28
    assert not r['all_100_fresh_pages_visually_inspected']
    assert not r['current_104_page_amendments_included']
    assert not r['clean_machine_build'] and not r['publication_ready']
    assert r['new_model_calls'] == r['new_native_worlds'] == 0
