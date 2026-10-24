import json
from pathlib import Path

import pytest

from utopia.optimization.design_space import candidate_to_cli, load_candidate, load_space, validate_candidate


ROOT = Path(__file__).resolve().parents[2]
SPACE = ROOT / "research/specs/design-space-v0.json"
EXAMPLE = ROOT / "research/specs/example-design-v0.json"


def test_example_design_is_valid_and_maps_to_existing_cli():
    space, candidate = load_space(SPACE), load_candidate(EXAMPLE)
    validate_candidate(space, candidate)
    flags = candidate_to_cli(space, candidate, years=3)
    schedule = flags[flags.index("--acceptance_rate_schedule") + 1]
    assert schedule == "0.3,0.3,0.3"
    assert "--log_resource_ledger" in flags
    assert "--funding_budget_mode" in flags


@pytest.mark.parametrize(
    "change, message",
    [
        ({"acceptance_rate": 0.9}, "outside"),
        ({"reviews_per_paper": 2.5}, "expected integer"),
        ({"reviewer_matching": "prestige"}, "not in"),
        ({"reviewer_capacity": True}, "expected integer"),
    ],
)
def test_invalid_design_values_are_rejected(change, message):
    space, candidate = load_space(SPACE), load_candidate(EXAMPLE)
    candidate.update(change)
    with pytest.raises(ValueError, match=message):
        validate_candidate(space, candidate)


def test_missing_and_unknown_variables_are_rejected():
    space, candidate = load_space(SPACE), load_candidate(EXAMPLE)
    del candidate["resubmission_cost"]
    candidate["mystery"] = 1
    with pytest.raises(ValueError, match="missing variables.*unknown variables"):
        validate_candidate(space, candidate)


def test_spec_is_strict_json():
    assert json.loads(SPACE.read_text(encoding="utf-8"))["version"] == 1

