"""Claim boundaries of the committed partial result, without raw-file access."""
import json
from pathlib import Path

import pytest

from scripts.reports.code_mechanism_lab import verify_run
from utopia.system.code_mechanisms import sha, validate_code_artifact

ROOT = Path(__file__).resolve().parents[2]


def result():
    return json.loads((ROOT / "research/results/generated-code-mechanisms-v1.json").read_text())


def test_committed_proof_does_not_claim_successful_source_optimization():
    data = result()
    assert data["evidence_role"] == "initial-execution-only-optimization-incomplete"
    assert data["selected_optimized_system"] is None
    assert data["optimization_status"] == "failed-during-first-objective-code-revision"
    assert data["failed_proposals_assigned_numeric_loss"] is False
    assert data["frozen_source_replay_passed"] and data["checkpoint_resume_passed"]
    assert data["initial_attempt_statuses"] == ["invalid", "invalid", "complete"]
    validate_code_artifact(data["artifact"])
    assert data["artifact_sha256"] == sha(data["artifact"])
    assert data["summary"]["publication_records"] == 5
    assert data["summary"]["accepted"] + data["summary"]["rejected"] == 5


def test_full_search_publisher_refuses_execution_only_proof():
    with pytest.raises(ValueError):
        verify_run(result())
