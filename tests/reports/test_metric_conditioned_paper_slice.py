import copy
import json
from pathlib import Path
import sqlite3
import statistics

import pytest

from scripts.figures.metric_conditioned_results import SYNTHETIC
from scripts.reports.metric_conditioned_paper_slice import (
    PAPER_OUTPUT,
    SLICE_SCHEMA,
    build_slice,
    main,
    write_outputs,
)
from scripts.reports.metric_conditioned_heldout_release import (
    probe_readiness,
    publish,
)
from utopia.optimization.harness import digest
from utopia.optimization.metric_conditioned_analysis import build_analyses
from utopia.optimization.metric_conditioned_study import (
    EVALUATION_SNAPSHOT_SCHEMA,
    FREEZE_SCHEMA,
    REPORT_SCHEMA,
    STUDY_SCHEMA,
)
from utopia.optimization.loss import loss_spec_sha256


ARMS = (
    "metric-conditioned-participation-review-v1-1",
    "metric-conditioned-topic-diversity-v1-1",
    "metric-conditioned-review-burden-v1-1",
)
LOSSES = (
    "participation-review-tradeoff-probe",
    "topic-diversity-probe",
    "review-burden-probe",
)
OPTIMIZATION_SEEDS = [601, 607, 617]
HELD_OUT_SEEDS = [701, 709, 719, 727, 733]
SOURCE_COMMIT = "a" * 40


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _registry(path, rows, adopted=()):
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY, status TEXT, wall_seconds REAL,
            source_commit TEXT, attempt INTEGER, max_attempts INTEGER
        );
        CREATE TABLE attempts (
            run_id TEXT, attempt INTEGER, status TEXT, wall_seconds REAL
        );
        CREATE TABLE artifact_links (
            logical_run_id TEXT PRIMARY KEY
        );
    """)
    adopted = set(adopted)
    for run_id in rows:
        physical = run_id not in adopted
        connection.execute(
            "INSERT INTO runs VALUES (?, 'complete', ?, ?, 1, 2)",
            (run_id, 100.0 if physical else None, SOURCE_COMMIT),
        )
        if physical:
            connection.execute(
                "INSERT INTO attempts VALUES (?, 1, 'complete', 100.0)",
                (run_id,),
            )
        else:
            connection.execute("INSERT INTO artifact_links VALUES (?)", (run_id,))
    connection.commit()
    connection.close()


def _profile(metric_id, direction, base, *, slice_id=None):
    values = [base - 0.02, base - 0.01, base, base + 0.01, base + 0.02]
    return {
        "id": metric_id,
        "slice": slice_id,
        "direction": direction,
        "seed_values": [
            {
                "seed": seed,
                "status": "measured",
                "metric_version": "synthetic-test-only",
                "value": value,
                "missing_reason": None,
            }
            for seed, value in zip(HELD_OUT_SEEDS, values)
        ],
        "summary": {
            "n": 5,
            "mean": base,
            "median": base,
            "population_sd": 0.01414213562373095,
            "min": base - 0.02,
            "max": base + 0.02,
        },
        "structured_summary": {},
        "complete": True,
    }


def _loss(base, *, own, arm_index):
    values = [base - 0.02, base - 0.01, base, base + 0.01, base + 0.02]
    return {
        "status": "complete",
        "loss": statistics.fmean(values) + 0.25 * statistics.pstdev(values),
        "is_own_loss": own,
        "held_out_seed_values": [
            {"seed": seed, "run_id": f"held-{arm_index}-{seed}", "loss": value, "missing_reason": None}
            for seed, value in zip(HELD_OUT_SEEDS, values)
        ],
        "rejected_runs": [],
    }


def _fixture(tmp_path):
    specs_dir = tmp_path / "specs"
    campaign_specs = {}
    loss_specs = {}
    campaign_paths = []
    for arm in ARMS:
        loss_id = LOSSES[ARMS.index(arm)]
        loss_path = specs_dir / f"{loss_id}.json"
        loss_spec = {
            "schema": "scienceutopia.loss-spec.v1",
            "id": loss_id,
            "version": "synthetic-test-only",
            "across_seeds": {
                "aggregation": "mean_plus_population_sd",
                "dispersion_weight": 0.25,
                "minimum_valid_runs": 3,
            },
        }
        _write_json(loss_path, loss_spec)
        loss_specs[loss_id] = loss_spec
        spec = {
            "schema": "scienceutopia.closed-loop-campaign.v1",
            "id": arm,
            "version": "synthetic-test-only",
            "study_template": "synthetic-study-template.json",
            "loss_spec": str(loss_path),
            "fidelity": "synthetic-test-only",
            "seed_sets": {
                "optimization": OPTIMIZATION_SEEDS,
                "held_out_evaluation": HELD_OUT_SEEDS,
            },
            "optimizer": {
                "kind": "adaptive_random_search",
                "seed": 20261028,
                "initial_random": 3,
                "mutation_scale": 0.2,
            },
            "budget": {"max_suggestions": 5, "initial_batch": 3, "adaptive_batch": 1},
            "execution": {
                "workers": 1,
                "output_root": "synthetic-test-only",
                "require_clean_worktree": True,
            },
        }
        path = specs_dir / f"{arm}.json"
        _write_json(path, spec)
        campaign_specs[arm] = spec
        campaign_paths.append(str(path))
    suite = [
        {"id": "active-researcher-fraction", "role": "evaluation_metric", "direction": "maximize", "slice": None},
        {"id": "active-researcher-fraction", "role": "evaluation_metric", "direction": "maximize", "slice": "low-resource-researchers"},
        {"id": "topic-entropy", "role": "evaluation_metric", "direction": "observe", "slice": None},
        {"id": "review-burden-per-active-researcher", "role": "evaluation_metric", "direction": "minimize", "slice": None},
        {"id": "review-coverage", "role": "shadow_diagnostic", "direction": "observe", "slice": None},
        {"id": "submission-count", "role": "shadow_diagnostic", "direction": "observe", "slice": None},
        {"id": "accepted-paper-count", "role": "shadow_diagnostic", "direction": "observe", "slice": None},
    ]
    manifest = {
        "schema": STUDY_SCHEMA,
        "id": "synthetic-metric-conditioned-v1-1",
        "version": "synthetic-test-only",
        "campaigns": campaign_paths,
        "common_optimization_seeds": OPTIMIZATION_SEEDS,
        "common_held_out_evaluation_seeds": HELD_OUT_SEEDS,
        "held_out_metric_suite": suite,
        "held_out_evaluator": {
            "id": "synthetic-held-out-evaluator",
            "version": "synthetic-test-only",
            "spec": "synthetic-test-only",
        },
        "decision_policy": "report_only",
    }
    manifest_path = tmp_path / "manifest.json"
    _write_json(manifest_path, manifest)

    campaign_roots = {}
    winners = []
    states = {}
    for arm_index, arm in enumerate(ARMS):
        root = tmp_path / "campaigns" / arm
        root.mkdir(parents=True)
        revision = f"revision-{arm_index}"
        suggestions = []
        for proposal in range(5):
            loss = 0.8 - 0.1 * proposal + 0.03 * arm_index
            suggestions.append({
                "suggestion": {
                    "suggestion_id": f"synthetic-{arm}-{proposal}",
                    "proposal_index": proposal,
                    "phase": "initial" if proposal < 3 else "adaptive",
                },
                "source_candidate": {
                    "acceptance_rate": 0.2 + arm_index * 0.1,
                    "reviews_per_paper": 2 + arm_index,
                    "reviewer_capacity": 4,
                    "reviewer_matching": ("random", "topic", "random")[arm_index],
                    "review_policy": "persona",
                    "funding_budget_slots_frac": 0.3 + arm_index * 0.1,
                    "funding_application_cost": arm_index,
                    "resubmission_cost": 5.0,
                },
                "design_id": f"synthetic-design-{arm_index}-{proposal}",
                "system_fingerprint": f"synthetic-fingerprint-{arm_index}-{proposal}",
                "status": "observed_complete",
                "observation": {"loss": loss},
            })
        state = {
            "schema": "scienceutopia.closed-loop-state.v1",
            "campaign_id": arm,
            "revision": revision,
            "suggestions": suggestions,
        }
        snapshot = {
            "schema": "scienceutopia.closed-loop-snapshot.v1",
            "revision": revision,
            "campaign": campaign_specs[arm],
            "loss_spec": loss_specs[LOSSES[arm_index]],
            "source": {"commit": SOURCE_COMMIT, "tree_dirty": False, "dirty_paths": []},
        }
        _write_json(root / "campaign-state.json", state)
        _write_json(root / "campaign-snapshot.json", snapshot)
        run_ids = [f"{arm}-s{proposal}-seed{seed}" for proposal in range(5) for seed in OPTIMIZATION_SEEDS]
        adopted = run_ids[:9] if arm_index else []
        _registry(root / "runs.sqlite3", run_ids, adopted)
        winner = suggestions[-1]
        winners.append({
            "campaign_id": arm,
            "campaign_revision": revision,
            "loss_spec": {
                "id": LOSSES[arm_index],
                "version": "synthetic",
                "sha256": loss_spec_sha256(loss_specs[LOSSES[arm_index]]),
            },
            "suggestion_id": winner["suggestion"]["suggestion_id"],
            "proposal_index": winner["suggestion"]["proposal_index"],
            "design_id": winner["design_id"],
            "system_fingerprint": winner["system_fingerprint"],
            "source_candidate": winner["source_candidate"],
            "optimization_observation": winner["observation"],
        })
        states[arm] = state
        campaign_roots[arm] = root

    study_root = tmp_path / "study"
    evaluation_root = study_root / "held-out-evaluation"
    evaluation_root.mkdir(parents=True)
    freeze = {
        "schema": FREEZE_SCHEMA,
        "study_id": manifest["id"],
        "study_revision": "synthetic-study-revision",
        "source_commit": SOURCE_COMMIT,
        "frozen_utc": "synthetic-test-only",
        "decision_policy": "report_only",
        "optimization_seeds": OPTIMIZATION_SEEDS,
        "held_out_seeds_unconsumed_at_freeze": HELD_OUT_SEEDS,
        "winners": winners,
    }
    immutable = dict(freeze)
    immutable.pop("frozen_utc")
    freeze["freeze_sha256"] = digest(immutable, length=64)
    _write_json(study_root / "winner-freeze.json", freeze)

    held_runs = [
        {
            "run_id": f"held-{arm_index}-{seed}",
            "campaign_id": arm,
            "loss_spec_id": LOSSES[arm_index],
            "design_id": winners[arm_index]["design_id"],
            "seed": seed,
        }
        for arm_index, arm in enumerate(ARMS)
        for seed in HELD_OUT_SEEDS
    ]
    evaluation_snapshot = {
        "schema": EVALUATION_SNAPSHOT_SCHEMA,
        "study_id": manifest["id"],
        "study_revision": freeze["study_revision"],
        "winner_freeze_sha256": freeze["freeze_sha256"],
        "held_out_seeds": HELD_OUT_SEEDS,
        "metric_suite": suite,
        "held_out_evaluator": manifest["held_out_evaluator"],
        "runs": held_runs,
    }
    _write_json(evaluation_root / "snapshot.json", evaluation_snapshot)
    _registry(evaluation_root / "runs.sqlite3", [item["run_id"] for item in held_runs])

    loss_bases = {
        ARMS[0]: (0.40, 0.80, 0.90),
        ARMS[1]: (0.60, 0.30, 1.00),
        ARMS[2]: (0.50, 0.70, 0.20),
    }
    losses = {
        arm: {
            loss_id: _loss(
                base,
                own=loss_id == LOSSES[ARMS.index(arm)],
                arm_index=ARMS.index(arm),
            )
            for loss_id, base in zip(LOSSES, loss_bases[arm])
        }
        for arm in ARMS
    }
    profiles = {}
    for arm_index, arm in enumerate(ARMS):
        profiles[arm] = [
            _profile("active-researcher-fraction", "maximize", 0.8 - 0.1 * arm_index),
            _profile("active-researcher-fraction", "maximize", 0.6 - 0.03 * arm_index, slice_id="low-resource-researchers"),
            _profile("topic-entropy", "observe", 1.0 + 0.3 * (arm_index == 1)),
            _profile("review-burden-per-active-researcher", "minimize", (1.0, 1.2, 0.5)[arm_index]),
            _profile("review-coverage", "observe", (0.9, 0.8, 0.5)[arm_index]),
            _profile("submission-count", "observe", 10 - arm_index),
            _profile("accepted-paper-count", "observe", 3 - 0.5 * arm_index),
        ]
    analyses = build_analyses(freeze=freeze, profiles=profiles, losses=losses)
    report = {
        "schema": REPORT_SCHEMA,
        "study_id": manifest["id"],
        "study_revision": freeze["study_revision"],
        "winner_freeze_sha256": freeze["freeze_sha256"],
        "decision_policy": "report_only",
        "provenance": {"data_classification": SYNTHETIC},
        "loss_by_frozen_winner": losses,
        "held_out_metric_profiles": profiles,
        "common_run_evaluations": {
            item["run_id"]: {"run_id": item["run_id"], "metrics": {}}
            for item in held_runs
        },
        "analyses": analyses,
        "raw_registry_report": {"report_errors": []},
    }
    _write_json(evaluation_root / "cross-evaluation.json", report)
    return {
        "manifest_path": manifest_path,
        "study_root": study_root,
        "campaign_roots": campaign_roots,
        "report_path": evaluation_root / "cross-evaluation.json",
    }


def _build(fixture):
    return build_slice(
        manifest_path=fixture["manifest_path"],
        study_root=fixture["study_root"],
        campaign_roots=fixture["campaign_roots"],
        classification=SYNTHETIC,
    )


def test_build_slice_validates_and_summarizes_complete_study(tmp_path):
    fixture = _fixture(tmp_path)
    result, figure = _build(fixture)

    assert result["schema"] == SLICE_SCHEMA
    assert result["conclusions"]["distinct_frozen_designs"] == 3
    assert result["conclusions"]["rank_reversal_across_losses"] is True
    assert result["runtime"]["logical_optimization_runs"] == 45
    assert result["runtime"]["physical_optimization_runs"] == 27
    assert result["runtime"]["adopted_optimization_runs"] == 18
    assert result["runtime"]["held_out_evaluation"]["logical_runs"] == 15
    assert all(
        item["n"] == 5
        for arm in ARMS
        for item in result["cross_objective_uncertainty"][arm].values()
    )
    own = result["cross_objective_uncertainty"][ARMS[0]][LOSSES[0]]
    assert own["bootstrap_resamples"] == 3125
    assert own["method"].startswith("exact_nonparametric_bootstrap")
    assert own["estimate"] > own["per_seed_mean"]
    assert [item["label"] for item in figure["arms"]] == [
        "Participation-review", "Topic-entropy proxy", "Review-burden proxy"
    ]
    assert "uncertainty" in figure["cross_evaluation"]


def test_atomic_output_contains_tables_figures_reports_and_manifest(tmp_path):
    fixture = _fixture(tmp_path / "input")
    result, figure = _build(fixture)
    output = tmp_path / "published"

    paths = write_outputs(result, figure, output, formats=("png",))

    assert paths
    expected = {
        "metric-conditioned-paper-slice.json",
        "metric-conditioned-figure-data.json",
        "cross-objective-losses.csv",
        "held-out-metrics.csv",
        "paired-effects.csv",
        "winner-designs.csv",
        "runtime-summary.csv",
        "metric-conditioned-results.generated.md",
        "metric-conditioned-results.generated.tex",
        "artifact-manifest.json",
    }
    assert expected.issubset({path.name for path in output.iterdir()})
    assert len(list((output / "figures").glob("*.png"))) == 3
    markdown = (output / "metric-conditioned-results.generated.md").read_text()
    tex = (output / "metric-conditioned-results.generated.tex").read_text()
    assert "3 distinct frozen institutional designs" in markdown
    assert "rank reversal" in markdown
    assert "Institutional parameters" in markdown
    assert "metric-conditioned-designs" in tex
    manifest = json.loads((output / "artifact-manifest.json").read_text())
    assert manifest["artifacts"]
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_outputs(result, figure, output, formats=("png",))


def test_fail_closed_on_missing_cross_objective_seed(tmp_path):
    fixture = _fixture(tmp_path)
    report = json.loads(fixture["report_path"].read_text())
    report["loss_by_frozen_winner"][ARMS[0]][LOSSES[0]][
        "held_out_seed_values"
    ].pop()
    _write_json(fixture["report_path"], report)

    with pytest.raises(ValueError, match="incomplete cross-evaluation cell"):
        _build(fixture)


def test_fail_closed_on_provenance_mismatch(tmp_path):
    fixture = _fixture(tmp_path)
    snapshot_path = fixture["campaign_roots"][ARMS[1]] / "campaign-snapshot.json"
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["source"]["commit"] = "c" * 40
    _write_json(snapshot_path, snapshot)

    with pytest.raises(ValueError, match="different source commits"):
        _build(fixture)


def test_fail_closed_when_arm_changes_controlled_optimizer(tmp_path):
    fixture = _fixture(tmp_path)
    manifest = json.loads(fixture["manifest_path"].read_text())
    changed_path = Path(manifest["campaigns"][1])
    changed = json.loads(changed_path.read_text())
    changed["optimizer"]["mutation_scale"] = 0.5
    _write_json(changed_path, changed)

    with pytest.raises(ValueError, match="controlled field optimizer"):
        _build(fixture)


def test_fail_closed_when_preregistered_analysis_is_tampered(tmp_path):
    fixture = _fixture(tmp_path)
    report = json.loads(fixture["report_path"].read_text())
    report["analyses"]["rank_reversal"]["columns"][f"loss:{LOSSES[0]}"][
        "raw_order"
    ].reverse()
    _write_json(fixture["report_path"], report)

    with pytest.raises(ValueError, match="do not match recomputed inputs"):
        _build(fixture)


def test_fail_closed_when_metric_summary_is_tampered(tmp_path):
    fixture = _fixture(tmp_path)
    report = json.loads(fixture["report_path"].read_text())
    report["held_out_metric_profiles"][ARMS[0]][0]["summary"]["mean"] += 0.1
    _write_json(fixture["report_path"], report)

    with pytest.raises(ValueError, match="summary mean is inconsistent"):
        _build(fixture)


def test_readiness_gate_does_not_open_report_before_all_runs_complete(tmp_path):
    fixture = _fixture(tmp_path)
    registry = fixture["study_root"] / "held-out-evaluation/runs.sqlite3"
    connection = sqlite3.connect(registry)
    connection.execute(
        "UPDATE runs SET status = 'planned', attempt = 0 WHERE run_id = ?",
        (f"held-0-{HELD_OUT_SEEDS[0]}",),
    )
    connection.commit()
    connection.close()
    fixture["report_path"].write_text("not-json", encoding="utf-8")

    readiness = probe_readiness(fixture["study_root"])
    assert readiness["ready_for_report"] is False
    assert readiness["value_files_read"] is False
    with pytest.raises(RuntimeError, match="refusing to read cross-evaluation"):
        publish(
            manifest_path=fixture["manifest_path"],
            study_root=fixture["study_root"],
            campaign_roots=fixture["campaign_roots"],
            output_dir=tmp_path / "must-not-exist",
            classification=SYNTHETIC,
            formats=("png",),
        )
    assert not (tmp_path / "must-not-exist").exists()


def test_readiness_gate_opens_only_after_complete_registry(tmp_path):
    fixture = _fixture(tmp_path)
    readiness = probe_readiness(fixture["study_root"])

    assert readiness["expected_runs"] == 15
    assert readiness["status_counts"] == {"complete": 15}
    assert readiness["ready_for_report"] is True
    assert readiness["ready_for_publication"] is True
    assert readiness["value_files_read"] is False


def test_synthetic_cli_cannot_publish_to_paper_destination():
    with pytest.raises(ValueError, match="may not be published"):
        main([
            "--manifest", "missing.json",
            "--study-root", "missing",
            "--campaign-root", "arm=missing",
            "--classification", "synthetic-test",
            "--output-dir", str(PAPER_OUTPUT),
            "--formats", "png",
        ])


def test_paper_boundary_requires_generated_fragment_and_all_figures():
    root = Path(__file__).resolve().parents[2]
    boundary = (root / "paper/metric_conditioned_results.tex").read_text()
    assert boundary.count("\\IfFileExists") == 4
    assert "generated/metric-conditioned/metric-conditioned-results.generated" in boundary
    assert "No synthetic fixture" in boundary
    assert "tests/fixtures" not in boundary


def test_methods_flow_keeps_four_contracts_and_firewall_visible():
    root = Path(__file__).resolve().parents[2]
    flow = (root / "paper/metric_conditioned_methods_flow.tex").read_text()
    paper = (root / "paper/main.tex").read_text()

    for label in ("LossSpec", "ValiditySpec", "held-out", "DecisionPolicy"):
        assert label in flow
    assert "simultaneous immutable winner freeze" in flow
    assert "metric_conditioned_methods_flow" in paper
