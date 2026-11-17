"""Actual retained117-page source staging, no TeX/model/native execution."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.reports.paper_rebuild_bundle import corrected_expected, stage
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = 'paper/integrated-corrected-choice-build-v1.json'
POLICY = 'research/publication/paper-rebuild-allowlist-integrated-corrected-choice-v1.json'


def read(name):
    return json.loads((ROOT / name).read_text())


def seal(value):
    value.pop('content_sha256', None)
    value['content_sha256'] = digest(value)
    return value


def test_actual_reviewed_source_closure_stages_literally(tmp_path):
    receipt = checked(read(RECEIPT))
    assert hashlib.sha256((ROOT / receipt['pdf']).read_bytes()).hexdigest() == receipt['pdf_sha256']
    policy = read(POLICY)
    output = tmp_path / 'exact-reviewed-subset'
    result = stage(ROOT, policy, output, source_commit=receipt['source_commit'])
    assert set(result['files']) == set(policy['files'])
    assert len(result['literal_tex_dependencies']) == receipt['literal_dependency_count']
    assert not result['original_bytes_transformed']
    assert not result['raw_or_model_data_included']
    assert not result['published_or_uploaded']
    assert result['new_model_calls'] == 0
    for name, expected in result['files'].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize('change', ['checksum', 'pages', 'review', 'ready', 'entrypoint', 'hash', 'escape'])
def test_bad_new_receipt_does_not_relax_historical_or_current_source_guards(change):
    receipt = copy.deepcopy(read(RECEIPT))
    if change == 'checksum': receipt['content_sha256'] = '0' * 64
    elif change == 'pages': receipt['pages'] = 111
    elif change == 'review': receipt['visual_review']['all117_layouts_reviewed'] = False
    elif change == 'ready': receipt['publication_ready'] = True
    elif change == 'entrypoint': receipt['entrypoint'] = 'paper/main.tex'
    elif change == 'hash': receipt['source_file_sha256']['paper/integrated.tex'] = '0' * 64
    else: receipt['source_file_sha256']['paper/../unbound.tex'] = '0' * 64
    if change != 'checksum': seal(receipt)
    with pytest.raises(ValueError):
        corrected_expected(ROOT, receipt, 'paper/integrated.tex')


def test_explicit_policy_cannot_omit_the_new_result_figure(tmp_path):
    policy = read(POLICY)
    policy['files'].remove('research/figures/native-corrected-choice-search-v1/corrected-choice-loss-paths.png')
    output = tmp_path / 'must-not-be-created'
    with pytest.raises(ValueError, match='missing allowlisted TeX dependency'):
        stage(ROOT, policy, output, source_commit=read(RECEIPT)['source_commit'])
    assert not output.exists()


def test_actual_subset_reconstruction_keeps_all117_reviewed_page_hashes():
    receipt = checked(read(RECEIPT))
    proof = checked(read('research/results/integrated-corrected-rebuild-subset-verification-v1.json'))
    assert proof['original_build_receipt_content_sha256'] == receipt['content_sha256']
    assert proof['original_reviewed_pdf_sha256'] == receipt['pdf_sha256']
    assert proof['page_png_sha256'] == receipt['visual_review']['page_sha256']
    assert proof['text_sha256'] == receipt['build']['text_sha256']
    assert proof['log_sha256'] == receipt['build']['log_sha256']
    assert proof['input_files'] == len(read(POLICY)['files']) == 89
    assert proof['literal_dependencies'] == receipt['literal_dependency_count'] == 86
    assert proof['all117_page_images_match_reviewed_original']
    assert not proof['numerical_replication'] and not proof['clean_machine_build']
    assert not proof['publication_ready']
