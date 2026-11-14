"""Current reviewed manuscript subset, not scientific or clean-machine evidence."""
import json

import pytest

from scripts.reports import paper_rebuild_bundle as bundle
from utopia.optimization.native_numeric_designer import checked

POLICY = 'research/publication/paper-rebuild-allowlist-integrated-staged-construction-v1.json'


def test_staged_paper_subset_keeps_exact_reviewed_inputs_and_only_new_pdf(tmp_path):
    policy = json.loads((bundle.ROOT / POLICY).read_text())
    receipt = checked(json.loads((bundle.ROOT / policy['receipt']).read_text()))
    value = bundle.stage(bundle.ROOT, policy, tmp_path / 'subset', source_commit='SCRIPTED-staging-source')
    assert len(value['files']) == 68 and len(value['literal_tex_dependencies']) == 65
    assert (receipt['pages'], receipt['figures'], receipt['tables'], receipt['cited_references']) == (82, 42, 36, 27)
    assert receipt['output'] in value['files']
    assert 'output/pdf/science-utopia-lab-integrated-open-institutions-working-paper.pdf' not in value['files']
    assert value['original_build_source_commit'] == receipt['source_commit']
    assert receipt['scientific_scope']['new_scientific_model_calls'] == 0
    assert not receipt['scientific_scope']['real_staged_campaign_started_at_manuscript_snapshot']
    assert not receipt['publication_ready'] and not value['published_or_uploaded']


@pytest.mark.parametrize('changed', ['paper/integrated/discussion.tex',
    'paper/submission-sources.bib', 'paper/integrated/native-workflow-feedback.tex'])
def test_changed_new_inputs_cannot_inherit_the_reviewed_receipt(tmp_path, monkeypatch, changed):
    policy = json.loads((bundle.ROOT / POLICY).read_text())
    read = bundle.read_file
    def altered(root, name):
        body = read(root, name)
        return body + b'\nSCRIPTED changed input' if name == changed else body
    monkeypatch.setattr(bundle, 'read_file', altered)
    with pytest.raises(ValueError, match='changed from reviewed receipt'):
        bundle.stage(bundle.ROOT, policy, tmp_path / 'subset', source_commit='SCRIPTED')
    assert not (tmp_path / 'subset').exists()


def test_actual_rebuild_matches_all_reviewed_pages_without_claiming_new_science():
    r = checked(json.loads((bundle.ROOT / 'research/results/integrated-staged-construction-rebuild-subset-verification-v1.json').read_text()))
    original = checked(json.loads((bundle.ROOT / 'paper/integrated-staged-construction-build-v1.json').read_text()))
    assert r['original_receipt_content_sha256'] == original['content_sha256']
    assert r['subset']['files'] == 68 and r['subset']['literal_dependencies'] == 65
    assert r['subset']['all_staged_input_bytes_unchanged']
    assert r['actual_build']['exit_code'] == r['render']['exit_code'] == 0
    assert r['render']['pages'] == 82 and r['render']['all_page_pixels_match_reviewed_original']
    from utopia.system.design_patch import digest
    assert r['render']['page_hash_manifest_sha256'] == digest(original['visual_review']['page_png_sha256'])
    assert r['text']['default_pdftotext_sha256'] == original['build']['text_sha256']
    assert r['text']['identical_to_reviewed_original'] and r['new_model_calls'] == 0
    assert not r['original_PDF_or_receipt_overwritten'] and not r['publication_ready']
