import json
from pathlib import Path

from scripts.figures.native_objective_instrument_paper_v1 import reference_groups

ROOT=Path(__file__).resolve().parents[2]


def test_every_exact_reference_tie_is_labelled_without_coordinate_jitter():
    r=json.loads((ROOT/'research/data/native-objective-instrument-loop-v1/report.json').read_text())
    assert reference_groups(r,'throughput')==[(-7.,['R1','R2','R3']),(-5.,['R5']),(0.,['R4'])]
    assert reference_groups(r,'content-utility')==[(-4.,['R1','R2','R3','R5']),(0.,['R4'])]
