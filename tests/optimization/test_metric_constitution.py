from copy import deepcopy
import json
from pathlib import Path

import pytest

from utopia.optimization.metric_constitution import (
    constitution_sha256,
    load_metric_constitution,
    validate_references,
)


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "research/specs/example-metric-constitution-v1.json"


def test_example_constitution_is_schema_and_reference_valid():
    document = load_metric_constitution(EXAMPLE)
    assert document["aggregation_boundary"]["default_mode"] == "constrained_vector"
    assert document["aggregation_boundary"]["global_scalarization_prohibited"] is True
    assert len(constitution_sha256(document)) == 64


def test_semantic_validator_rejects_unknown_evaluator():
    document = json.loads(EXAMPLE.read_text())
    document["metric_registry"][0]["evaluator_ref"] = "missing-evaluator"
    with pytest.raises(ValueError, match="unknown IDs: missing-evaluator"):
        validate_references(document)


def test_semantic_validator_rejects_duplicate_ids():
    document = json.loads(EXAMPLE.read_text())
    duplicate = deepcopy(document["metric_registry"][0])
    document["metric_registry"].append(duplicate)
    with pytest.raises(ValueError, match="duplicate metric IDs"):
        validate_references(document)
