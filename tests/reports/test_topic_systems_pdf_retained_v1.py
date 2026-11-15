"""Actual reviewed PDF retention, not independent scientific reproduction."""
import hashlib
import json
from pathlib import Path
import subprocess

from scripts.reports.paper_rebuild_bundle import integrated_expected, literal_dependencies
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = 'paper/integrated-topic-systems-build-v1.json'


def receipt():
    return checked(json.loads((ROOT / RECEIPT).read_text()))


def test_actual_98_page_build_preserves_every_prior_reviewed_artifact():
    r = receipt()
    assert (r['pages'], r['figures'], r['tables'], r['cited_references']) == (98, 50, 46, 29)
    assert r['source_commit'] == 'cb2fca8adbc37621df0408f8bb23dce337cb228c'
    assert hashlib.sha256((ROOT / r['output']).read_bytes()).hexdigest() == r['pdf_sha256']
    assert r['build']['exit_codes'] == [0, 0] and r['build']['downloads'] == 0
    assert r['build']['text_identical'] and r['build']['rendered_page_identity_verified']
    assert r['build']['overfull_underfull_or_undefined_diagnostics'] == 0
    assert r['build']['bbox_word_tags_accounted'] == 44438 and r['build']['off_page_text_words'] == 0
    assert r['visual_review']['pages_reviewed'] == list(range(1, 99))
    assert len(r['visual_review']['page_png_sha256']) == 98
    assert r['visual_review']['detail_pages_reviewed'] == [1, 4, *range(72, 81)]
    assert not r['visual_review']['clipped_or_overlapping_content_observed']
    for name, value in r['preserved_files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value


def test_actual_build_contains_closed_paths_without_inventing_a_gain_or_unused_evaluation():
    r = receipt()
    body = '\n'.join(subprocess.check_output(['git', 'show', r['source_commit'] + ':' + name],
        cwd=ROOT, text=True) for name in r['source_files']['files'] if name.endswith('.tex'))
    scope = r['scientific_scope']
    assert scope['own_slots'] == 6 and scope['complete_own_worlds'] == 5 and scope['runtime_nulls'] == 1
    assert not scope['own_advantage_demonstrated'] and not scope['new_unused_evaluation']
    assert not scope['independent_optimizer_replication'] and not r['publication_ready']
    assert scope['new_scientific_model_calls_by_manuscript_work'] == 0
    assert 'All six slots close without a gain over the visible strong reference' in body
    assert 'reference-inclusive incumbent is flat' in body
    assert 'conditional incompatibility, not a failed' in body
    for label in ('sec:problem', 'sec:design', 'sec:search', 'sec:parameter', 'sec:structural',
        'sec:nested', 'sec:gradient-evidence', 'sec:matched', 'sec:observatory',
        'sec:native-longitudinal-comparison', 'sec:native-choice-resource',
        'sec:native-topic-system-search', 'app:reproduction'):
        assert '\\label{' + label + '}' in body


def test_explicit_80_file_policy_binds_exact_historical_inputs_not_arbitrary_later_head():
    r = receipt()
    policy = checked(json.loads((ROOT / 'research/publication/paper-rebuild-allowlist-integrated-topic-systems-v1.json').read_text()))
    expected = integrated_expected(ROOT, r, policy['entrypoint'])
    assert len(policy['files']) == 80 and len(r['literal_dependencies']) == 77
    assert set(policy['files']) == set(r['literal_dependencies']) | {'LICENSE', RECEIPT, r['output']}
    bodies = {name: ((ROOT / name).read_bytes() if name in ('LICENSE', RECEIPT, r['output']) else
        subprocess.check_output(['git', 'show', r['source_commit'] + ':' + name], cwd=ROOT))
        for name in policy['files']}
    for name, raw in bodies.items():
        if name not in ('LICENSE', RECEIPT):
            assert hashlib.sha256(raw).hexdigest() == expected[name]
    assert literal_dependencies(bodies, policy['entrypoint'], repository_parent_inputs=True) == r['literal_dependencies']
