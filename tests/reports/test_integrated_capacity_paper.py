"""Retained capacity manuscript and predecessors, not new inference."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def receipt():
    return checked(json.loads((ROOT / 'paper/integrated-capacity-authority-build-v1.json').read_text()))


def test_reviewed_capacity_artifact_keeps_all_predecessors():
    r = receipt()
    for path, expected in {**r['preserved_files'], r['output']: r['pdf_sha256']}.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    assert (r['pages'], r['figures'], r['tables'], r['cited_references']) == (64, 31, 25, 26)
    assert r['build']['exit_codes'] == [0, 0] and r['build']['text_identical']
    assert len(set(r['build']['log_sha256'])) == 1
    assert not r['build']['off_page_text_words']
    assert not r['build']['layout_or_undefined_reference_warnings']
    assert r['visual_review']['pages_reviewed'] == list(range(1, 65))
    assert r['visual_review']['fresh_150dpi_detail_pages'] == [43, 44, 45, 46]
    assert len(r['visual_review']['page_png_sha256']) == 64
    scope = r['scientific_scope']
    assert scope['capacity_TP_counted_as_closed']
    assert (scope['capacity_physical_attempts'], scope['capacity_own_submissions'],
            scope['capacity_own_completions'], scope['capacity_technical_nulls']) == (9, 4, 3, 1)
    assert not scope['capacity_unused_evaluation_dispatched']
    assert not scope['capacity_generated_policy_advantage_demonstrated']
    assert not scope['capacity_observed_tradeoff'] and not scope['publication_ready']


def test_actual_text_and_every_frozen_build_dependency_match():
    r = receipt()
    bodies = []
    for group in ('source_files', 'figure_files', 'support_files', 'evidence_files'):
        hashes = {}
        for name in r[group]['files']:
            blob = subprocess.check_output(['git', 'show', r['source_commit'] + ':' + name], cwd=ROOT)
            hashes[name] = hashlib.sha256(blob).hexdigest()
            if group == 'source_files':
                bodies.append(blob.decode())
        assert hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == r[group]['manifest_sha256']
    source = '\n'.join(bodies)
    assert len(re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', source)) == 31
    assert source.count(r'\begin{table}') == 25
    pdf = subprocess.check_output(['pdftotext', str(ROOT / r['output']), '-'])
    assert hashlib.sha256(pdf).hexdigest() == r['build']['text_sha256']
    text = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', pdf.decode()))
    for marker in ('Capacity-limited native search preserves a strong allocation rule',
                   'two transfers of 10 from the nonexistent actor system',
                   'it does not grant the native.project action',
                   '172 code calls and 34 committed annual boundaries',
                   'not dispatched for this flat pilot',
                   '1,171 completed replies'):
        assert marker in text
    assert '??' not in text
