"""The actual91-page artifact and its scoped proof, not scientific replication."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from scripts.reports.paper_rebuild_bundle import integrated_expected, literal_dependencies
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def read(name):
    return checked(json.loads((ROOT / name).read_text()))


def receipt():
    return read('paper/integrated-choice-resource-build-v1.json')


def test_actual_build_visual_scope_and_preserved_previous_artifacts():
    r = receipt()
    assert (r['pages'], r['figures'], r['tables'], r['cited_references']) == (91, 48, 43, 29)
    assert hashlib.sha256((ROOT / r['output']).read_bytes()).hexdigest() == r['pdf_sha256']
    assert r['source_commit'] == '2940086de58eb4d50e890b8e23b37d90b11debb0'
    assert r['build']['exit_codes'] == [0, 0] and r['build']['downloads'] == 0
    assert r['build']['text_identical'] and r['build']['rendered_page_identity_verified']
    assert r['build']['overfull_underfull_or_undefined_diagnostics'] == 0
    assert r['build']['bbox_word_tags_accounted'] == 40010 and r['build']['off_page_text_words'] == 0
    assert r['visual_review']['pages_reviewed'] == list(range(1, 92))
    assert len(r['visual_review']['page_png_sha256']) == 91
    assert r['visual_review']['detail_pages_reviewed'] == [1, 4, 69, 70, 71, 72, 73]
    assert not r['visual_review']['clipped_or_overlapping_content_observed']
    for name, sha in r['preserved_files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
    assert not r['publication_ready']


def test_actual77_file_reconstruction_and_every_page_match_are_not_inference():
    r = receipt()
    p = read('research/results/integrated-choice-resource-rebuild-subset-verification-v1.json')
    policy = read('research/publication/paper-rebuild-allowlist-integrated-choice-resource-v1.json')
    assert p['original_receipt_content_sha256'] == r['content_sha256']
    assert p['input_files'] == len(policy['files']) == 77 and p['literal_dependencies'] == 74
    assert p['staging_exit_code'] == p['build_exit_code'] == p['render_exit_code'] == 0
    assert p['page_png_sha256'] == r['visual_review']['page_png_sha256']
    assert p['text_matches_reviewed_original'] and p['all_rendered_page_pixels_match_reviewed_original']
    assert not p['prior_dependency_setup_failure']['process_started']
    assert not p['prior_dependency_setup_failure']['original_staging_restarted']
    assert not p['clean_machine_build'] and not p['independent_inference_rerun']
    assert not p['publication_ready'] and not p['original_bytes_transformed']
    expected = integrated_expected(ROOT, r, policy['entrypoint'])
    for name in policy['files']:
        if name not in ('LICENSE', policy['receipt']):
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected[name]
    bodies = {name: (ROOT / name).read_bytes() for name in policy['files']}
    assert literal_dependencies(bodies, policy['entrypoint'], repository_parent_inputs=True) == r['literal_dependencies']


def test_built_source_contains_all_tracks_and_distinguishes_new_observation_types():
    r = receipt()
    body = '\n'.join(subprocess.check_output(['git', 'show', r['source_commit'] + ':' + name],
        cwd=ROOT, text=True) for name in r['source_files']['files'] if name.endswith('.tex'))
    for label in ('sec:problem', 'sec:design', 'sec:search', 'sec:parameter', 'sec:structural',
                  'sec:nested', 'sec:gradient-evidence', 'sec:matched', 'sec:observatory',
                  'sec:native-longitudinal-comparison', 'sec:native-choice-resource', 'app:reproduction'):
        assert '\\label{' + label + '}' in body
    labels = re.findall(r'\\label\{([^}]+)\}', body)
    assert len(labels) == len(set(labels))
    assert set(re.findall(r'\\ref\{([^}]+)\}', body)) <= set(labels)
    assert 'Exact recommended-topic matches are 0/10' in body
    assert 'matches\nto the recommended minimum duration are 2/10' in body
    assert 'without a topic enum' in body and 'not another optimizer run' in body
    assert 'neither unused evaluation nor independent\noptimizer replication' in body
    assert 'Unused evaluation is not newly rescored' in body or 'unused evaluation is not newly rescored' in body
    assert 'This algebra does not adopt that weight' in body
    scope = r['scientific_scope']
    assert scope['choice_pilot_physical_worlds'] == 3
    assert scope['resource_readout_measured_worlds'] == 12 and scope['resource_readout_unknown_worlds'] == 2
    assert not scope['new_objective_adopted'] and not scope['historical_selection_changed']
    assert not scope['own_advantage_demonstrated'] and not scope['unused_evaluation_rescored']
