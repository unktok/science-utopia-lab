"""Manuscript claims trace to all three retained developer conditions."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_complete_catalog_table_and_scope_match_retained_rows():
    path = ROOT / 'research/data/native-catalog-actuation-v1/controls.csv'
    with path.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    text = (ROOT / 'paper/integrated/native-catalog.tex').read_text()
    labels = ['No effect', 'Concrete advice', 'Direct assignment']
    assert [r['condition'] for r in rows] == ['cut', 'information', 'project']
    for label, row in zip(labels, rows):
        assert row['status'] == 'complete' and row['seed'] == '61001'
        table = f"{label} & ${int(float(row['throughput']))}$ & ${int(float(row['founder-activity']))}$ & {row['committed_responses']} & {row['direction_requests']} & {row['catalog_project_effects']}"
        assert table in text
    for marker in ('same initial graph, available grants', '3,3,3,2,2', '2,2,2,2,2',
                   'all ten original direction requests', 'zero original direction calls',
                   '50,40,40', '518,946', '45,741', '90,562', 'Three scientist-load POSTs',
                   'hand-written controls, not generated discoveries', 'one reused development seed',
                   'its first initial-readiness attempt stops', 'unknown response costs'):
        assert marker in text
    assert text.count(r'\includegraphics') == 2
    assert text.count(r'\begin{table}') == 1
    for path in ('project-states.png', 'losses-and-activity.png'):
        assert (ROOT / 'paper/figures/native-catalog-actuation-v1' / path).is_file()
    assert r'\input{integrated/native-catalog}' in (ROOT / 'paper/integrated.tex').read_text()
