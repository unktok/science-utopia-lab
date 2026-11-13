"""Actual minimal rebuild identity; no new numerical/model evidence."""
import hashlib
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def test_actual_planning_subset_keeps_original_source_and_all_reviewed_pixels():
    r = checked(json.loads((ROOT/'research/results/integrated-planning-search-rebuild-subset-verification-v1.json').read_text()))
    build = checked(json.loads((ROOT/'paper/integrated-planning-search-build-v1.json').read_text()))
    subset = checked(r['subset_manifest'])
    assert subset['source_commit'] == r['staging_source_commit'] == 'f4d0fe576fa1b5487ade490b7c0f7281a7d32b54'
    assert subset['original_build_source_commit'] == r['original_build_source_commit'] == build['source_commit']
    assert len(subset['files']) == 58 and len(subset['literal_tex_dependencies']) == 55
    assert hashlib.sha256((ROOT/r['policy_file']).read_bytes()).hexdigest() == r['policy_file_sha256']
    assert r['page_png_sha256'] == build['visual_review']['page_png_sha256']
    assert r['rebuilt_text_sha256'] == build['build']['text_sha256']
    assert r['pages'] == 69 and r['render_dpi'] == 90 and r['render_exit_code'] == 0
    assert r['fresh_visual_spot_checks'] == [1, 48]
    assert r['all_69_rendered_PNGs_byte_identical_to_reviewed']
    assert r['staging_CLI_exit_code'] == r['cache_only_untrusted_build_exit_code'] == 0
    assert r['build_attempt_exit_codes'] == [1, 0] and 'does not exist' in r['initial_build_error']
    assert not r['binary_pdf_identical'] and r['rebuilt_pdf_sha256'] != r['original_reviewed_pdf_sha256']
    for name in ('numerical_results_recomputed', 'raw_audit_repeated', 'independent_inference_rerun',
                 'new_model_calls', 'new_downloads', 'published_or_uploaded',
                 'anonymous_or_release_clearance', 'publication_ready', 'old_artifacts_changed'):
        assert not r[name]
    for name, expected in subset['files'].items():
        blob = subprocess.check_output(['git', 'show', r['staging_source_commit']+':'+name], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == expected
