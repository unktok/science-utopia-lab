"""Actual source/subset/PDF identity evidence, not new scientific inference."""
import json
from pathlib import Path
import subprocess

from scripts.check_repository_docs import check
from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]


def test_actual_integrated_subset_rebuild_retains_scopes_and_reviewed_page_identity():
    r = checked(json.loads((ROOT / 'research/results/integrated-capacity-rebuild-subset-verification-v1.json').read_text()))
    build = checked(json.loads((ROOT / 'paper/integrated-capacity-authority-build-v1.json').read_text()))
    subset = checked(r['subset_manifest'])
    assert subset['source_commit'] == r['staging_source_commit']
    assert subset['original_build_source_commit'] == r['original_build_source_commit'] == build['source_commit']
    assert len(subset['files']) == 51 and len(subset['literal_tex_dependencies']) == 48
    assert file_sha256(ROOT / r['policy_file']) == r['policy_file_sha256']
    assert r['page_png_sha256'] == build['visual_review']['page_png_sha256']
    assert r['rebuilt_text_sha256'] == build['build']['text_sha256']
    assert r['fresh_visual_spot_checks'] == [1, 43] and r['pages'] == 64 and r['render_dpi'] == 90
    assert r['all_64_rendered_PNGs_byte_identical_to_reviewed']
    assert not r['binary_pdf_identical'] and r['rebuilt_pdf_sha256'] != r['original_reviewed_pdf_sha256']
    assert r['qa']['tests'] == 33 and not r['qa']['failures'] and not r['qa']['errors']
    for name in ('numerical_results_recomputed', 'raw_audit_repeated', 'independent_inference_rerun',
            'new_model_calls', 'published_or_uploaded', 'anonymous_or_release_clearance', 'publication_ready'):
        assert not r[name]
    for name, expected in subset['files'].items():
        assert file_sha256(ROOT / name) == expected
    source = subprocess.check_output(['git', 'show', r['staging_source_commit'] + ':scripts/reports/paper_rebuild_bundle.py'], cwd=ROOT)
    assert source == (ROOT / 'scripts/reports/paper_rebuild_bundle.py').read_bytes()


def test_rebuild_instructions_and_unchanged_historical_paths_remain_portable():
    assert check(ROOT, documents=('docs/paper-rebuild-bundle.md', 'paper/README.md'), manifest=None)['status'] == 'passed'
