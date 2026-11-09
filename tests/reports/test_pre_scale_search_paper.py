"""Bind the manuscript's rounded tables to retained actual closed observations."""
import json
from pathlib import Path
import statistics

from scripts.reports.pre_scale_search_reproduce_v1 import validate

ROOT = Path(__file__).resolve().parents[2]


def test_actual_paper_table_matches_all_retained_evaluation_labels():
    report = validate(json.loads((ROOT / 'research/data/pre-scale-search-v1/report.json').read_text()))
    text = (ROOT / 'paper/integrated/pre-scale-search.tex').read_text()
    body = text.split('\\label{tab:prescale-evaluation}', 1)[1].split('\\end{tabular}', 1)[0]
    rows = [line for line in body.splitlines() if ' & ' in line and not line.startswith('\\toprule')]
    assert len(rows) == 12
    worlds = {w['identity']: w for w in report['worlds']}
    for line in rows:
        fields = [x.strip().replace('$', '').removesuffix('\\\\').strip() for x in line.split('&')]
        title, *numbers = fields
        prefix, method = title.split(': ', 1)
        if prefix == 'Ref':
            label = 'reference:' + {'open seed': 'open-seed', 'reviewed accept-all': 'reviewed-accept-all',
                'no-review accept-all': 'no-review-accept-all', 'no-review reject-all': 'no-review-reject-all'}[method]
        else:
            label = 'selected:' + {'T': 'throughput', 'E': 'efficiency'}[prefix] + ':' + {
                'numerical': 'parameters', 'code / fixed graph': 'code-fixed-graph',
                'code and graph': 'code-and-graph', 'uniform': 'random'}[method]
        selected = [r for r in report['evaluation_rows'] if r['label'] == label]
        assert len(selected) == 3
        expected = [statistics.mean(worlds[r['physical_job']]['measurement']['metrics'][m]['value'] for r in selected)
            for m in ('native.accepted_decisions', 'native.accepted_peer_score_sum', 'native.review_records')]
        expected += [report['evaluation_summary'][label][s]['mean'] for s in ('throughput', 'efficiency', 'selective')]
        assert [float(x) for x in numbers] == [round(x, 3) for x in expected]


def test_actual_search_table_retains_both_slots_and_fixed_initial_selections():
    report = validate(json.loads((ROOT / 'research/data/pre-scale-search-v1/report.json').read_text()))
    text = (ROOT / 'paper/integrated/pre-scale-search.tex').read_text()
    body = text.split('\\label{tab:prescale-slots}', 1)[1].split('\\end{tabular}', 1)[0]
    rows = [line for line in body.splitlines() if ' & ' in line and not line.startswith('\\toprule')]
    assert len(rows) == 8
    for line in rows:
        objective, method, *values = [x.strip().replace('$', '') for x in line.split('&')]
        arm = {'T': 'throughput', 'E': 'efficiency'}[objective] + ':' + {
            'Numerical': 'parameters', 'Code / fixed graph': 'code-fixed-graph',
            'Code and graph': 'code-and-graph', 'Uniform': 'random'}[method]
        slots = [r for r in report['search_slots'] if r['arm'] == arm]
        for value, slot in zip(values[:2], slots, strict=True):
            assert value == 'F' if slot['own_loss'] is None else float(value) == round(slot['own_loss'], 3)
        selected = report['optimization_paths'][arm]['fixed_selection']['selected_row_id']
        assert ('Initial' in values[2]) == selected.startswith('reference:')
        if not selected.startswith('reference:'):
            assert selected.rsplit(':', 1)[1].upper() in values[2]
