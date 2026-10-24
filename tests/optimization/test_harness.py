import json
from pathlib import Path

import pytest

from utopia.arguments import parse_arguments
from utopia.optimization.harness import (
    RunRegistry,
    build_command,
    build_report,
    design_id,
    load_study,
    manifest_status,
    run_id,
    sample_designs,
    study_revision,
)


ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "research/specs/study-v0-smoke.json"
STUDY_V1 = ROOT / "research/specs/study-v1-smoke.json"


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
        report = build_report(registry)
        assert report["status_counts"] == {"complete": 1}
        assert report["attempt_status_counts"] == {"failed": 1, "complete": 1}
        assert report["attempt_failure_rate"] == 0.5
        assert report["completed_run_wall_seconds"]["mean"] == 12.5
        assert report["funding_application_diagnostics"][0]["targets"] == 3
        assert report["funding_application_distributions"]["generation_attempts"]["mean"] == 4
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

