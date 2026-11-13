"""Print presentation keeps the complete closed study, ties and inference scope."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.figures.native_planning_paper_v1 import render, validate
from scripts.reports.native_objective_instrument_loop_v1 import cross_score_groups
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-planning-objective-loop-v1'


def inputs():
    return [checked(json.loads((DATA / name).read_text())) for name in ('report.json', 'content-contributions.json')]


def reseal(value):
    value.pop('content_sha256'); value['content_sha256'] = digest(value); return value


def test_exact_join_and_six_points_keep_every_label():
    report, content = inputs(); validate(report, content)
    groups, unavailable = cross_score_groups(report)
    assert not unavailable and len(groups) == 6 and sum(len(g['labels']) for g in groups) == 14
    assert groups[0]['labels'] == ['R7', 'U0', 'U1', 'U2']
    assert groups[0]['T'] == -18 and groups[0]['U'] == -13.333333333333332


def test_changed_content_scope_and_missing_slots_are_rejected():
    report, content = inputs(); bad = deepcopy(content)
    bad['worlds'][0]['sign_counts']['negative'] = 1
    with pytest.raises(ValueError):
        validate(report, reseal(bad))
    bad = deepcopy(report); bad['slots'].pop()
    with pytest.raises(ValueError):
        validate(reseal(bad), content)


def test_three_print_figures_render_without_changing_inputs(tmp_path):
    report, content = inputs(); before = digest([report, content])
    render(report, content, tmp_path)
    assert digest([report, content]) == before
    assert {p.name for p in tmp_path.iterdir()} == {
        name+'.'+ext for name in ('loss-paths', 'cross-scores', 'content-contributions') for ext in ('png', 'svg')}
    assert all(p.stat().st_size > 10000 for p in tmp_path.iterdir())


def test_complete_paper_table_matches_original_float_scores_and_groups():
    report, _ = inputs(); text = (ROOT / 'paper/integrated/native-planning-search.tex').read_text()
    groups, _ = cross_score_groups(report)
    mapping = {label: g['group'] for g in groups for label in g['labels']}
    rows = [('R'+str(i+1), x['scores']) for i, x in enumerate(report['references'])]
    rows += [(('T' if s['objective'] == 'throughput' else 'U')+str(s['generation']), s['cross_scores'])
             for s in report['slots']]
    def fmt(v):
        return str(int(v)) if v == int(v) else f'{v:.4f}'
    for label, scores in rows:
        line = next(line for line in text.splitlines() if line.startswith(label+' &'))
        assert f"& ${fmt(scores['throughput'])}$ & ${fmt(scores['content-utility'])}$ & {mapping[label]}" in line
    assert text.count(r'\includegraphics') == 3 and text.count(r'\begin{table}') == 1
    assert r'\input{integrated/native-planning-search}' in (ROOT / 'paper/integrated.tex').read_text()


def test_paper_keeps_observed_input_classes_costs_and_unfinished_claims():
    text = (ROOT / 'paper/integrated/native-planning-search.tex').read_text()
    for marker in ('All six programs submit and complete', 'No reference fallback',
        '91 pairs', '36 tie only in T', 'eight exact observed-input classes',
        '336', '56 committed annual boundaries', '216 accepted occurrences',
        '54 unique contents', '13,014.325 seconds', '2,196,668', '194,184', '368,423',
        '162 critic POSTs', '86 POSTs', '200 POSTs', 'unknown token usage',
        'not useful automatic', 'no unused seed is chosen'):
        assert marker in text
    assert 'three U programs preserve' in (ROOT / 'paper/integrated/discussion.tex').read_text()
