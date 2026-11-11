"""Integrated-paper identity, coverage and literal-provenance regression checks."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def receipt():
    return json.loads((ROOT / 'paper/integrated-build-v1.json').read_text())


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def historical(name):
    """The v1 receipt binds its own source, not a later editable manuscript."""
    return subprocess.check_output(['git','show',receipt()['source_commit']+':'+name],cwd=ROOT)


def manuscript():
    return '\n'.join(historical(n).decode() for n in receipt()['source_files'])


def test_integrated_sources_assets_evidence_and_preserved_history():
    r = receipt()
    assert r['schema'] == 'scienceutopia.integrated-paper-build.v1'
    assert not r['artificial_page_cap']
    assert r['build_exit_code'] == r['downloads'] == 0
    for group in ('source_files', 'figure_files', 'support_files', 'evidence_files', 'preserved_files'):
        assert r[group]
        for name, expected in r[group].items():
            assert (ROOT / name).resolve().is_relative_to(ROOT)
            observed=sha(name) if group=='preserved_files' else hashlib.sha256(historical(name)).hexdigest()
            assert observed == expected, name
    assert sha(r['output']) == r['pdf_sha256']
    assert r['new_model_calls'] == r['new_code_world_executions'] == 0
    assert not r['new_raw_audit']


def test_recursive_inputs_figures_citations_and_crossreferences_are_closed():
    r = receipt(); body = manuscript()
    for name in re.findall(r'\\input\{([^}]+)\}', body):
        full = 'paper/' + name + ('' if name.endswith('.tex') else '.tex')
        assert full in r['source_files']
    figures = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', body)
    assert len(figures) == r['figures'] == 15
    for name in figures:
        full = (ROOT / 'paper' / name).resolve().relative_to(ROOT).as_posix()
        assert full in r['figure_files']
    labels = re.findall(r'\\label\{([^}]+)\}', body)
    assert len(labels) == len(set(labels))
    assert set(re.findall(r'\\ref\{([^}]+)\}', body)) <= set(labels)
    bib = historical('paper/references.bib').decode() + historical('paper/submission-sources.bib').decode()
    keys = set(re.findall(r'@\w+\s*\{\s*([^,\s]+)', bib))
    cited = {k.strip() for g in re.findall(r'\\cite\w*\{([^}]+)\}', body) for k in g.split(',')}
    assert cited <= keys and len(cited) == r['cited_references']


def test_whole_program_coverage_and_no_mechanical_rewrite_placeholders():
    body = manuscript()
    for label in ('sec:problem', 'sec:design', 'sec:search', 'sec:parameter',
                  'sec:structural', 'sec:nested', 'sec:gradient-evidence',
                  'sec:matched', 'sec:observatory', 'app:reproduction'):
        assert '\\label{' + label + '}' in body
    for marker in ('ZZPROTECTED', 'TODO', 'FIXME', '/Users/', 'turn155view'):
        assert marker not in body
    for literal in ('qwen3:8b', 'qwen3.6:35b-mlx-64k', '1078279d1ce8',
                    '425ec10396b1', 'ecab4b45c3ec', 'fdf4d1c16964',
                    '5ea52a520d7f', 'acf3a2e', 'b6654adefc42'):
        assert '\\code{' + literal + '}' in body
    assert 'qwen3: 8b' not in body and 'qwen3.6: 35b' not in body
    assert 'The post-update draw is not omitted when it worsens' in body
    assert not receipt()['layout_or_undefined_warnings']


def test_retained_native_case_counts_have_separate_sources():
    paths = (
        ('native-objective-redesign-v12-a1.json', 6, 565),
        ('native-nested-search-v13-a1.json', 8, 592),
        ('native-open-estimators-v11-a1.json', 8, 742),
    )
    sources = set()
    for name, worlds, replies in paths:
        d = json.loads((ROOT / 'research/results' / name).read_bytes())
        assert d['status'] == 'complete'
        assert d['physical_native_worlds'] == worlds
        assert d['physical_researcher_responses'] == replies
        sources.add(d['source_commit'])
    assert len(sources) == 3


def test_reviewed_pdf_pages_and_text_do_not_leak_placeholders():
    r = receipt()
    assert r['visual_qa']['all_final_pages_reviewed']
    assert r['visual_qa']['pages_reviewed'] == list(range(1, r['pages'] + 1))
    assert len(r['visual_qa']['page_png_sha256']) == r['pages']
    if shutil.which('pdfinfo'):
        info = subprocess.check_output(['pdfinfo', str(ROOT / r['output'])], text=True)
        assert re.search(r'^Pages:\s+' + str(r['pages']) + '$', info, re.M)
    if shutil.which('pdftotext'):
        text = subprocess.check_output(['pdftotext', str(ROOT / r['output']), '-'], text=True)
        assert 'ZZPROTECTED' not in text and '??' not in text
        assert 'Institution Foundry' in text
