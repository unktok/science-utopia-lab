from pathlib import Path

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
