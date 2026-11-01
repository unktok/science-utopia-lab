from copy import deepcopy
import json

import pytest

from scripts.figures.native_transition_validation import ROOT, INPUTS, load_evidence, make_figure


def test_actual_fidelity_and_bank_path_are_distinct():
    values = [json.loads((ROOT / p).read_text()) for p in INPUTS]
    fidelity, path, best = load_evidence(*values)
    assert fidelity["actual_native_secant"] == 0 and fidelity["predicted_directional_derivative"] < -1
    assert path[0]["expected_full_native_loss"] == -2.5
    assert best == -3 and best < path[-1]["expected_full_native_loss"] < -2.99
    bad = deepcopy(values)
    bad[1]["path"][-1]["expected_full_native_loss"] = -30
    with pytest.raises(ValueError, match="expectation"):
        load_evidence(*bad)


def test_figure_is_deterministic_and_manifest_bound():
    make_figure()
    output = ROOT / "paper/figures/native-transition-validation-v4"
    before = {s: output.with_suffix(s).read_bytes() for s in (".pdf", ".png", ".manifest.json")}
    make_figure()
    assert before == {s: output.with_suffix(s).read_bytes() for s in before}
