"""Actual minimal rebuild preserves every reviewed page, not scientific reruns."""
import hashlib
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def test_catalog_minimal_rebuild_keeps_exact_reviewed_page_pixels_and_scopes():
    r = checked(json.loads((ROOT / 'research/results/integrated-catalog-rebuild-subset-verification-v1.json').read_text()))
    build = checked(json.loads((ROOT / 'paper/integrated-catalog-planning-build-v1.json').read_text()))
    subset = checked(r['subset_manifest'])
    assert len(subset['files']) == 54 and len(subset['literal_tex_dependencies']) == 51
    assert subset['source_commit'] == r['staging_source_commit']
    assert subset['original_build_source_commit'] == r['original_build_source_commit'] == build['source_commit']
    assert r['pages'] == 66 and r['render_dpi'] == 90
    assert r['page_png_sha256'] == build['visual_review']['page_png_sha256']
    assert r['rebuilt_text_sha256'] == build['build']['text_sha256']
    assert r['fresh_visual_spot_checks'] == [1, 47] and r['all_66_rendered_PNGs_byte_identical_to_reviewed']
    assert not r['binary_pdf_identical'] and r['cache_only_untrusted_build_exit_code'] == 0
    assert r['qa']['tests'] == 38 and r['qa']['failures'] == r['qa']['errors'] == 0
    for key in ('new_downloads', 'new_model_calls', 'numerical_results_recomputed', 'raw_audit_repeated',
                'independent_inference_rerun', 'old_artifacts_changed', 'published_or_uploaded',
                'anonymous_or_release_clearance', 'publication_ready'):
        assert not r[key]
    for name, expected in subset['files'].items():
        blob = subprocess.check_output(['git', 'show', r['staging_source_commit'] + ':' + name], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == expected
    tool = subprocess.check_output(['git', 'show', r['staging_source_commit'] + ':scripts/reports/paper_rebuild_bundle.py'], cwd=ROOT)
    assert hashlib.sha256(tool).hexdigest() == r['staging_tool_file_sha256']
