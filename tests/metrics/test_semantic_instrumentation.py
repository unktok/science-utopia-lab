from copy import deepcopy
import json
from pathlib import Path

import jsonschema
import pytest

from scripts.reports.semantic_instrumentation_shadow import write_report
from utopia.metrics.semantic_instrumentation import (
    REPORT_SCHEMA,
    build_shadow_report,
    validate_bundle,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
BUNDLE_SCHEMA = ROOT / "research" / "specs" / "semantic-instrumentation-bundle-v1.schema.json"
REPORT_SCHEMA_PATH = (
    ROOT / "research" / "specs" / "semantic-instrumentation-shadow-report-v1.schema.json"
)
GROUND_TRUTH = FIXTURES / "semantic-instrumentation-ground-truth-v1.json"
GAMING = FIXTURES / "semantic-instrumentation-gaming-counterexample-v1.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _flags(report):
    return {item["id"]: item for item in report["gaming_counterdiagnostics"]}


@pytest.mark.parametrize("path", (GROUND_TRUTH, GAMING))
def test_versioned_bundle_and_report_schemas_validate(path):
    bundle = _load(path)
    bundle_schema = _load(BUNDLE_SCHEMA)
    report_schema = _load(REPORT_SCHEMA_PATH)
    jsonschema.Draft202012Validator.check_schema(bundle_schema)
    jsonschema.Draft202012Validator(bundle_schema).validate(bundle)

    report = build_shadow_report(bundle)

    assert report["schema"] == REPORT_SCHEMA
    jsonschema.Draft202012Validator.check_schema(report_schema)
    jsonschema.Draft202012Validator(report_schema).validate(report)


def test_ground_truth_fixture_recovers_verification_replication_and_correction():
    report = build_shadow_report(_load(GROUND_TRUTH))

    assert report["authorization"] == {
        "mode": "report_only",
        "optimization_input": False,
        "candidate_selection": False,
        "promotion_veto": False,
        "allowed_uses": ["shadow_diagnostic", "synthetic_contract_validation"],
    }
    assert report["contract_coverage"]["events"] == 13
    assert set(report["contract_coverage"]["event_type_counts"]) == {
        "claim.created",
        "claim.revised",
        "claim.withdrawn",
        "evidence.attached",
        "evidence.invalidated",
        "verification.completed",
        "replication.attempted",
        "replication.resolved",
        "correction.issued",
        "correction.propagated",
    }
    assert report["contract_coverage"]["claim_ids"] == 3
    assert report["contract_coverage"]["claim_versions"] == 4
    assert report["epistemic_progress_shadow"][
        "verification_weighted_entropy_reduction"
    ]["count"] == 2
    assert report["epistemic_progress_shadow"][
        "synthetic_truth_brier_improvement"
    ]["count"] == 2
    assert report["robustness_shadow"]["truth_aligned_independent_results"] == {
        "numerator": 2,
        "denominator": 2,
        "value": 1.0,
    }
    assert report["robustness_shadow"]["correction_issuance_coverage"]["value"] == 1.0
    assert report["robustness_shadow"]["correction_propagation_coverage"]["value"] == 1.0
    assert report["robustness_shadow"]["stale_dependent_claim_refs"] == []
    assert not any(item["triggered"] for item in report["gaming_counterdiagnostics"])


def test_gaming_fixture_detects_correlated_independence_splitting_and_easy_selection():
    report = build_shadow_report(_load(GAMING))
    flags = _flags(report)

    assert all(item["triggered"] for item in flags.values())
    assert len(flags[
        "declared-independence-with-correlated-or-missing-lineage"
    ]["event_ids"]) == 3
    assert flags["claim-splitting-on-one-truth-target"]["truth_target_ids"] == [
        "easy-target-a"
    ]
    assert flags["easy-target-selection"]["hard_target_coverage"]["value"] == 0.0
    assert report["epistemic_progress_shadow"][
        "verification_weighted_entropy_reduction"
    ]["count"] == 0
    assert report["epistemic_progress_shadow"]["independent_result_coverage"]["value"] == 0.0


def test_missing_lineage_is_retained_but_never_counted_as_independence():
    bundle = _load(GROUND_TRUTH)
    verification = next(
        item for item in bundle["events"]
        if item["event_type"] == "verification.completed"
    )
    verification["payload"]["lineage"]["data"] = {
        "status": "missing",
        "reason": "not_observed",
        "detail": "The synthetic test intentionally removes the verifier data lineage."
    }

    report = build_shadow_report(bundle)
    assessment = next(
        item for item in report["lineage_and_missingness"]["independence_assessments"]
        if item["event_id"] == verification["event_id"]
    )

    assert assessment["independence_status"] == "unknown"
    assert report["lineage_and_missingness"]["incomplete_lineages"] == 1
    assert report["lineage_and_missingness"]["missing_reasons"]["not_observed"] == 1
    assert _flags(report)[
        "declared-independence-with-correlated-or-missing-lineage"
    ]["triggered"] is True
    assert report["epistemic_progress_shadow"][
        "verification_weighted_entropy_reduction"
    ]["count"] == 1


def test_missingness_without_reason_fails_closed():
    bundle = _load(GROUND_TRUTH)
    correction = next(
        item for item in bundle["events"] if item["event_type"] == "correction.issued"
    )
    del correction["payload"]["replacement_claim_ref"]["reason"]

    with pytest.raises(ValueError, match="fields do not match"):
        validate_bundle(bundle)


def test_semantic_lineage_and_lifecycle_fail_closed():
    bundle = _load(GROUND_TRUTH)
    resolution = next(
        item for item in bundle["events"] if item["event_type"] == "replication.resolved"
    )
    resolution["provenance"]["source_event_ids"] = []

    with pytest.raises(ValueError, match="does not cite its attempt"):
        validate_bundle(bundle)

    bundle = _load(GROUND_TRUTH)
    resolution = next(
        item for item in bundle["events"] if item["event_type"] == "replication.resolved"
    )
    resolution["payload"]["outcome"] = "supports"
    with pytest.raises(ValueError, match="requires a prior challenging"):
        validate_bundle(bundle)

    bundle = _load(GROUND_TRUTH)
    resolution = next(
        item for item in bundle["events"] if item["event_type"] == "replication.resolved"
    )
    resolution["payload"]["lineage"]["organization"]["value"] = "laundered-lineage"
    with pytest.raises(ValueError, match="lineage differs from its attempt"):
        validate_bundle(bundle)

    bundle = _load(GROUND_TRUTH)
    bundle["events"][2]["step"] = 0
    with pytest.raises(ValueError, match="moves semantic time backwards"):
        validate_bundle(bundle)

    bundle = _load(GROUND_TRUTH)
    late_verification = deepcopy(bundle["events"][2])
    late_verification["event_id"] = "evt-late-invalid-evidence-verification"
    late_verification["sequence"] = len(bundle["events"])
    late_verification["step"] = 10
    late_verification["payload"]["verification_id"] = "late-invalid-verification"
    late_verification["payload"]["claim_ref"] = "claim-false@1"
    late_verification["payload"]["evidence_ids"] = ["evidence-false"]
    late_verification["provenance"]["source_event_ids"] = ["evt-evidence-false"]
    bundle["events"].append(late_verification)
    with pytest.raises(ValueError, match="already invalidated evidence"):
        validate_bundle(bundle)


def test_inconclusive_result_remains_in_denominator_without_progress_credit():
    bundle = _load(GROUND_TRUTH)
    verification = next(
        item for item in bundle["events"]
        if item["event_type"] == "verification.completed"
    )
    verification["payload"]["outcome"] = "inconclusive"

    report = build_shadow_report(bundle)

    assert report["epistemic_progress_shadow"]["independent_result_coverage"] == {
        "numerator": 1,
        "denominator": 2,
        "value": 0.5,
    }
    assert report["epistemic_progress_shadow"][
        "verification_weighted_entropy_reduction"
    ]["count"] == 1


def test_report_only_authorization_cannot_be_promoted_in_place():
    bundle = _load(GROUND_TRUTH)
    bundle["instrumentation_use"] = "optimization_input"

    with pytest.raises(ValueError, match="report_only"):
        validate_bundle(bundle)


def test_experimental_shadow_requires_explicitly_missing_ground_truth():
    bundle = _load(GAMING)
    bundle["classification"] = "experimental_shadow"
    bundle["ground_truth"] = {
        "status": "missing",
        "reason": "not_observed",
        "detail": "A real observational stream has no synthetic truth oracle."
    }

    report = build_shadow_report(bundle)

    assert report["ground_truth_boundary"] == {
        "status": "missing",
        "schema": None,
        "target_count": 0,
        "synthetic_only": False,
    }
    assert report["epistemic_progress_shadow"]["truth_target_coverage"] == {
        "numerator": 0,
        "denominator": 0,
        "value": None,
    }
    assert report["epistemic_progress_shadow"][
        "synthetic_truth_brier_improvement"
    ]["count"] == 0
    assert _flags(report)["easy-target-selection"] == {
        "id": "easy-target-selection",
        "status": "not_evaluable",
        "triggered": None,
        "hard_target_coverage": {"numerator": 0, "denominator": 0, "value": None},
        "interpretation": (
            "Avoiding hard targets can inflate verification yield; difficulty "
            "remains a separate diagnostic."
        ),
    }


def test_atomic_cli_report_does_not_mutate_source_and_refuses_overwrite(tmp_path):
    source = tmp_path / "bundle.json"
    source.write_bytes(GROUND_TRUTH.read_bytes())
    before = source.read_bytes()
    output = tmp_path / "shadow-report.json"

    report = write_report(source, output)

    assert source.read_bytes() == before
    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert report["authorization"]["optimization_input"] is False
    with pytest.raises(FileExistsError, match="refuse to overwrite"):
        write_report(source, output)


def test_exact_event_contract_rejects_unversioned_extra_fields():
    bundle = _load(GROUND_TRUTH)
    bundle["events"][0]["optimization_score"] = 1.0

    with pytest.raises(ValueError, match="fields do not match"):
        validate_bundle(bundle)
