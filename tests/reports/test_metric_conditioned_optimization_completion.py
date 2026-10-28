import json
from pathlib import Path
import sqlite3

import matplotlib.image as mpimg
import pytest
import jsonschema

from scripts.reports.metric_conditioned_optimization_completion import (
    main as completion_main,
    write_package,
)
from utopia.optimization.harness import digest
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.optimization.metric_conditioned_completion import (
    REPORT_SCHEMA,
    build_optimization_completion_report,
)
from utopia.optimization.metric_conditioned_study import FREEZE_SCHEMA, STUDY_SCHEMA


ROOT = Path(__file__).resolve().parents[2]
ARMS = (
    "metric-conditioned-participation-review-v1-1",
    "metric-conditioned-topic-diversity-v1-1",
    "metric-conditioned-review-burden-v1-1",
)
LOSS_PATHS = (
    ROOT / "research/objectives/losses/participation-review-tradeoff-probe-v1.json",
    ROOT / "research/objectives/losses/topic-diversity-probe-v1.json",
    ROOT / "research/objectives/losses/review-burden-probe-v1.json",
)
DEV_SEEDS = [601, 607, 617]
HELD_OUT_SEEDS = [701, 709, 719, 727, 733]
SOURCE_COMMIT = "a" * 40


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _metric(metric_id, value):
    return {"metric_id": metric_id, "status": "measured", "value": value, "slice_results": {}}


def _evaluation(run_id, active, topic, burden):
    return {
        "run_id": run_id,
        "metrics": {
            "active-researcher-fraction": _metric("active-researcher-fraction", active),
            "topic-entropy": _metric("topic-entropy", topic),
            "review-burden-per-active-researcher": _metric(
                "review-burden-per-active-researcher", burden
            ),
        },
    }


def _registry(path, rows, adopted):
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY, seed INTEGER, seed_role TEXT, status TEXT,
            wall_seconds REAL
        );
        CREATE TABLE attempts (
            run_id TEXT, attempt INTEGER, status TEXT, wall_seconds REAL
        );
        CREATE TABLE artifact_links (
            logical_run_id TEXT PRIMARY KEY, source_registry_path TEXT,
            physical_run_id TEXT, physical_output_root TEXT,
            execution_identity_sha256 TEXT, bundle_receipt_path TEXT,
            bundle_receipt_sha256 TEXT, source_attempt INTEGER,
            source_attempt_provenance_sha256 TEXT, adopted_utc TEXT
        );
    """)
    for row in rows:
        is_adopted = row["run_id"] in adopted
        connection.execute(
            "INSERT INTO runs VALUES (?, ?, 'optimization', 'complete', ?)",
            (row["run_id"], row["seed"], None if is_adopted else 12.5),
        )
        if is_adopted:
            connection.execute(
                "INSERT INTO artifact_links VALUES (?, 'source.sqlite3', ?, '/synthetic', ?, "
                "'receipt.json', ?, 1, ?, 'synthetic')",
                (row["run_id"], f"physical-{row['run_id']}", "b" * 64, "c" * 64, "d" * 64),
            )
        else:
            connection.execute(
                "INSERT INTO attempts VALUES (?, 1, 'complete', 12.5)", (row["run_id"],)
            )
    connection.commit()
    connection.close()


def _fixture(tmp_path):
    losses = [json.loads(path.read_text(encoding="utf-8")) for path in LOSS_PATHS]
    specs = tmp_path / "specs"
    campaign_paths = []
    campaign_roots = {}
    winner_records = []

    for arm_index, (arm, loss) in enumerate(zip(ARMS, losses)):
        spec = {
            "id": arm,
            "study_template": "synthetic-test-template.json",
            "fidelity": "synthetic",
            "seed_sets": {
                "optimization": DEV_SEEDS,
                "held_out_evaluation": HELD_OUT_SEEDS,
            },
            "budget": {"max_suggestions": 5},
            "optimizer": {"kind": "adaptive_random_search", "seed": 1234},
            "execution": {"model": "synthetic-test-only", "api_backend": "none"},
        }
        spec_path = specs / f"{arm}.json"
        _write_json(spec_path, spec)
        campaign_paths.append(str(spec_path))

        root = tmp_path / "campaigns" / arm
        root.mkdir(parents=True)
        campaign_roots[arm] = root
        revision = f"synthetic-revision-{arm_index}"
        suggestions = []
        registry_rows = []
        objective_evaluations = []
        for proposal in range(5):
            run_ids = []
            for seed_index, seed in enumerate(DEV_SEEDS):
                run_id = f"{arm}-p{proposal}-s{seed}"
                run_ids.append(run_id)
                registry_rows.append({"run_id": run_id, "seed": seed})
                jitter = (seed_index - 1) * 0.01
                active = 0.50 + 0.08 * proposal + (0.10 if arm_index == 0 else 0) + jitter
                topic = 0.40 + 0.20 * proposal + (0.55 if arm_index == 1 else 0) + jitter
                burden = 1.80 - 0.20 * proposal - (0.55 if arm_index == 2 else 0) + jitter
                objective_evaluations.append(_evaluation(run_id, active, topic, burden))
            selected = [item for item in objective_evaluations if item["run_id"] in run_ids]
            observation = evaluate_loss(loss, selected)
            suggestions.append({
                "suggestion": {
                    "suggestion_id": f"synthetic-{arm}-p{proposal}",
                    "proposal_index": proposal,
                    "phase": "initial" if proposal < 3 else "adaptive",
                },
                "source_candidate": {
                    "acceptance_rate": 0.20 + 0.05 * proposal,
                    "reviews_per_paper": 2 + arm_index,
                    "reviewer_capacity": 3 + proposal,
                    "reviewer_matching": "topic" if arm_index == 1 else "random",
                    "review_policy": "persona",
                    "funding_budget_slots_frac": 0.30 + 0.05 * arm_index,
                    "funding_application_cost": float(arm_index),
                    "resubmission_cost": 5.0,
                },
                "design_id": f"synthetic-design-{arm_index}-{proposal}",
                "system_fingerprint": f"synthetic-fingerprint-{arm_index}-{proposal}",
                "run_ids": run_ids,
                "status": "observed_complete",
                "observation": {"loss": observation["loss"]},
            })
        state = {
            "schema": "scienceutopia.closed-loop-state.v1",
            "campaign_id": arm,
            "revision": revision,
            "suggestions": suggestions,
        }
        snapshot = {
            "schema": "scienceutopia.closed-loop-snapshot.v1",
            "campaign": spec,
            "loss_spec": loss,
            "source": {"commit": SOURCE_COMMIT, "tree_dirty": False, "dirty_paths": []},
        }
        _write_json(root / "campaign-state.json", state)
        _write_json(root / "campaign-snapshot.json", snapshot)
        adopted = {
            row["run_id"] for row in registry_rows
            if arm_index > 0
            and any(f"-p{proposal}-" in row["run_id"] for proposal in range(3))
        }
        _registry(root / "runs.sqlite3", registry_rows, adopted)
        connection = sqlite3.connect(root / "runs.sqlite3")
        connection.row_factory = sqlite3.Row
        artifact_links = [
            dict(row) for row in connection.execute(
                "SELECT * FROM artifact_links ORDER BY logical_run_id"
            )
        ]
        connection.close()
        _write_json(root / "reports" / "registry-report.json", {
            "total_runs": 15,
            "status_counts": {"complete": 15},
            "artifact_provenance_counts": {
                "executed": 15 - len(adopted),
                "adopted": len(adopted),
            },
            "artifact_links": artifact_links,
            "objective_evaluations": objective_evaluations,
            "report_errors": [],
        })
        winner = suggestions[-1]
        winner_records.append({
            "campaign_id": arm,
            "campaign_revision": revision,
            "loss_spec": {
                "id": loss["id"], "version": loss["version"],
                "sha256": loss_spec_sha256(loss),
            },
            "suggestion_id": winner["suggestion"]["suggestion_id"],
            "proposal_index": winner["suggestion"]["proposal_index"],
            "design_id": winner["design_id"],
            "system_fingerprint": winner["system_fingerprint"],
            "source_candidate": winner["source_candidate"],
            "optimization_observation": winner["observation"],
        })

    manifest = {
        "schema": STUDY_SCHEMA,
        "id": "synthetic-metric-conditioned-optimization-v1-1",
        "campaigns": campaign_paths,
        "common_optimization_seeds": DEV_SEEDS,
        "common_held_out_evaluation_seeds": HELD_OUT_SEEDS,
        "decision_policy": "report_only",
    }
    manifest_path = tmp_path / "manifest.json"
    _write_json(manifest_path, manifest)
    study_root = tmp_path / "study"
    freeze = {
        "schema": FREEZE_SCHEMA,
        "study_id": manifest["id"],
        "study_revision": "synthetic-study-revision",
        "source_commit": SOURCE_COMMIT,
        "frozen_utc": "synthetic-test-only",
        "decision_policy": "report_only",
        "optimization_seeds": DEV_SEEDS,
        "held_out_seeds_unconsumed_at_freeze": HELD_OUT_SEEDS,
        "winners": winner_records,
    }
    immutable = dict(freeze)
    immutable.pop("frozen_utc")
    freeze["freeze_sha256"] = digest(immutable, length=64)
    _write_json(study_root / "winner-freeze.json", freeze)
    return manifest_path, study_root, campaign_roots


def test_completion_report_cross_scores_45_runs_and_preserves_provenance(tmp_path):
    manifest, study_root, roots = _fixture(tmp_path)
    registry_bytes = {
        arm: (root / "runs.sqlite3").read_bytes() for arm, root in roots.items()
    }
    report = build_optimization_completion_report(
        manifest_path=manifest,
        study_root=study_root,
        campaign_roots=roots,
        classification="synthetic_test_fixture",
        repo_root=ROOT,
    )

    assert report["schema"] == REPORT_SCHEMA
    assert report["contract"] == {
        "arms": 3,
        "candidates_per_arm": 5,
        "development_seeds_per_candidate": 3,
        "logical_runs": 45,
        "distinct_losses": 3,
        "decision_policy": "report_only",
    }
    assert report["execution"]["executed_runs"] == 27
    assert report["execution"]["adopted_runs"] == 18
    assert report["evidence_boundary"]["held_out_consumed"] is False
    assert set(report["provenance"]["controlled_search_contract_sha256"]) == {
        "study_template", "fidelity", "seed_sets", "optimizer", "budget", "execution",
    }
    rankings = report["development_cross_objective"]["candidate_rankings"]
    assert len(rankings) == 3
    assert all(len(item["values"]) == 15 for item in rankings.values())
    assert report["development_cross_objective"]["winner_reversals"]
    assert all(
        candidate["cross_objective_losses"]
        for arm in report["arms"].values() for candidate in arm["candidates"]
    )
    assert registry_bytes == {
        arm: (root / "runs.sqlite3").read_bytes() for arm, root in roots.items()
    }
    schema = json.loads(
        (ROOT / "research/specs/metric-conditioned-optimization-completion-v1.schema.json")
        .read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(schema).validate(report)


def test_completion_refuses_any_held_out_planning_artifact(tmp_path):
    manifest, study_root, roots = _fixture(tmp_path)
    _write_json(study_root / "held-out-evaluation" / "snapshot.json", {"synthetic": True})

    with pytest.raises(ValueError, match="held-out evidence is already planned or consumed"):
        build_optimization_completion_report(
            manifest_path=manifest,
            study_root=study_root,
            campaign_roots=roots,
            classification="synthetic_test_fixture",
            repo_root=ROOT,
        )


def test_completion_refuses_missing_logical_run(tmp_path):
    manifest, study_root, roots = _fixture(tmp_path)
    registry = next(iter(roots.values())) / "runs.sqlite3"
    connection = sqlite3.connect(registry)
    connection.execute("DELETE FROM attempts WHERE run_id=(SELECT run_id FROM runs LIMIT 1)")
    connection.execute("DELETE FROM runs WHERE run_id=(SELECT run_id FROM runs LIMIT 1)")
    connection.commit()
    connection.close()

    with pytest.raises(ValueError, match="14 logical runs, expected 15"):
        build_optimization_completion_report(
            manifest_path=manifest,
            study_root=study_root,
            campaign_roots=roots,
            classification="synthetic_test_fixture",
            repo_root=ROOT,
        )


def test_completion_refuses_unprovenanced_executed_run(tmp_path):
    manifest, study_root, roots = _fixture(tmp_path)
    registry = next(iter(roots.values())) / "runs.sqlite3"
    connection = sqlite3.connect(registry)
    connection.execute("DELETE FROM attempts WHERE run_id=(SELECT run_id FROM runs LIMIT 1)")
    connection.commit()
    connection.close()

    with pytest.raises(ValueError, match="lacks a complete attempt"):
        build_optimization_completion_report(
            manifest_path=manifest,
            study_root=study_root,
            campaign_roots=roots,
            classification="synthetic_test_fixture",
            repo_root=ROOT,
        )


def test_completion_refuses_held_out_seed_in_arm_registry(tmp_path):
    manifest, study_root, roots = _fixture(tmp_path)
    registry = next(iter(roots.values())) / "runs.sqlite3"
    connection = sqlite3.connect(registry)
    connection.execute(
        "UPDATE runs SET seed=? WHERE run_id=(SELECT run_id FROM runs LIMIT 1)",
        (701,),
    )
    connection.commit()
    connection.close()

    with pytest.raises(ValueError, match="development seed firewall"):
        build_optimization_completion_report(
            manifest_path=manifest,
            study_root=study_root,
            campaign_roots=roots,
            classification="synthetic_test_fixture",
            repo_root=ROOT,
        )


def test_synthetic_end_to_end_package_is_watermarked_and_machine_readable(tmp_path):
    manifest, study_root, roots = _fixture(tmp_path)
    output = tmp_path / "package"
    arguments = [
        "--manifest", str(manifest),
        "--study-root", str(study_root),
    ]
    for arm, root in roots.items():
        arguments.extend(("--campaign-root", f"{arm}={root}"))
    arguments.extend((
        "--classification", "synthetic-test",
        "--output-dir", str(output),
        "--formats", "png",
    ))
    assert completion_main(arguments) == 0

    assert (output / "metric-conditioned-optimization-completion.json").exists()
    assert (output / "development-candidates.csv").read_text().count("\n") == 16
    assert (output / "development-cross-objective.csv").read_text().count("\n") == 10
    assert (output / "frozen-winner-systems.csv").read_text().count("\n") == 4
    assert (output / "artifact-manifest.json").exists()
    image = mpimg.imread(output / "figures/metric-conditioned-optimization-completion.png")
    top = image[: max(1, image.shape[0] // 8), :, :3]
    assert ((top[:, :, 0] > 0.45) & (top[:, :, 0] > top[:, :, 1] * 1.4)).any()
    markdown = (output / "metric-conditioned-optimization-completion.md").read_text()
    assert "Held-out seeds were verified unused" in markdown
    assert "does not select a universal" in markdown


def test_package_refuses_overwrite(tmp_path):
    manifest, study_root, roots = _fixture(tmp_path)
    report = build_optimization_completion_report(
        manifest_path=manifest,
        study_root=study_root,
        campaign_roots=roots,
        classification="synthetic_test_fixture",
        repo_root=ROOT,
    )
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError, match="refuse to overwrite"):
        write_package(report, output, formats=("png",))
