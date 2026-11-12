"""Retained closed-advice PDF and all prior snapshots, not new native evidence."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def receipt():
    return checked(json.loads((ROOT/'paper/integrated-advice-build-v1.json').read_text()))


def test_reviewed_artifact_and_all_predecessors_keep_their_literal_bindings():
    r = receipt()
    for name, expected in {**r['preserved_files'], r['output']:r['pdf_sha256']}.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected
    assert (r['pages'],r['figures'],r['tables'],r['cited_references']) == (61,29,24,26)
    assert r['build']['exit_codes'] == [0,0] and r['build']['text_identical']
    assert len(set(r['build']['log_sha256'])) == 1
    assert r['build']['bbox_word_tags_accounted'] == 24397
    assert not r['build']['off_page_text_words']
    assert r['build']['layout_or_undefined_reference_warnings'] == 0
    assert r['visual_review']['pages_reviewed'] == list(range(1,62))
    assert len(r['visual_review']['page_png_sha256']) == 61
    assert r['visual_review']['fresh_150dpi_detail_pages'] == [42,43]
    assert r['scientific_scope']['instruction_timing_assay_counted_as_closed']
    assert r['scientific_scope']['instruction_timing_worlds'] == 3
    assert not r['scientific_scope']['capacity_TP_counted_as_closed']
    assert not r['scientific_scope']['complete_behavioral_equivalence_claimed']
    assert not r['scientific_scope']['instruction_timing_effectiveness_demonstrated']
    assert not r['scientific_scope']['publication_ready']


def test_literal_build_source_assets_and_pdf_text_match_the_frozen_snapshot():
    r = receipt(); bodies = []
    for group in ('source_files','figure_files','support_files','evidence_files'):
        hashes = {}
        for name in r[group]['files']:
            body = subprocess.check_output(['git','show',r['source_commit']+':'+name],cwd=ROOT)
            hashes[name] = hashlib.sha256(body).hexdigest()
            if group == 'source_files': bodies.append(body.decode())
        assert hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest() == r[group]['manifest_sha256']
    src = '\n'.join(bodies)
    assert len(re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',src)) == 29
    assert src.count(r'\begin{table}') == 24
    pdf = subprocess.check_output(['pdftotext',str(ROOT/r['output']),'-'])
    assert hashlib.sha256(pdf).hexdigest() == r['build']['text_sha256']
    text = re.sub(r'\s+',' ',pdf.decode())
    for marker in ('All 30 direction requests','389 scientist replies with 360734 input',
                   'not establish general instruction ineffectiveness',
                   'complete ordered model-input and literal-response sequences differ',
                   'Institutional AI specifies executable governance manifests'):
        assert marker in text
    assert '??' not in text
