"""Verify the reviewed paper snapshot and old byte-reconstruction manifests."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import unicodedata

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = 'research/data/historical-paper-reconstruction-v1/'


def read(name):
    return json.loads((ROOT/name).read_text())


def sha(body):
    return hashlib.sha256(body).hexdigest()


def test_actual_new_pdf_and_preserved_old_pdfs_match_their_own_receipts():
    r = read('paper/integrated-estimands-build-v1.json')
    assert sha((ROOT/r['output']).read_bytes()) == r['pdf_sha256']
    for name, expected in r['preserved_files'].items():
        assert sha((ROOT/name).read_bytes()) == expected
    assert (r['pages'],r['figures'],r['tables'],r['cited_references']) == (56,26,21,25)
    assert r['build']['exit_codes'] == [0,0] and r['build']['text_identical']
    assert r['build']['first_log_sha256'] == r['build']['second_log_sha256']
    assert r['build']['layout_or_undefined_reference_warnings'] == 0
    assert r['build']['bbox_word_tags_accounted'] == 22027
    assert r['build']['off_page_text_words'] == 0
    assert r['visual_review']['pages_reviewed_for_layout'] == 56
    assert r['visual_review']['all_final_contact_sheets_inspected']
    assert r['retained_initial_build_issue']['exit_code'] == 1
    assert r['retained_initial_build_issue']['source_commit'] != r['source_commit']
    assert not any(r['scientific_scope'].values())


def test_new_snapshot_dependencies_and_finite_estimands_are_bound_to_its_build_source():
    r = read('paper/integrated-estimands-build-v1.json'); original = {}
    for group in ('source_files','figure_files','support_files','evidence_files'):
        names = r[group]['files']; assert names == sorted(set(names))
        hashes = {}
        for name in names:
            blob = subprocess.check_output(['git','show',r['source_commit']+':'+name],cwd=ROOT)
            hashes[name] = sha(blob)
            if group == 'source_files': original[name] = blob.decode()
        assert sha(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()) == r[group]['manifest_sha256']
    body = '\n'.join(original.values())
    assert len(re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',body)) == r['figures']
    assert body.count('\\begin{table}') == r['tables']
    labels = re.findall(r'\\label\{([^}]+)\}',body)
    assert len(labels) == len(set(labels))
    assert set(re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',body)) <= set(labels)
    assert 'eq:finite-minimum-set' in labels and 'eq:reference-relative-loss' in labels
    assert '\\input{integrated/native-loop}' in body
    assert '\\input{integrated/appendices}' in body


def test_actual_pdf_text_has_the_correct_author_glyph_and_no_unresolved_references():
    if not shutil.which('pdftotext'):
        pytest.skip('pdftotext is unavailable; the actual PDF text is not inspected')
    r = read('paper/integrated-estimands-build-v1.json')
    text = subprocess.check_output(['pdftotext',str(ROOT/r['output']),'-'])
    assert sha(text) == r['build']['text_sha256']
    viewed = unicodedata.normalize('NFC',text.decode())
    assert 'Katy Börner' in viewed and 'Katy B"orner' not in viewed
    assert '??' not in viewed
    assert 'What finite searches and fixed-policy comparisons estimate' in re.sub(r'\s+',' ',viewed)


def test_three_actual_staged_manifests_match_every_exact_historical_blob():
    expected = {'pilot':12,'v2':13,'anonymous':13}
    for name, count in expected.items():
        r = read(DATA+name+'-manifest.json')
        supplied = r.pop('content_sha256')
        assert sha(json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()) == supplied
        assert len(r['files']) == count
        assert r['source_commit'] == '8027f568cc16b0aed7428eab593f716b19530b20'
        for path, expected_sha in r['files'].items():
            blob = subprocess.check_output(['git','show',r['source_commit']+':'+path],cwd=ROOT)
            assert sha(blob) == expected_sha
        assert not r['original_bytes_transformed'] and not r['published_or_uploaded']
        assert not r['raw_or_model_data_included'] and not r['new_model_calls']
        assert not r['numerical_reproduction_or_clean_machine_build_claimed']
