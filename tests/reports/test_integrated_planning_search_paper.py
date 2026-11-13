"""Bind the closed-planning manuscript to its actual source and retained results."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def receipt():
    return checked(json.loads((ROOT / 'paper/integrated-planning-search-build-v1.json').read_text()))


def test_planning_manuscript_and_all_predecessors_keep_exact_bytes_and_scope():
    r = receipt()
    assert len(r['preserved_files']) == 24
    for name, expected in {**r['preserved_files'], r['output']: r['pdf_sha256']}.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    assert (r['pages'], r['figures'], r['tables'], r['cited_references']) == (69, 36, 27, 26)
    assert r['build']['exit_codes'] == [0, 0] and r['build']['text_identical']
    assert len(set(r['build']['log_sha256'])) == 1
    assert r['build']['bbox_word_tags_accounted'] == 28302
    for field in ('off_page_text_words', 'layout_or_undefined_reference_warnings',
                  'unresolved_question_mark_pairs', 'downloads'):
        assert r['build'][field] == 0
    assert r['visual_review']['pages_reviewed'] == list(range(1, 70))
    assert len(r['visual_review']['page_png_sha256']) == 69
    assert r['visual_review']['fresh_150dpi_detail_pages'] == [1, 2, 3, 48, 49, 50, 51, 52]
    s = r['scientific_scope']
    for name, value in {'planning_physical_worlds': 14, 'planning_common_references': 8,
                        'planning_own_submissions': 6, 'planning_own_completions': 6,
                        'planning_technical_nulls': 0, 'planning_content_occurrences': 216,
                        'planning_unique_contents': 54, 'planning_observed_input_classes': 8,
                        'new_model_calls_by_manuscript_work': 0}.items():
        assert s[name] == value
    assert s['new_planning_objective_search_counted_as_closed']
    assert s['planning_only_selection_source_changes']
    assert s['planning_all_own_assigned_losses_tie_best_reference']
    for field in ('planning_generated_policy_advantage_demonstrated',
                  'planning_independent_optimizer_replication',
                  'planning_unused_evaluation_dispatched', 'publication_ready'):
        assert not s[field]
    assert not r['publication_ready'] and not r['new_paper_rebuild_subset_verified']
    old = checked(json.loads((ROOT / 'paper/integrated-catalog-planning-build-v1.json').read_text()))
    assert not old['scientific_scope']['new_planning_objective_search_counted_as_closed']


def test_planning_manuscript_source_manifests_and_actual_pdf_content():
    r = receipt()
    source = []
    for group, count in [('source_files', 16), ('figure_files', 44),
                         ('support_files', 27), ('evidence_files', 163)]:
        assert len(r[group]['files']) == count
        hashes = {}
        for name in r[group]['files']:
            body = subprocess.check_output(['git', 'show', r['source_commit'] + ':' + name], cwd=ROOT)
            hashes[name] = hashlib.sha256(body).hexdigest()
            if group == 'source_files':
                source.append(body.decode())
        digest = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert digest == r[group]['manifest_sha256']
    body = '\n'.join(source)
    assert len(re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', body)) == 36
    assert body.count(r'\begin{table}') == 27
    raw = subprocess.check_output(['pdftotext', str(ROOT / r['output']), '-'])
    assert hashlib.sha256(raw).hexdigest() == r['build']['text_sha256']
    text = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', raw.decode()))
    for marker in ('216', '54 unique contents', '2,196,668', '194,184', '162',
                   'Content preferences refine observed count ties',
                   '518,946', 'All 496 scientist requests have committed replies'):
        assert marker in text
    assert '??' not in text


def test_complete_reading_guide_stays_with_body_instead_of_a_spill_page():
    r = receipt()
    page = subprocess.check_output(['pdftotext', '-f', '3', '-l', '3',
                                    str(ROOT / r['output']), '-']).decode()
    assert 'Reading this manuscript.' in page and '1 Introduction' in page
