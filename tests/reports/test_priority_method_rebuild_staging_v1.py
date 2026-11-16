"""Historical input-byte staging only: no TeX, rendering, native world or model."""
import json

import pytest

from scripts.reports import paper_rebuild_bundle as bundle
from tests.reports.test_paper_rebuild_bundle import historical_integrated_root
from utopia.system.design_patch import digest

POLICY = 'research/publication/paper-rebuild-allowlist-integrated-priority-method-v1.json'
PUBLISHED = 'fe5b5cba6e7366fc33107b61d42fcdc9842de1c6'
BUILD_SOURCE = '09c2e6d1315b306bbbb4c7039321f1bd801a59a6'


@pytest.fixture(scope='module')
def snapshot(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('priority-historical-inputs')
    policy = json.loads((bundle.ROOT / POLICY).read_text())
    root = historical_integrated_root(tmp, source=PUBLISHED, explicit_policy=policy)
    return root, policy


def test_exact_reviewed111_page_inputs_stage_without_later_corrected_methods(snapshot, tmp_path):
    root, policy = snapshot
    output = tmp_path / 'subset'
    r = bundle.stage(root, policy, output, source_commit='SCRIPTED-source-only-test')
    assert r['original_build_source_commit'] == BUILD_SOURCE
    assert len(r['files']) == 86 and len(r['literal_tex_dependencies']) == 83
    assert set(r['files']) == set(r['literal_tex_dependencies']) | {
        'LICENSE', policy['receipt'], 'output/pdf/science-utopia-lab-integrated-priority-method-working-paper.pdf'}
    assert 'paper/integrated/native-priority-method-snapshot.tex' in r['files']
    assert 'paper/integrated/native-corrected-choice-design.tex' not in r['files']
    assert 'research/data/pre-scale-information-v1/table-tabular.tex' in r['files']
    assert not r['raw_or_model_data_included'] and not r['published_or_uploaded']
    assert not r['original_bytes_transformed'] and not r['numerical_reproduction_or_clean_machine_build_claimed']
    assert not r['limited_text_scan_findings']
    assert 'integrated.tex' in (output / 'REBUILD.md').read_text()


@pytest.mark.parametrize('name', ['paper/integrated.tex',
    'paper/integrated/native-priority-method-snapshot.tex',
    'paper/figures/native-priority-method-v1/method-loss-paths.png',
    'paper/references.bib',
    'output/pdf/science-utopia-lab-integrated-priority-method-working-paper.pdf'])
def test_changed_reviewed_input_is_rejected_before_any_staging(snapshot, tmp_path, monkeypatch, name):
    root, policy = snapshot
    original = bundle.read_file
    monkeypatch.setattr(bundle, 'read_file', lambda base, key:
        original(base, key) + b'\nSCRIPTED unreviewed change' if key == name else original(base, key))
    destination = tmp_path / 'changed'
    with pytest.raises(ValueError, match='changed from reviewed receipt'):
        bundle.stage(root, policy, destination, source_commit='SCRIPTED')
    assert not destination.exists()


@pytest.mark.parametrize('change', ['source-hash', 'outside-path', 'review-state'])
def test_resealed_invalid_receipt_cannot_replace_original_historical_bindings(snapshot, tmp_path, monkeypatch, change):
    root, policy = snapshot
    original = bundle.read_file
    receipt = json.loads(original(root, policy['receipt']))
    receipt.pop('content_sha256')
    if change == 'source-hash': receipt['source_file_sha256']['paper/integrated.tex'] = '0' * 64
    elif change == 'outside-path': receipt['source_file_sha256']['../../outside.tex'] = '0' * 64
    else: receipt['visual_review']['all111_layouts_reviewed'] = False
    receipt['content_sha256'] = digest(receipt)
    monkeypatch.setattr(bundle, 'read_file', lambda base, key:
        json.dumps(receipt).encode() if key == policy['receipt'] else original(base, key))
    destination = tmp_path / 'bad-binding'
    with pytest.raises(ValueError):
        bundle.stage(root, policy, destination, source_commit='SCRIPTED')
    assert not destination.exists()
