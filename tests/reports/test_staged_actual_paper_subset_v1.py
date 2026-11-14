"""Current actual-result paper retention/subset; not new scientific evidence."""
import hashlib
import json

import pytest

from scripts.reports import paper_rebuild_bundle as bundle
from utopia.optimization.native_numeric_designer import checked

POLICY = 'research/publication/paper-rebuild-allowlist-integrated-staged-actual-v1.json'


def test_actual_paper_keeps_complete_unfavorable_science_and_previous_artifacts():
    root = bundle.ROOT
    r = checked(json.loads((root/'paper/integrated-staged-actual-build-v1.json').read_text()))
    assert (r['pages'], r['figures'], r['tables'], r['cited_references']) == (85, 44, 38, 28)
    assert r['visual_review']['pages_reviewed'] == list(range(1, 86))
    assert len(r['visual_review']['page_png_sha256']) == 85
    assert r['build']['rendered_page_identity_verified'] and r['build']['text_identical']
    assert r['build']['off_page_text_words'] == r['build']['layout_or_undefined_reference_warnings'] == 0
    scope = r['scientific_scope']
    assert (scope['own_slots'], scope['development_worlds'], scope['fixed_worlds'], scope['fixed_logical_labels']) == (6, 8, 3, 4)
    assert scope['unused_seeds'] == [1891355522]
    for key in ('own_advantage_demonstrated', 'independent_optimizer_replication', 'publication_ready'):
        assert not scope[key]
    assert scope['new_scientific_model_calls_by_manuscript_work'] == 0
    for name, expected in {**r['preserved_files'], r['output']: r['pdf_sha256']}.items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected


def test_exact_current_actual_paper_subset_stages_without_runtime_or_raw_data(tmp_path):
    policy = json.loads((bundle.ROOT/POLICY).read_text())
    receipt = checked(json.loads((bundle.ROOT/policy['receipt']).read_text()))
    r = bundle.stage(bundle.ROOT, policy, tmp_path/'subset', source_commit='SCRIPTED-staging-source')
    assert len(r['files']) == 71 and len(r['literal_tex_dependencies']) == 68
    assert set(r['files']) == set(receipt['literal_dependencies']) | {'LICENSE', receipt['output'], policy['receipt']}
    assert r['original_build_source_commit'] == receipt['source_commit']
    assert not r['raw_or_model_data_included'] and not r['published_or_uploaded']
    assert not r['numerical_reproduction_or_clean_machine_build_claimed']


@pytest.mark.parametrize('changed', ['paper/integrated/native-staged-construction.tex',
    'paper/figures/native-staged-fixed-v1/fixed-policy-seed-scores.png', 'paper/submission-sources.bib'])
def test_changed_actual_result_input_cannot_inherit_reviewed_receipt(tmp_path, monkeypatch, changed):
    policy = json.loads((bundle.ROOT/POLICY).read_text())
    original = bundle.read_file
    def altered(root, name):
        body = original(root, name)
        return body + b'\nSCRIPTED changed input' if name == changed else body
    monkeypatch.setattr(bundle, 'read_file', altered)
    with pytest.raises(ValueError, match='changed from reviewed receipt'):
        bundle.stage(bundle.ROOT, policy, tmp_path/'subset', source_commit='SCRIPTED')
    assert not (tmp_path/'subset').exists()


def test_actual_subset_rebuild_matches_all_pages_without_new_science():
    root = bundle.ROOT
    r = checked(json.loads((root/'research/results/integrated-staged-actual-rebuild-subset-verification-v1.json').read_text()))
    original = checked(json.loads((root/'paper/integrated-staged-actual-build-v1.json').read_text()))
    assert r['original_receipt_content_sha256'] == original['content_sha256']
    assert (r['input_files'], r['literal_dependencies'], r['pages']) == (71, 68, 85)
    assert r['cache_only_untrusted_actual_build_exit_code'] == 0
    assert r['all_staged_input_bytes_unchanged']
    assert r['all_rendered_page_pixels_match_reviewed_original']
    assert r['page_png_sha256'] == original['visual_review']['page_png_sha256']
    assert r['rebuilt_default_pdftotext_sha256'] == original['build']['text_sha256']
    assert not r['binary_pdf_identical']
    for key in ('new_downloads', 'new_model_calls', 'off_page_text_words'):
        assert r[key] == 0
    for key in ('raw_audit_repeated', 'independent_inference_rerun', 'numerical_results_recomputed',
                'clean_machine_build_claimed', 'original_pdf_or_receipt_overwritten',
                'published_or_uploaded', 'anonymous_or_release_clearance', 'publication_ready'):
        assert not r[key]
