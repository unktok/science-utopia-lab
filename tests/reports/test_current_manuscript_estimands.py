"""Source/evidence editorial regressions, not factual web or method validation."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def bodies():
    pending = ['paper/integrated.tex']; found = {}
    while pending:
        name = pending.pop()
        if name in found:
            continue
        text = (ROOT/name).read_text(); found[name] = text
        pending.extend('paper/'+p+('' if p.endswith('.tex') else '.tex')
            for p in re.findall(r'\\input\{([^}]+)\}',text))
    return found


def test_current_citations_have_explicit_primary_identity_checks_not_invented_reproduction():
    audit = json.loads((ROOT/'research/results/manuscript-bibliographic-identity-audit-v4.json').read_text())
    current = audit; records = {}; visited = set()
    while True:
        for key,url in current.get('primary_records',current.get('additional_primary_records',{})).items():
            assert key not in records, 'duplicate identity in audit chain'
            records[key] = url
        if 'prior_audit' not in current:
            break
        prior_path = (ROOT / current['prior_audit']).resolve()
        assert prior_path.is_relative_to(ROOT) and prior_path not in visited
        visited.add(prior_path)
        assert hashlib.sha256(prior_path.read_bytes()).hexdigest() == current['prior_audit_file_sha256']
        current = json.loads(prior_path.read_text())
    cited = {k.strip() for t in bodies().values()
        for g in re.findall(r'\\cite\w*\{([^}]+)\}',t) for k in g.split(',')}
    assert cited == set(records) and len(cited) == audit['current_source_citation_count']
    for name, digest in audit['bibliography_file_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest
    assert not audit['all_cited_methods_independently_reproduced']
    assert not audit['all_related_work_claims_fully_reaudited']
    assert not audit['publication_ready']


def test_publication_updates_keep_stable_keys_but_actual_published_years():
    bib = (ROOT/'paper/submission-sources.bib').read_text()
    for key, year in [('hu2024adas',2025),('zhang2024aflow',2025),('ma2024sga',2024)]:
        block = re.search(r'@inproceedings\{'+key+r',([\s\S]*?)(?=\n@|\Z)',bib).group(1)
        assert re.search(r'year\s*=\s*\{'+str(year)+r'\}',block)
        assert 'booktitle=' in block and 'journal={arXiv' not in block
    assert '33940--33962' in bib and 'Xiong-Hui' in bib


def test_finite_estimands_retain_ties_nulls_selection_units_and_original_world():
    text = (ROOT/'paper/integrated/problem-method.tex').read_text()
    for marker in ('sec:finite-estimands','eq:finite-minimum-set','eq:reference-relative-loss',
                   'unavailable selection','conditional evidence','independent optimization histories',
                   'not scalar feedback alone','identical residual LLM randomness'):
        assert marker in text
    assert 'SciEvo~\\citep{jin2024scievo}' in text
    assert 'No retrospective failure penalty' in text


def test_bibliographic_accent_is_not_printed_as_a_literal_quote():
    bib = (ROOT/'paper/references.bib').read_text()
    assert r'B{\"o}rner' in bib
    assert 'B{"o}rner' not in bib
