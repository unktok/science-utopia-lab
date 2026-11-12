from pathlib import Path
from fractions import Fraction
import json

import pytest

from scripts.figures.native_objective_fixed_paper_v1 import export

REPORT = Path(__file__).resolve().parents[2]/'research/data/native-objective-fixed-evaluation-v1/report.json'


def test_actual_retained_public_report_renders_twice_without_mutation(tmp_path):
    before = REPORT.read_bytes()
    outputs = [tmp_path/'one', tmp_path/'two']
    for output in outputs:
        export(REPORT, output)
    assert REPORT.read_bytes() == before
    assert {p.name: p.read_bytes() for p in outputs[0].iterdir()} == {
        p.name: p.read_bytes() for p in outputs[1].iterdir()}
    with pytest.raises(ValueError, match='fresh output'):
        export(REPORT, outputs[0])


def test_every_printed_fixed_table_value_matches_original_report():
    text = (REPORT.parents[3]/'paper/integrated/native-loop.tex').read_text()
    table = text.split(r'\label{tab:native-tu-fixed}', 1)[1].split(r'\end{table}', 1)[0]
    lines = [line for line in table.splitlines() if line.startswith((
        'Reviewed all +', 'One-reviewer all +', 'No-review all +',
        'No-review reject-all +', 'Reviewed all;', 'T-selected literal'))]
    report = json.loads(REPORT.read_text())
    labels = [label for label in report['labels'] if label != 'selected:content-utility']
    assert len(lines) == len(labels) == 6
    rows = {(r['label'], r['seed']): r for r in report['logical_rows']}
    for line, label in zip(lines, labels):
        fields = line.split('&')
        for field, score in zip(fields[1:], report['score_order']):
            entries = field.split('$')[1].split(',')
            for entry, seed in zip(entries, report['seeds']):
                assert abs(float(Fraction(entry))-rows[label, seed]['scores'][score]) < 1e-12
