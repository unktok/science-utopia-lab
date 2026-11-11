"""Manuscript facts join closed evidence, never the live held-out scores."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    return json.loads((ROOT / name).read_text())


def test_native_stopped_counts_costs_and_nulls_match_retained_verification():
    r = load('research/results/native-loop-stopped-prefix-verification-v1.json')
    text = (ROOT / 'paper/integrated/native-loop.tex').read_text()
    assert r['scientific_status'] == 'stopped'
    assert (r['reference_worlds'], r['submitted_slots'], r['complete_submissions'],
            r['technical_null_submissions'], r['unsubmitted_slots']) == (8, 11, 5, 6, 1)
    assert r['original_evaluation_worlds'] == 0 and r['audited_physical_worlds'] == 19
    assert r['scientist_completed_responses'] == 1796
    assert r['scientist_reported_prompt_tokens'] == 1615207
    assert r['scientist_reported_completion_tokens'] == 181308
    assert r['failure']['provider_eval_count'] == 8192 and not r['failure']['completion_unknown']
    rows = [line for line in text.splitlines() if line.startswith(('T &', 'E &'))]
    assert len(rows) == 6
    assert sum('Float used as index' in row for row in rows) == 2
    assert sum(row.count('Float used as index') for row in rows) == 3
    assert sum(row.count('Missing world envelope') for row in rows) == 2
    assert sum(row.count('Missing feature key') for row in rows) == 1
    assert sum(row.count('Not submitted') for row in rows) == 1
    assert 'not normal completion' in text and 'no imputed' in text


def test_paper_resource_table_rebuilds_each_row_from_saved_actor_vectors():
    r = load('research/data/native-resource-support-v1/summary.json')
    text = (ROOT / 'paper/integrated/native-loop.tex').read_text()
    assert r['summary']['complete_worlds'] == 44 and r['summary']['skipped_worlds'] == 5
    for row in r['per_year']:
        year = row['year']; vectors = [w['annual'][year - 1] for w in r['worlds']]
        active = sum(sum(v['is_active']) for v in vectors)
        n = sum(len(v['resources']) for v in vectors)
        lo = min(x for v in vectors for x in v['resources'])
        hi = max(x for v in vectors for x in v['resources'])
        expected = f'{year} & {active} / {n} & {lo:g} & {hi:g}'
        assert expected in text
    assert sum(sum(sum(v['is_active']) for v in w['annual']) for w in r['worlds']) == 880
    assert 'within-year minima' in text and 'different actors' in text


def test_new_section_references_are_closed_without_dropping_old_sections():
    entry = (ROOT / 'paper/integrated.tex').read_text()
    assert '\\input{integrated/native-loop}' in entry
    assert '\\input{integrated/design-diagnostics}' in entry
    sources = [entry]
    for path in re.findall(r'\\input\{([^}]+)\}', entry):
        sources.append((ROOT / 'paper' / (path + '.tex')).read_text())
    text = '\n'.join(sources)
    labels = re.findall(r'\\label\{([^}]+)\}', text)
    # Deeper inputs are exercised by the existing manuscript dependency tests.
    assert len(labels) == len(set(labels))
    assert '\\label{eq:conditional-accept-all}' in text
    assert 'for an unreviewed record' in text
    assert 'no participation, novelty or fairness' in text
    bib = (ROOT / 'paper/submission-sources.bib').read_text()
    for key in ('zhang2024aflow', 'feng2026adapt', 'cadet2026mining', 'braganeto2026community'):
        assert key in text and '{' + key + ',' in bib
