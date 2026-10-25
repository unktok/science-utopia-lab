import json
from pathlib import Path

import pytest

from utopia.arguments import parse_arguments
from utopia.optimization.harness import (
    RunRegistry,
    apply_funding_reliability_to_readiness,
    apply_participation_suitability_to_readiness,
    build_command,
    build_report,
    design_id,
    evaluate_funding_reliability,
    evaluate_participation_measurement_suitability,
    load_study,
    manifest_status,
    run_id,
    sample_designs,
    study_revision,
)


ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "research/specs/study-v0-smoke.json"
STUDY_V1 = ROOT / "research/specs/study-v1-smoke.json"
STUDY_V2 = ROOT / "research/specs/study-v2-smoke.json"
LONGITUDINAL_STUDY = ROOT / "research/specs/study-v3-longitudinal-pilot.json"

RELIABILITY_POLICY = {
    "id": "funding-pipeline-reliability",
    "version": "1.0.0",
    "failure_action": "quarantine",
    "minimum_targets": 2,
    "maximum_semantic_invalid_attempt_rate": 0.25,
    "maximum_sanitized_reference_attempt_rate": 0.25,
    "maximum_request_error_attempt_rate": 0.0,
    "maximum_terminal_drop_rate": 0.0,
}

PARTICIPATION_POLICY = {
    "id": "participation-longitudinal-suitability",
    "version": "1.0.0",
    "failure_action": "recalibrate_fidelity",
    "minimum_years": 4,
    "minimum_initial_researchers": 10,
    "minimum_protected_slice_support": 5,
    "minimum_distinct_annual_active_counts": 2,
    "aggregate_minimum_exclusive": 0.0,
    "aggregate_maximum_exclusive": 1.0,
    "protected_slice_minimum_exclusive": 0.0,
    "protected_slice_maximum_exclusive": 1.0,
}


def test_seed_roles_are_disjoint_and_revision_is_deterministic():
    study, space, baseline = load_study(STUDY)
    assert set(study["seed_sets"]["exploration"]).isdisjoint(study["seed_sets"]["selection"])
    assert study_revision(study, space) == study_revision(study, space)
    assert design_id(baseline).startswith("d")
    assert len(study["metric_constitution_sha256"]) == 64


@pytest.mark.parametrize("kind", ["random", "sobol"])
def test_sampling_is_deterministic_valid_and_unique(kind):
    _, space, _ = load_study(STUDY)
    first = sample_designs(space, kind=kind, count=4, seed=7)
    second = sample_designs(space, kind=kind, count=4, seed=7)
    assert first == second
    assert len({json.dumps(row, sort_keys=True) for row in first}) == 4


def test_sobol_requires_power_of_two():
    _, space, _ = load_study(STUDY)
    with pytest.raises(ValueError, match="power of two"):
        sample_designs(space, kind="sobol", count=3, seed=7)


def test_zero_samples_supports_baseline_only_calibration():
    _, space, _ = load_study(LONGITUDINAL_STUDY)

    assert sample_designs(space, kind="sobol", count=0, seed=7) == []


def test_command_maps_to_safe_explicit_run_id(tmp_path):
    study, space, baseline = load_study(STUDY)
    revision = study_revision(study, space)
    identity = run_id(study["id"], revision, baseline, "smoke", "exploration", 101)
    command = build_command(
        study, space, baseline, run=identity, fidelity="smoke", seed=101, output_root=tmp_path
    )
    args = parse_arguments(command[4:], create_dirs=False)
    assert args.experiment_id == identity
    assert args.output_dir == str(tmp_path / "checkpoints" / identity)
    assert args.acceptance_rate_schedule == [0.3]


def test_command_carries_measurement_context_resource_profile(tmp_path):
    study, space, baseline = load_study(STUDY_V1)
    command = build_command(
        study, space, baseline, run="measurement-ready", fidelity="smoke", seed=101,
        output_root=tmp_path,
    )

    args = parse_arguments(command[4:], create_dirs=False)

    assert args.population_resource_profile == "balanced_two_band"
    assert len(study["seed_sets"]["exploration"]) == 5


def test_longitudinal_fidelity_is_small_four_year_pilot(tmp_path):
    study, space, baseline = load_study(LONGITUDINAL_STUDY)
    command = build_command(
        study, space, baseline, run="longitudinal-pilot", fidelity="longitudinal",
        seed=113, output_root=tmp_path,
    )

    args = parse_arguments(command[4:], create_dirs=False)

    assert study["sampler"]["count"] == 0
    assert args.experiment_stage == "pilot"
    assert args.num_years == 4
    assert args.num_institutions == 2
    assert args.num_conferences == 1
    assert args.acceptance_rate_schedule == [0.3, 0.3, 0.3, 0.3]


def test_v2_study_versions_funding_reliability_gate():
    study, space, _ = load_study(STUDY_V2)

    assert study["funding_reliability_policy"]["failure_action"] == "quarantine"
    assert study["funding_reliability_policy"]["maximum_terminal_drop_rate"] == 0.0
    old_study, old_space, _ = load_study(STUDY_V1)
    assert study_revision(study, space) != study_revision(old_study, old_space)


def test_registry_is_idempotent_and_recovers_interrupted(tmp_path):
    registry = RunRegistry(tmp_path / "registry.sqlite3")
    record = {
        "run_id": "run-1", "study_id": "study", "study_revision": "abc",
        "design_id": "d1", "design_json": "{}", "sampler": "random",
        "fidelity": "smoke", "seed_role": "exploration", "seed": 1,
        "max_attempts": 2, "command_json": "[]", "output_root": str(tmp_path),
        "created_utc": "now",
    }
    try:
        assert registry.add(record) is True
        assert registry.add(record) is False
        row = registry.start("run-1")
        assert row["attempt"] == 1 and row["status"] == "running"
        assert registry.recover_interrupted() == 1
        row = registry.rows()[0]
        assert row["status"] == "failed"
        assert registry.attempt_rows()[0]["status"] == "failed"
        row = registry.start("run-1")
        assert row["attempt"] == 2
        registry.finish("run-1", status="complete", returncode=0, wall_seconds=12.5, error=None)
        trace_dir = tmp_path / "checkpoints" / "run-1"
        trace_dir.mkdir(parents=True)
        (trace_dir / "funding_application_trace_year_1.summary.json").write_text(json.dumps({
            "counts": {
                "targets": 3, "validated": 3, "submitted": 2,
                "declined_by_agent": 1, "dropped": 0,
                "evaluated": 2, "decided": 2, "funded": 1,
                "allocations_recorded": 1, "allocations_applied": 1,
                "generation_attempts": 4, "semantic_invalid_attempts": 1,
                "request_error_attempts": 0,
            }
        }))
        report = build_report(
            registry, funding_reliability_policy=RELIABILITY_POLICY
        )
        assert report["status_counts"] == {"complete": 1}
        assert report["attempt_status_counts"] == {"failed": 1, "complete": 1}
        assert report["attempt_failure_rate"] == 0.5
        assert report["completed_run_wall_seconds"]["mean"] == 12.5
        assert report["funding_application_diagnostics"][0]["targets"] == 3
        assert report["funding_application_distributions"]["generation_attempts"]["mean"] == 4
        assert report["funding_application_reliability"][0]["state"] == "pass"
        assert report["report_errors"]
    finally:
        registry.close()


def test_run_id_rejects_unsafe_override():
    with pytest.raises(SystemExit):
        parse_arguments(["--experiment_stage", "smoke", "--run-id", "../escape"], create_dirs=False)


def test_manifest_status_rejects_failed_application_conservation(tmp_path):
    run_id_value = "run-1"
    docs = tmp_path / "docs" / run_id_value
    output = tmp_path / "checkpoints" / run_id_value
    docs.mkdir(parents=True)
    output.mkdir(parents=True)
    (docs / "run_manifest.json").write_text(json.dumps({
        "status": "complete", "args": {"output_dir": str(output)}
    }))
    (docs / "integrity_checks.json").write_text(json.dumps([
        {"year": 1, "passed": True, "failures": []}
    ]))
    summary = output / "funding_application_trace_year_1.summary.json"
    summary.write_text(json.dumps({"passed": False, "failures": ["unexplained"]}))
    row = {"output_root": str(tmp_path), "run_id": run_id_value}

    status, error = manifest_status(row)

    assert status == "invalid"
    assert error == "funding application trace failed: funding_application_trace_year_1.summary.json"


def test_funding_reliability_gate_quarantines_bad_and_small_runs():
    bad = evaluate_funding_reliability({
        "run_id": "bad", "targets": 10, "dropped": 1,
        "generation_attempts": 10, "semantic_invalid_attempts": 3,
        "sanitized_reference_attempts": 0, "request_error_attempts": 0,
    }, RELIABILITY_POLICY)
    small = evaluate_funding_reliability({
        "run_id": "small", "targets": 1, "dropped": 0,
        "generation_attempts": 1, "semantic_invalid_attempts": 0,
        "sanitized_reference_attempts": 0, "request_error_attempts": 0,
    }, RELIABILITY_POLICY)

    assert bad["state"] == "fail"
    assert bad["comparison_eligible"] is False
    assert bad["disposition"] == "quarantine"
    assert len(bad["policy_sha256"]) == 64
    assert any("semantic_invalid" in reason for reason in bad["reasons"])
    assert any("terminal_drop" in reason for reason in bad["reasons"])
    assert small["state"] == "insufficient_evidence"
    assert small["comparison_eligible"] is False


def test_funding_reliability_failure_blocks_objective_readiness():
    readiness = [{
        "design_id": "d1", "authorized_for_ranking": True, "blocking_reasons": []
    }]
    completed = [{"run_id": "run-1", "design_id": "d1"}]
    reliability = [{"run_id": "run-1", "state": "fail"}]

    apply_funding_reliability_to_readiness(readiness, completed, reliability)

    assert readiness[0]["authorized_for_ranking"] is False
    assert readiness[0]["funding_reliability_states"] == ["fail"]
    assert readiness[0]["blocking_reasons"] == [
        "one or more runs did not pass the funding reliability gate"
    ]


def test_participation_measurement_gate_accepts_interior_trajectory(tmp_path):
    import pandas as pd

    docs = tmp_path / "run-1"
    docs.mkdir()
    rows = []
    for year, active_count in ((1, 10), (2, 10), (3, 9), (4, 7)):
        for agent in range(10):
            inactive_count = 10 - active_count
            rows.append({
                "agent_id": f"r{agent}",
                "year": year,
                "is_active": agent >= inactive_count,
                "resource_band": "lower-band" if agent < 5 else "upper-band",
            })
    pd.DataFrame(rows).to_parquet(docs / "agent_year.parquet", index=False)
    evaluation = {
        "run_id": "run-1",
        "metrics": {"active-researcher-fraction": {"status": "measured"}},
    }

    result = evaluate_participation_measurement_suitability(
        evaluation, docs, PARTICIPATION_POLICY
    )

    assert result["state"] == "pass"
    assert result["comparison_eligible"] is True
    assert result["observations"]["annual_active_counts"] == [
        {"year": 1, "active": 10},
        {"year": 2, "active": 10},
        {"year": 3, "active": 9},
        {"year": 4, "active": 7},
    ]
    assert result["observations"]["aggregate_final_active_fraction"] == 0.7
    assert result["observations"]["protected_slice_final_active_fraction"] == 0.4


@pytest.mark.parametrize("final_lower_active", [0, 5])
def test_participation_measurement_gate_rejects_slice_floor_or_ceiling(
    tmp_path, final_lower_active
):
    import pandas as pd

    docs = tmp_path / f"run-{final_lower_active}"
    docs.mkdir()
    rows = []
    for year in range(1, 5):
        for agent in range(10):
            lower_active = final_lower_active if year == 4 else 5
            rows.append({
                "agent_id": f"r{agent}",
                "year": year,
                "is_active": agent >= 5 or agent < lower_active,
                "resource_band": "lower-band" if agent < 5 else "upper-band",
            })
    pd.DataFrame(rows).to_parquet(docs / "agent_year.parquet", index=False)
    evaluation = {
        "run_id": docs.name,
        "metrics": {"active-researcher-fraction": {"status": "measured"}},
    }

    result = evaluate_participation_measurement_suitability(
        evaluation, docs, PARTICIPATION_POLICY
    )

    assert result["state"] == "fail"
    assert result["disposition"] == "recalibrate_fidelity"
    assert any("protected_slice_final_active_fraction" in reason for reason in result["reasons"])


def test_participation_measurement_failure_blocks_readiness():
    readiness = [{
        "design_id": "d1", "authorized_for_ranking": True, "blocking_reasons": []
    }]
    completed = [{"run_id": "run-1", "design_id": "d1"}]
    suitability = [{"run_id": "run-1", "state": "fail"}]

    apply_participation_suitability_to_readiness(
        readiness, completed, suitability
    )

    assert readiness[0]["authorized_for_ranking"] is False
    assert readiness[0]["participation_measurement_states"] == ["fail"]
    assert readiness[0]["blocking_reasons"] == [
        "one or more runs did not pass the participation measurement gate"
    ]

