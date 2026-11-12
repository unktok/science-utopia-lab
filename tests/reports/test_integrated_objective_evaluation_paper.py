"""Closed-evaluation manuscript: exact source, actual PDF and retained history."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def test_new_pdf_and_all_prior_pdfs_keep_literal_own_bindings():
    r = checked(json.loads((ROOT/'paper/integrated-objective-evaluation-build-v1.json').read_text()))
    for name, expected in {**r['preserved_files'], r['output']:r['pdf_sha256']}.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected
    assert (r['pages'], r['figures'], r['tables'], r['cited_references']) == (59, 28, 23, 25)
    assert r['build']['exit_codes'] == [0, 0] and r['build']['text_identical']
    assert len(set(r['build']['log_sha256'])) == 1
    assert r['build']['bbox_word_tags_accounted'] == 23521
    assert not r['build']['off_page_text_words'] and not r['build']['unresolved_question_mark_pairs']
    assert r['visual_review']['pages_reviewed'] == list(range(1,60))
    assert len(r['visual_review']['page_png_sha256']) == 59
    assert not r['scientific_scope']['publication_ready']
    assert not r['scientific_scope']['independent_optimizer_replication']


def test_snapshot_source_assets_and_actual_pdf_text_are_bound():
    r = checked(json.loads((ROOT/'paper/integrated-objective-evaluation-build-v1.json').read_text()))
    bodies = []
    for group in ('source_files', 'figure_files', 'support_files', 'evidence_files'):
        hashes = {}
        for name in r[group]['files']:
            body = subprocess.check_output(['git','show',r['source_commit']+':'+name],cwd=ROOT)
            hashes[name] = hashlib.sha256(body).hexdigest()
            if group == 'source_files': bodies.append(body.decode())
        assert hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest() == r[group]['manifest_sha256']
    text = '\n'.join(bodies)
    assert len(re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', text)) == 28
    assert text.count(r'\begin{table}') == 23
    pdf_text = subprocess.check_output(['pdftotext', str(ROOT/r['output']), '-'])
    assert hashlib.sha256(pdf_text).hexdigest() == r['build']['text_sha256']
    normalized = re.sub(r'\s+', ' ', pdf_text.decode())
    assert 'All eighteen complete normally' in normalized
    assert 'cross-objective U differences' in normalized
    assert '2377 scientist replies' in normalized
    assert 'still running at this checkpoint' not in normalized
    assert '??' not in normalized
