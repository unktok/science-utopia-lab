"""Reviewed new manuscript identity and all original frozen dependencies."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def receipt():
    return checked(json.loads((ROOT / 'paper/integrated-catalog-planning-build-v1.json').read_text()))


def test_new_catalog_pdf_and_every_preserved_pdf_keep_their_own_bytes():
    r = receipt()
    for name, expected in {**r['preserved_files'], r['output']: r['pdf_sha256']}.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    assert (r['pages'], r['figures'], r['tables'], r['cited_references']) == (66, 33, 26, 26)
    assert r['build']['exit_codes'] == [0, 0] and r['build']['text_identical']
    assert len(set(r['build']['log_sha256'])) == 1
    assert r['build']['bbox_word_tags_accounted'] == 26797
    assert not r['build']['off_page_text_words'] and not r['build']['layout_or_undefined_reference_warnings']
    assert r['visual_review']['pages_reviewed'] == list(range(1, 67))
    assert len(r['visual_review']['page_png_sha256']) == 66
    assert r['visual_review']['fresh_150dpi_detail_pages'] == [1, 46, 47, 48, 49]
    scope = r['scientific_scope']
    assert scope['catalog_developer_comparison_counted_as_closed'] and scope['catalog_physical_worlds'] == 3
    assert scope['catalog_all_advice_choices_match_agenda'] == scope['catalog_validated_assignments'] == 10
    assert not scope['new_planning_objective_search_counted_as_closed']
    assert not scope['catalog_objective_specific_invention_or_heldout_gain_demonstrated']
    assert not scope['publication_ready']


def test_actual_frozen_source_manifests_and_pdf_text_are_complete():
    r = receipt(); source = []
    for group in ('source_files', 'figure_files', 'support_files', 'evidence_files'):
        hashes = {}
        for name in r[group]['files']:
            body = subprocess.check_output(['git', 'show', r['source_commit'] + ':' + name], cwd=ROOT)
            hashes[name] = hashlib.sha256(body).hexdigest()
            if group == 'source_files': source.append(body.decode())
        assert hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == r[group]['manifest_sha256']
    body = '\n'.join(source)
    assert len(re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', body)) == 33
    assert body.count(r'\begin{table}') == 26
    raw = subprocess.check_output(['pdftotext', str(ROOT / r['output']), '-'])
    assert hashlib.sha256(raw).hexdigest() == r['build']['text_sha256']
    text = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', raw.decode()))
    for marker in ('Concrete agendas change native planning and accepted output', '518,946', '45,741',
                   'All 496 scientist requests have committed replies', 'one reused development seed',
                   'a termination signal', 'not automatic invention'):
        assert marker in text
    assert '??' not in text
