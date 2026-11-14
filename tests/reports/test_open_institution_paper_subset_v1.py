"""Only the reviewed81-page source/assets; no TeX, inference or old-data writes."""
import json
import subprocess

import pytest

from scripts.reports import paper_rebuild_bundle as bundle

POLICY = 'research/publication/paper-rebuild-allowlist-integrated-open-institutions-v1.json'
ASSET_SOURCE = 'c0c5bf1528ed823818c78a865813a4bf9d9380ed'


def fixture(tmp_path):
    policy = json.loads((bundle.ROOT / POLICY).read_text())
    root = tmp_path / 'bound-source'
    subprocess.run(['git', 'clone', '--shared', '--no-checkout', '--quiet',
        str(bundle.ROOT), str(root)], check=True)
    # This immutable asset commit includes the actualf344c77e literal inputs,
    # its reviewed PDF/receipt, and no dependency on changing current TeX.
    for name in policy['files']:
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(subprocess.check_output(['git', 'show', ASSET_SOURCE + ':' + name], cwd=bundle.ROOT))
    return root, policy


def test_exact_open_manuscript_subset_retains_new_results_not_the_old_pdf(tmp_path):
    root, policy = fixture(tmp_path)
    value = bundle.stage(root, policy, tmp_path / 'subset', source_commit='SCRIPTED-staging-source')
    assert len(value['files']) == 68 and len(value['literal_tex_dependencies']) == 65
    assert value['original_build_source_commit'] == 'f344c77e342d302e6fb1ce0484015749d0198607'
    assert value['original_build_receipt_schema'] == 'scienceutopia.integrated-open-institutions-manuscript.v1'
    assert {'paper/figures/native-open-institution-v3/objective-loss-paths.png',
        'paper/figures/native-open-institution-fixed-v1/fixed-policy-seed-scores.png'} <= set(value['literal_tex_dependencies'])
    assert 'output/pdf/science-utopia-lab-integrated-open-institutions-working-paper.pdf' in value['files']
    assert 'output/pdf/science-utopia-lab-integrated-workflow-feedback-working-paper.pdf' not in value['files']
    assert not any(n.endswith(('report.json', 'responses.sqlite', 'call.http.json')) for n in value['files'])
    assert not value['raw_or_model_data_included'] and not value['published_or_uploaded']


@pytest.mark.parametrize('name', ['paper/integrated.tex',
    'paper/figures/native-open-institution-v3/objective-loss-paths.png',
    'paper/figures/native-open-institution-fixed-v1/fixed-policy-seed-scores.png',
    'paper/submission-sources.bib'])
def test_altered_open_manuscript_input_still_fails_before_destination(tmp_path, name):
    root, policy = fixture(tmp_path); path = root / name
    receipt = (root / policy['receipt']).read_bytes()
    path.write_bytes(path.read_bytes() + b'\nSCRIPTED changed input')
    with pytest.raises(ValueError, match='changed from reviewed receipt'):
        bundle.stage(root, policy, tmp_path / 'changed-subset', source_commit='SCRIPTED')
    assert (root / policy['receipt']).read_bytes() == receipt
    assert not (tmp_path / 'changed-subset').exists()


def test_actual_subset_rebuild_retains_all81_reviewed_pixels_without_fresh_inference():
    from utopia.optimization.native_numeric_designer import checked
    proof = checked(json.loads((bundle.ROOT / 'research/results/integrated-open-institutions-rebuild-subset-verification-v1.json').read_text()))
    original = checked(json.loads((bundle.ROOT / 'paper/integrated-open-institutions-build-v1.json').read_text()))
    assert proof['subset']['files'] == 68 and proof['subset']['literal_dependencies'] == 65
    assert proof['subset']['all_staged_input_bytes_unchanged']
    assert proof['original_receipt_content_sha256'] == original['content_sha256']
    assert proof['render']['page_png_sha256'] == original['visual_review']['page_png_sha256']
    assert proof['render']['pages'] == 81 and proof['render']['all_page_pixels_match_reviewed_original']
    assert proof['text']['identical_to_reviewed_original'] and proof['actual_build']['exit_code'] == 0
    assert proof['actual_build']['existing_TeX_cache_required']
    assert not proof['fresh_inference_or_clean_machine_build_claimed']
    assert not proof['original_PDF_or_receipt_overwritten'] and not proof['publication_ready']
