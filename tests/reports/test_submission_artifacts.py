"""Bind the reviewed working paper to sources/assets; no TeX build or inference."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def test_reviewed_pdf_and_complete_source_dependencies_match_receipt():
    receipt=json.loads((ROOT/'paper/submission-build-v2.json').read_text())
    assert receipt['status'] in ('working-draft-not-submission-ready','submission-ready-pending-user-approval')
    assert receipt['visual_qa']['all_pages_inspected'] is True
    assert receipt['visual_qa']['pages']==list(range(1,receipt['pages']+1))
    assets={receipt['output']:receipt['pdf_sha256'],'paper/submission.tex':receipt['tex_sha256'],
        'paper/submission-sources.bib':receipt['additional_bibliography_sha256'],
        'paper/figures/native-controls-v2-a1-print/manifest.json':receipt['strong_control_print_figure_manifest_sha256'],
        **receipt['additional_dependencies']}
    for relative,expected in assets.items():
        target=(ROOT/relative).resolve()
        assert target.is_relative_to(ROOT) and target.is_file()
        assert sha(target)==expected,relative
    info=shutil.which('pdfinfo')
    if info:
        text=subprocess.check_output([info,str(ROOT/receipt['output'])],text=True)
        assert int(re.search(r'^Pages:\s+(\d+)',text,re.M).group(1))==receipt['pages']


def test_manuscript_citations_and_included_figures_have_bound_local_inputs():
    receipt=json.loads((ROOT/'paper/submission-build-v2.json').read_text())
    tex=(ROOT/'paper/submission.tex').read_text()+(ROOT/'paper/submission-results.tex').read_text()
    bib=(ROOT/'paper/references.bib').read_text()+(ROOT/'paper/submission-sources.bib').read_text()
    available=set(re.findall(r'@\w+\s*\{\s*([^,\s]+)',bib))
    used={key.strip() for group in re.findall(r'\\cite\w*\{([^}]+)\}',tex) for key in group.split(',')}
    assert used and used<=available
    for relative in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',tex):
        assert 'paper/'+relative in receipt['additional_dependencies']
