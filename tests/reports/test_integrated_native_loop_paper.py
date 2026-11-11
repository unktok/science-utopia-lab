"""Manuscript facts join closed evidence, never the live held-out scores."""
import json
from pathlib import Path
import re
import hashlib
import subprocess

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


def test_unused_evaluation_paper_table_matches_every_retained_policy_mean():
    r = load('research/data/native-fixed-evaluation-v1/report.json')
    text = (ROOT / 'paper/integrated/native-loop.tex').read_text()
    expected = [
        ('reference:open-seed', 'Initial seed'), ('reference:legacy', 'Legacy'),
        ('reference:reviewed-accept-all', 'Reviewed / all'),
        ('reference:no-review-accept-all', 'No review / all'),
        ('reference:routed-one-accept-all', 'One reviewer / all'),
        ('reference:routed-two-accept-all', 'Two reviewers / all'),
        ('selected:throughput:parameters', 'T / numeric'),
        ('selected:efficiency:parameters', 'E / numeric'),
        ('selected:throughput:code-fixed-graph', 'T / fixed code'),
        ('selected:efficiency:code-fixed-graph', 'E / fixed code')]
    worlds = {w['physical_job']: w for w in r['physical_worlds']}
    for label, name in expected:
        row = next(line for line in text.splitlines() if line.startswith(name + ' &'))
        # Keep displayed rounding separate from the retained exact values.
        numbers = [float(x) for x in re.findall(r'(?<![A-Za-z])[-+]?\d*\.\d+|(?<![A-Za-z])[-+]?\d+', row)]
        observations = [worlds[x['physical_job']] for x in r['evaluation_rows'] if x['label'] == label]
        means = [sum(w['measurement']['metrics']['native.' + k]['value'] for w in observations) / 3
                 for k in ('accepted_decisions', 'accepted_peer_score_sum', 'review_records')]
        means += [r['evaluation_summary'][label][k]['mean'] for k in ('throughput', 'efficiency')]
        assert len(numbers) == len(means) == 5
        assert all(abs(a - b) < .00051 for a, b in zip(numbers, means))
    assert 'T / code and graph & -- & -- & -- & -- & --' in text
    assert 'E / code and graph & -- & -- & -- & -- & --' in text
    assert 'not an isolated effect of graph syntax or search' in text


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


def test_reviewed_snapshot_keeps_original_pdf_and_exact_source_boundaries():
    r = load('paper/integrated-native-execution-build-v1.json')
    assert r['schema'] == 'scienceutopia.integrated-native-execution-paper-build.v1'
    sha = lambda b: hashlib.sha256(b).hexdigest()
    assert sha((ROOT / r['output']).read_bytes()) == r['pdf_sha256']
    for name, expected in r['preserved_files'].items():
        assert sha((ROOT / name).read_bytes()) == expected
    for group in ('source_files', 'figure_files', 'support_files', 'evidence_files'):
        values = {name: sha(subprocess.check_output(
            ['git', 'show', r['source_commit'] + ':' + name], cwd=ROOT))
            for name in r[group]['files']}
        assert sha(json.dumps(values, sort_keys=True, separators=(',', ':')).encode()) == r[group]['manifest_sha256']
    assert r['pages'] == r['visual_review']['pages_reviewed'] == 49
    assert r['build']['exit_codes'] == [0, 0] and r['build']['text_identical']
    assert not r['build']['off_page_text_words']
    assert all(value is False for key, value in r['scientific_scope'].items()
               if key not in ('new_model_calls_from_manuscript', 'new_candidate_worlds_or_losses_from_manuscript'))
    assert r['scientific_scope']['new_model_calls_from_manuscript'] == 0
