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
    run_id,
    sample_designs,
    study_revision,
)


ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "research/specs/study-v0-smoke.json"


def test_seed_roles_are_disjoint_and_revision_is_deterministic():
    study, space, baseline = load_study(STUDY)
    assert set(study["seed_sets"]["exploration"]).isdisjoint(study["seed_sets"]["selection"])
    assert study_revision(study, space) == study_revision(study, space)
    assert design_id(baseline).startswith("d")


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
        report = build_report(registry)
        assert report["status_counts"] == {"complete": 1}
        assert report["attempt_status_counts"] == {"failed": 1, "complete": 1}
        assert report["attempt_failure_rate"] == 0.5
        assert report["completed_run_wall_seconds"]["mean"] == 12.5
        assert report["report_errors"]
    finally:
        registry.close()


def test_run_id_rejects_unsafe_override():
    with pytest.raises(SystemExit):
        parse_arguments(["--experiment_stage", "smoke", "--run-id", "../escape"], create_dirs=False)

