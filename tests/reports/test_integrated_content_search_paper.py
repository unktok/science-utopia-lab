"""Reviewed native count/content manuscript snapshot and actual figure bindings."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import unicodedata

import pytest

from utopia.optimization.native_numeric_designer import checked

ROOT=Path(__file__).resolve().parents[2]


def read(name):return json.loads((ROOT/name).read_text())
def sha(body):return hashlib.sha256(body).hexdigest()


def test_new_reviewed_pdf_and_old_artifacts_keep_exact_own_bindings():
    r=checked(read('paper/integrated-content-search-build-v1.json'))
    assert sha((ROOT/r['output']).read_bytes())==r['pdf_sha256']
    for name,expected in r['preserved_files'].items():assert sha((ROOT/name).read_bytes())==expected
    assert (r['pages'],r['figures'],r['tables'],r['cited_references'])==(58,27,22,25)
    assert r['build']['exit_codes']==[0,0] and r['build']['text_identical']
    assert r['build']['first_log_sha256']==r['build']['second_log_sha256']
    assert r['build']['bbox_word_tags_accounted']==23111
    assert r['build']['off_page_text_words']==r['build']['unresolved_question_mark_pairs']==0
    assert r['visual_review']['pages_reviewed_for_layout']==58
    assert r['visual_review']['unchanged_page_PNGs_byte_identical']==56
    assert r['visual_review']['changed_final_pages_freshly_reviewed_at_150dpi']==[39,40]
    assert not r['visual_review']['clipped_or_overlapping_content_observed']
    assert r['scientific_scope']['closed_development_proposals']==8
    assert r['scientific_scope']['closed_development_completions']==6
    assert r['scientific_scope']['closed_development_technical_nulls']==2
    assert not r['scientific_scope']['live641xx_fixed_evaluation_counted_as_closed']
    assert not r['scientific_scope']['instruction_timing_assay_counted_as_executed']
    assert not r['scientific_scope']['publication_ready']


def test_source_dependencies_and_print_figure_preserve_all_actual_values():
    r=read('paper/integrated-content-search-build-v1.json');bodies=[]
    for group in ('source_files','figure_files','support_files','evidence_files'):
        names=r[group]['files'];assert names==sorted(set(names));values={}
        for name in names:
            original=subprocess.check_output(['git','show',r['source_commit']+':'+name],cwd=ROOT)
            values[name]=sha(original)
            if group=='source_files':bodies.append(original.decode())
        assert sha(json.dumps(values,sort_keys=True,separators=(',',':')).encode())==r[group]['manifest_sha256']
    body='\n'.join(bodies)
    assert len(re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',body))==27
    assert body.count(r'\begin{table}')==22
    labels=re.findall(r'\\label\{([^}]+)\}',body)
    assert len(labels)==len(set(labels))
    assert set(re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',body))<=set(labels)
    assert 'tab:native-content-search' in labels and 'fig:native-content-search-paths' in labels
    manifest=checked(read('paper/figures/native-objective-instrument-paper-v1/manifest.json'))
    data=checked(read('research/data/native-objective-instrument-loop-v1/report.json'))
    assert manifest['report_content_sha256']==data['content_sha256']
    assert manifest['report_file_sha256']==sha((ROOT/'research/data/native-objective-instrument-loop-v1/report.json').read_bytes())
    for name,expected in manifest['files'].items():
        assert sha((ROOT/'paper/figures/native-objective-instrument-paper-v1'/name).read_bytes())==expected
    assert not manifest['coordinates_or_losses_changed']


def test_actual_pdf_text_contains_closed_development_not_a_closed_live_evaluation():
    if not shutil.which('pdftotext'):pytest.skip('pdftotext unavailable; actual PDF text not inspected')
    r=read('paper/integrated-content-search-build-v1.json')
    raw=subprocess.check_output(['pdftotext',str(ROOT/r['output']),'-'])
    assert sha(raw)==r['build']['text_sha256']
    text=unicodedata.normalize('NFKC',raw.decode());text=re.sub(r'\s+',' ',text)
    assert 'Katy Börner' in text and '??' not in text
    assert 'Closed count-versus-content institutional search' in text
    assert 'six complete native worlds and two have technical nulls' in text
    assert 'no closed held-out result or institutional advantage is claimed' in text
