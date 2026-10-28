import json
from pathlib import Path
import sys

import pytest

from utopia.optimization import harness
from utopia.optimization.artifact_reuse import receipt_path
from utopia.optimization.harness import RunRegistry, build_report, canonical_json
from utopia.optimization.metric_conditioned_study import MetricConditionedStudy


COMMIT = "a" * 40
ROOT = Path(__file__).resolve().parents[2]


def _command(run_id, output_root, *, seed=601, model="qwen3:8b"):
    return [
        sys.executable,
        "-B",
        "-m",
        "utopia",
        "--model",
        model,
        "--api-backend",
        "ollama",
        "--experiment_stage",
        "pilot",
        "--run-id",
        run_id,
        "--output-dir",
        str(output_root),
        "--seed",
        str(seed),
    ]


def _record(
    run_id,
    output_root,
    *,
    seed=601,
    design=None,
    fidelity="longitudinal",
    model="qwen3:8b",
    source_commit=COMMIT,
):
    design = design or {"acceptance_rate": 0.3}
    return {
        "run_id": run_id,
        "study_id": "arm",
        "study_revision": "revision",
        "design_id": "d-shared" if design == {"acceptance_rate": 0.3} else "d-other",
        "design_json": canonical_json(design),
        "sampler": "adaptive_random_search",
        "fidelity": fidelity,
        "seed_role": "optimization",
        "seed": seed,
        "max_attempts": 2,
        "command_json": canonical_json(
            _command(run_id, output_root, seed=seed, model=model)
        ),
        "output_root": str(output_root),
        "created_utc": "2026-10-28T00:00:00+00:00",
        "source_commit": source_commit,
    }


def _write_raw_artifact(root, run_id, *, seed=601, model="qwen3:8b", commit=COMMIT):
    docs = root / "docs" / run_id
    checkpoints = root / "checkpoints" / run_id
    logs = root / "logs" / run_id
    registry_logs = root / "registry-logs" / run_id
    docs.mkdir(parents=True)
    checkpoints.mkdir(parents=True)
    logs.mkdir(parents=True)
    registry_logs.mkdir(parents=True)
    (docs / "run_manifest.json").write_text(json.dumps({
        "status": "complete",
        "years_completed": 1,
        "experiment_id": run_id,
        "git_commit": commit,
        "args": {
            "seed": seed,
            "model": model,
            "api_backend": "ollama",
            "num_years": 1,
            "output_dir": str(checkpoints),
        },
    }))
    (docs / "integrity_checks.json").write_text(json.dumps([
        {"year": 1, "passed": True, "failures": []}
    ]))
    (checkpoints / "checkpoint_year_1.json").write_text(
        json.dumps({"year": 1, "phase": 5, "payload": "sealed"})
    )
    (logs / "simulation.log").write_text("complete\n")
    (registry_logs / "attempt-1.log").write_text("complete\n")


def _mark_executed(registry, record, *, status="complete", scheduler_suffix=""):
    if not registry.rows("run_id=?", (record["run_id"],)):
        assert registry.add(record)
    scheduler_id = "scheduler-" + record["run_id"] + scheduler_suffix
    registry.start_scheduler(scheduler_id, workers=1, recovered_runs=0)
    row = registry.start(record["run_id"])
    attempt_log = (
        Path(record["output_root"])
        / "registry-logs"
        / record["run_id"]
        / f"attempt-{row['attempt']}.log"
    )
    registry.attach_scheduler_attempt(
        row,
        scheduler_id=scheduler_id,
        worker_slot=0,
        workers=1,
        stdout_path=attempt_log,
        stderr_path=attempt_log,
        run_output_root=Path(record["output_root"]) / "checkpoints" / record["run_id"],
        cache_root=None,
        effective_command=json.loads(record["command_json"]),
    )
    registry.finish(
        record["run_id"],
        status=status,
        returncode=0 if status == "complete" else 1,
        wall_seconds=12.0,
        error=None if status == "complete" else "failed",
    )
    registry.finish_scheduler(scheduler_id, status="complete")


def _pair(tmp_path, *, target_kwargs=None, source_status="complete"):
    source_root = tmp_path / "source-output"
    target_root = tmp_path / "target-output"
    source_record = _record("source-run", source_root)
    target_record = _record("target-run", target_root, **(target_kwargs or {}))
    source = RunRegistry(tmp_path / "source.sqlite3")
    target = RunRegistry(tmp_path / "target.sqlite3")
    _mark_executed(source, source_record, status=source_status)
    if source_status == "complete":
        _write_raw_artifact(source_root, "source-run")
    assert target.add(target_record)
    return source, target, source_record, target_record


def test_adoption_is_transactional_idempotent_and_read_only(tmp_path):
    source, target, source_record, target_record = _pair(tmp_path)
    try:
        first = target.adopt_artifact(
            "target-run", source_registry_path=source.path, source_run="source-run"
        )
        second = target.adopt_artifact(
            "target-run", source_registry_path=source.path, source_run="source-run"
        )
        target_row = target.rows("run_id='target-run'")[0]
        resolved = target.resolve_artifact(target_row)

        assert first["adopted"] is True
        assert second["idempotent"] is True
        assert target_row["status"] == "complete" and target_row["attempt"] == 0
        assert target.attempt_rows() == []
        assert resolved.mode == "adopted"
        assert resolved.physical_run_id == "source-run"
        assert resolved.physical_output_root == Path(source_record["output_root"])
        assert receipt_path(resolved.physical_output_root, "source-run").is_file()
    finally:
        source.close()
        target.close()


def test_registry_rejects_reusing_run_id_with_different_execution_inputs(tmp_path):
    registry = RunRegistry(tmp_path / "runs.sqlite3")
    try:
        first = _record("same-run", tmp_path / "output")
        assert registry.add(first)
        with pytest.raises(ValueError, match="different execution inputs"):
            registry.add(_record("same-run", tmp_path / "output", seed=607))
        assert registry.validated_execution_identity(
            registry.rows("run_id='same-run'")[0]
        )
    finally:
        registry.close()


@pytest.mark.parametrize(
    "target_kwargs",
    [
        {"seed": 607},
        {"design": {"acceptance_rate": 0.5}},
        {"fidelity": "smoke"},
        {"model": "qwen3:14b"},
        {"source_commit": "b" * 40},
    ],
    ids=["wrong-seed", "wrong-design", "wrong-fidelity", "wrong-model", "wrong-commit"],
)
def test_adoption_rejects_execution_identity_mismatch(tmp_path, target_kwargs):
    source, target, _, _ = _pair(tmp_path, target_kwargs=target_kwargs)
    try:
        with pytest.raises(ValueError, match="execution identities differ"):
            target.adopt_artifact(
                "target-run", source_registry_path=source.path, source_run="source-run"
            )
        row = target.rows("run_id='target-run'")[0]
        assert row["status"] == "planned" and row["attempt"] == 0
        assert target.artifact_link_rows() == []
    finally:
        source.close()
        target.close()


def test_adoption_rejects_failed_source(tmp_path):
    source, target, _, _ = _pair(tmp_path, source_status="failed")
    try:
        with pytest.raises(ValueError, match="terminal complete and executed"):
            target.adopt_artifact(
                "target-run", source_registry_path=source.path, source_run="source-run"
            )
    finally:
        source.close()
        target.close()


@pytest.mark.parametrize("field,value", [("git_commit", "b" * 40), ("model", "qwen3:14b")])
def test_seal_rejects_manifest_identity_mismatch(tmp_path, field, value):
    source, target, source_record, _ = _pair(tmp_path)
    try:
        manifest_path = (
            Path(source_record["output_root"])
            / "docs"
            / "source-run"
            / "run_manifest.json"
        )
        manifest = json.loads(manifest_path.read_text())
        if field == "git_commit":
            manifest[field] = value
        else:
            manifest["args"][field] = value
        manifest_path.write_text(json.dumps(manifest))
        expected = f"source manifest {field.replace('git_commit', 'commit')}"
        with pytest.raises(ValueError, match=expected):
            source.seal_artifact("source-run")
    finally:
        source.close()
        target.close()


def test_adoption_rejects_target_with_attempt(tmp_path):
    source, target, _, _ = _pair(tmp_path)
    try:
        target.start("target-run")
        with pytest.raises(ValueError, match="planned with zero attempts"):
            target.adopt_artifact(
                "target-run", source_registry_path=source.path, source_run="source-run"
            )
        assert target.artifact_link_rows() == []
    finally:
        source.close()
        target.close()


def test_seal_rejects_symlink(tmp_path):
    source, target, source_record, _ = _pair(tmp_path)
    try:
        raw = Path(source_record["output_root"]) / "checkpoints" / "source-run"
        (raw / "linked.json").symlink_to(raw / "checkpoint_year_1.json")
        with pytest.raises(ValueError, match="symlink is forbidden"):
            source.seal_artifact("source-run")
    finally:
        source.close()
        target.close()


@pytest.mark.parametrize("mutation", ["tamper", "missing", "extra"])
def test_resolver_rejects_changed_or_partial_bundle(tmp_path, mutation):
    source, target, source_record, _ = _pair(tmp_path)
    try:
        target.adopt_artifact(
            "target-run", source_registry_path=source.path, source_run="source-run"
        )
        checkpoint = (
            Path(source_record["output_root"])
            / "checkpoints"
            / "source-run"
            / "checkpoint_year_1.json"
        )
        if mutation == "tamper":
            checkpoint.write_text("tampered")
        elif mutation == "missing":
            checkpoint.unlink()
        else:
            checkpoint.with_name("unexpected.json").write_text("extra")
        with pytest.raises(ValueError, match="missing, changed, or has extra files"):
            target.resolve_artifact(target.rows("run_id='target-run'")[0])
    finally:
        source.close()
        target.close()


def test_resolver_rejects_tampered_artifact_link(tmp_path):
    source, target, _, _ = _pair(tmp_path)
    try:
        target.adopt_artifact(
            "target-run", source_registry_path=source.path, source_run="source-run"
        )
        target.connection.execute(
            "UPDATE artifact_links SET source_registry_path=? WHERE logical_run_id=?",
            (str(tmp_path / "forged.sqlite3"), "target-run"),
        )
        target.connection.commit()
        with pytest.raises(ValueError, match="source registry is inconsistent"):
            target.resolve_artifact(target.rows("run_id='target-run'")[0])
    finally:
        source.close()
        target.close()


def test_build_report_reads_physical_and_writes_derived_only_to_logical(tmp_path, monkeypatch):
    source, target, source_record, target_record = _pair(tmp_path)
    try:
        target.adopt_artifact(
            "target-run", source_registry_path=source.path, source_run="source-run"
        )
        seen = {}

        def fake_evaluate_run(*, run_id, output_root, constitution):
            seen["evaluate"] = (run_id, Path(output_root))
            return {
                "run_id": run_id,
                "metrics": {},
                "comparison_eligibility": "feasible",
            }

        def fake_summary(run_id, output_root):
            seen["summary"] = (run_id, Path(output_root))
            return ({
                "annual": [{
                    "cumulative_unique_papers": 2,
                    "cumulative_accepted_papers": 1,
                    "active_researchers": 10,
                    "total_resources": 100.0,
                }],
                "total_reviews": 4,
            }, {}, {}, {})

        monkeypatch.setattr(harness, "evaluate_run", fake_evaluate_run)
        monkeypatch.setattr("utopia.analysis.release.summarize_run", fake_summary)
        report = build_report(target, constitution={
            "metric_registry": [], "layers": {"commitments": []}
        })

        source_root = Path(source_record["output_root"])
        target_root = Path(target_record["output_root"])
        assert seen["evaluate"] == ("source-run", source_root)
        assert seen["summary"] == ("source-run", source_root)
        assert not (source_root / "docs" / "source-run" / "objective_evaluation.json").exists()
        logical_evaluation = target_root / "docs" / "target-run" / "objective_evaluation.json"
        assert logical_evaluation.is_file()
        saved = json.loads(logical_evaluation.read_text())
        assert saved["run_id"] == "target-run"
        assert saved["artifact_provenance"]["physical_run_id"] == "source-run"
        assert report["artifact_provenance_counts"] == {"executed": 0, "adopted": 1}
        assert report["completed_runs"][0]["execution_mode"] == "adopted"
    finally:
        source.close()
        target.close()


def test_metric_conditioned_study_adopts_identical_initial_batch(tmp_path):
    manifest = json.loads((
        ROOT / "research/specs/metric-conditioned-optimization-study-v1.json"
    ).read_text())
    campaign_paths = []
    for index, relative in enumerate(manifest["campaigns"]):
        campaign = json.loads((ROOT / relative).read_text())
        campaign["study_template"] = str(ROOT / campaign["study_template"])
        campaign["loss_spec"] = str(ROOT / campaign["loss_spec"])
        campaign["execution"]["output_root"] = str(tmp_path / "outputs")
        campaign["execution"]["require_clean_worktree"] = False
        path = tmp_path / f"campaign-{index}.json"
        path.write_text(json.dumps(campaign))
        campaign_paths.append(str(path))
    manifest["campaigns"] = campaign_paths
    manifest_path = tmp_path / "study.json"
    manifest_path.write_text(json.dumps(manifest))

    study = MetricConditionedStudy(manifest_path)
    study.initialize()
    study.suggest_initial()
    canonical = study.campaigns[0]
    registry = RunRegistry(canonical.paths.registry)
    try:
        for row in registry.rows():
            record = dict(row)
            _mark_executed(registry, record)
            identity = json.loads(
                registry.execution_identity_row(row["run_id"])["identity_json"]
            )
            _write_raw_artifact(
                Path(row["output_root"]),
                row["run_id"],
                seed=row["seed"],
                model=identity["model"],
                commit=identity["producer_source_commit"],
            )
    finally:
        registry.close()

    first = study.adopt_initial(canonical.spec["id"])
    second = study.adopt_initial(canonical.spec["id"])

    assert first["logical_runs_adopted"] == 18
    assert second["logical_runs_adopted"] == 0
    assert second["logical_runs_idempotent"] == 18
    for target in study.campaigns[1:]:
        target_registry = RunRegistry(target.paths.registry)
        try:
            assert len(target_registry.artifact_link_rows()) == 9
            assert {row["status"] for row in target_registry.rows()} == {"complete"}
            assert {row["attempt"] for row in target_registry.rows()} == {0}
        finally:
            target_registry.close()


def test_metric_conditioned_study_skips_terminal_failed_initial_source(tmp_path):
    manifest = json.loads((
        ROOT / "research/specs/metric-conditioned-optimization-study-v1.json"
    ).read_text())
    campaign_paths = []
    for index, relative in enumerate(manifest["campaigns"]):
        campaign = json.loads((ROOT / relative).read_text())
        campaign["study_template"] = str(ROOT / campaign["study_template"])
        campaign["loss_spec"] = str(ROOT / campaign["loss_spec"])
        campaign["execution"]["output_root"] = str(tmp_path / "outputs")
        campaign["execution"]["require_clean_worktree"] = False
        path = tmp_path / f"campaign-{index}.json"
        path.write_text(json.dumps(campaign))
        campaign_paths.append(str(path))
    manifest["campaigns"] = campaign_paths
    manifest_path = tmp_path / "study.json"
    manifest_path.write_text(json.dumps(manifest))

    study = MetricConditionedStudy(manifest_path)
    study.initialize()
    study.suggest_initial()
    canonical = study.campaigns[0]
    registry = RunRegistry(canonical.paths.registry)
    try:
        rows = registry.rows()
        failed = rows[0]
        for row in rows:
            record = dict(row)
            if row["run_id"] == failed["run_id"]:
                _mark_executed(
                    registry, record, status="failed", scheduler_suffix="-first"
                )
                _mark_executed(
                    registry, record, status="failed", scheduler_suffix="-second"
                )
                continue
            _mark_executed(registry, record)
            identity = json.loads(
                registry.execution_identity_row(row["run_id"])["identity_json"]
            )
            _write_raw_artifact(
                Path(row["output_root"]),
                row["run_id"],
                seed=row["seed"],
                model=identity["model"],
                commit=identity["producer_source_commit"],
            )
    finally:
        registry.close()

    first = study.adopt_initial(canonical.spec["id"])
    second = study.adopt_initial(canonical.spec["id"])

    assert first["logical_runs_adopted"] == 16
    assert first["logical_runs_skipped_terminal_failed"] == 2
    assert second["logical_runs_adopted"] == 0
    assert second["logical_runs_idempotent"] == 16
    assert second["logical_runs_skipped_terminal_failed"] == 2
    for target in study.campaigns[1:]:
        skipped = first["skipped_terminal_failed"][target.spec["id"]]
        assert len(skipped) == 1
        assert skipped[0]["source_run_id"] == failed["run_id"]
        assert skipped[0]["reason"] == "source_has_no_complete_physical_bundle"
        target_registry = RunRegistry(target.paths.registry)
        try:
            assert len(target_registry.artifact_link_rows()) == 8
            assert len(target_registry.rows("status='complete'")) == 8
            planned = target_registry.rows("status='planned'")
            assert len(planned) == 1
            assert planned[0]["attempt"] == 0
            assert planned[0]["design_id"] == failed["design_id"]
            assert planned[0]["seed"] == failed["seed"]
            assert target_registry.attempt_rows() == []
        finally:
            target_registry.close()


def test_metric_conditioned_study_preflights_nonterminal_sources(tmp_path):
    manifest = json.loads((
        ROOT / "research/specs/metric-conditioned-optimization-study-v1.json"
    ).read_text())
    campaign_paths = []
    for index, relative in enumerate(manifest["campaigns"]):
        campaign = json.loads((ROOT / relative).read_text())
        campaign["study_template"] = str(ROOT / campaign["study_template"])
        campaign["loss_spec"] = str(ROOT / campaign["loss_spec"])
        campaign["execution"]["output_root"] = str(tmp_path / "outputs")
        campaign["execution"]["require_clean_worktree"] = False
        path = tmp_path / f"campaign-{index}.json"
        path.write_text(json.dumps(campaign))
        campaign_paths.append(str(path))
    manifest["campaigns"] = campaign_paths
    manifest_path = tmp_path / "study.json"
    manifest_path.write_text(json.dumps(manifest))

    study = MetricConditionedStudy(manifest_path)
    study.initialize()
    study.suggest_initial()
    canonical = study.campaigns[0]
    registry = RunRegistry(canonical.paths.registry)
    try:
        row = registry.rows()[0]
        _mark_executed(registry, dict(row))
        identity = json.loads(
            registry.execution_identity_row(row["run_id"])["identity_json"]
        )
        _write_raw_artifact(
            Path(row["output_root"]),
            row["run_id"],
            seed=row["seed"],
            model=identity["model"],
            commit=identity["producer_source_commit"],
        )
    finally:
        registry.close()

    with pytest.raises(RuntimeError, match="canonical initial sources are not terminal"):
        study.adopt_initial(canonical.spec["id"])
    for target in study.campaigns[1:]:
        target_registry = RunRegistry(target.paths.registry)
        try:
            assert target_registry.artifact_link_rows() == []
            assert {row["status"] for row in target_registry.rows()} == {"planned"}
        finally:
            target_registry.close()
