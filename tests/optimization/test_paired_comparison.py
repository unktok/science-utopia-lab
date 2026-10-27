import json
import sqlite3

import pytest

from utopia.optimization.paired_comparison import (
    bootstrap_mean_interval,
    build_paired_comparison,
    main,
    render_markdown,
    summarize_deltas,
)


def _write_campaign(
    root, *, label, funding_fraction, eligibility, seed_role="exploration",
    confirmation_policy=None,
):
    root.mkdir()
    run_id = f"{label}-s1"
    design = {
        "funding_budget_slots_frac": funding_fraction,
        "reviewer_capacity": 4,
    }
    connection = sqlite3.connect(root / "registry.sqlite3")
    connection.executescript("""
        CREATE TABLE runs (
            run_id TEXT, seed INTEGER, status TEXT, fidelity TEXT, seed_role TEXT,
            design_id TEXT, design_json TEXT, wall_seconds REAL
        );
        CREATE TABLE attempts (run_id TEXT, status TEXT);
    """)
    connection.execute(
        "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (run_id, 1, "complete", "longitudinal", seed_role, label,
         json.dumps(design), 12.0),
    )
    connection.commit()
    connection.close()

    evaluation = {
        "run_id": run_id,
        "comparison_eligibility": eligibility,
        "hard_constraints": [{"id": "integrity", "state": "pass"}],
        "capabilities": [{
            "id": "participation-continuity",
            "state": "fail" if eligibility == "infeasible" else "pass",
        }],
        "measurement_gaps": [],
        "constitution": {"id": "constitution", "version": "1"},
        "evaluator": {"id": "evaluator", "version": "1"},
        "metrics": {
            "integrity-checks-pass": {"status": "measured", "value": True},
            "active-researcher-fraction": {
                "status": "measured",
                "value": 0.7 + funding_fraction,
                "slice_results": {
                    "low-resource-researchers": {
                        "status": "measured", "value": 0.5 + funding_fraction,
                    }
                },
            },
            "review-burden-per-active-researcher": {
                "status": "measured",
                "value": 2.0 - funding_fraction,
                "slice_results": {
                    "low-resource-researchers": {
                        "status": "measured", "value": 2.5 - funding_fraction,
                    }
                },
            },
            "topic-entropy": {"status": "measured", "value": 1.5},
        },
    }
    report = {
        "report_errors": [],
        "status_counts": {"complete": 1},
        "completed_runs": [{
            "run_id": run_id, "seed": 1, "total_resources": 100,
            "papers": 2, "reviews": 6, "accepted": 1,
        }],
        "objective_evaluations": [evaluation],
        "funding_application_reliability": [{"run_id": run_id, "state": "pass"}],
    }
    (root / "registry-report.json").write_text(json.dumps(report))
    study = {"id": label, "seed_sets": {seed_role: [1]}}
    if confirmation_policy is not None:
        study["paired_confirmation_policy"] = confirmation_policy
    (root / "study-snapshot.json").write_text(json.dumps({
        "study": study,
        "study_revision": f"{label}-revision",
    }))

    docs = root / "docs" / run_id
    docs.mkdir(parents=True)
    manifest = {
        "run_seed": 1,
        "git_commit": "abc",
        "git_dirty_files": "",
        "source_files_sha256": {"simulation.py": "hash"},
        "python": "3.11",
        "package_versions": {"numpy": "1"},
        "model_id": "qwen3:8b",
        "dataset_identity": {"revision": "dataset"},
        "ordered_documents_sha256": "documents",
        "retrieval_embedding": {"revision": "retrieval"},
        "metric_embedding": {"revision": "metric"},
        "resolved_config": {"fixed": True},
        "args": {
            "seed": 1,
            "funding_budget_slots_frac": funding_fraction,
            "reviewer_capacity": 4,
            "run_id": run_id,
            "experiment_id": run_id,
            "checkpoint_dir": str(root / "checkpoints" / run_id),
            "docs_dir": str(docs),
            "log_dir": str(root / "logs" / run_id),
            "output_dir": str(root / "checkpoints" / run_id),
        },
    }
    (docs / "run_manifest.json").write_text(json.dumps(manifest))

    checkpoint = root / "checkpoints" / run_id
    checkpoint.mkdir(parents=True)
    (checkpoint / "funding_application_trace_year_1.summary.json").write_text(
        json.dumps({"counts": {
            "targets": 3, "submitted": 3, "funded": 1,
            "allocations_applied": 1,
        }})
    )
    (checkpoint / "resource_balances.jsonl").write_text(
        json.dumps({"grant_income": 100.0 * funding_fraction}) + "\n"
    )


def test_paired_summary_uses_sample_sd_and_deterministic_bootstrap():
    first = summarize_deltas([0.0, 0.1, 0.2, 0.1, 0.0])
    second = summarize_deltas([0.0, 0.1, 0.2, 0.1, 0.0])

    assert first == second
    assert first["n"] == 5
    assert first["mean"] == pytest.approx(0.08)
    assert first["sample_sd"] == pytest.approx(0.08366600265)
    assert (first["positive"], first["zero"], first["negative"]) == (3, 2, 0)
    assert first["mean_interval"]["seed"] == 20261025
    assert bootstrap_mean_interval([1.0])["lower"] == 1.0


def test_build_comparison_keeps_infeasible_pair_as_diagnostic(tmp_path):
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write_campaign(baseline, label="baseline", funding_fraction=0.3,
                    eligibility="infeasible")
    _write_campaign(candidate, label="candidate", funding_fraction=0.5,
                    eligibility="feasible")

    report = build_paired_comparison(baseline, candidate, seeds=[1])

    assert report["audit"]["technical_admissibility_pass"] is True
    assert report["formal_comparison"]["status"] == "incomplete"
    assert report["formal_comparison"]["authorized_for_ranking"] is False
    assert report["paired_metric_summaries"]["active_researcher_fraction"]["mean"] \
        == pytest.approx(0.2)
    assert report["paired_runs"][0]["baseline_eligibility"] == "infeasible"
    assert "diagnostic evidence" in render_markdown(report)


def test_confirmation_treats_capability_failure_as_outcome_distribution(tmp_path):
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    policy = {
        "id": "confirmation-capability-outcomes",
        "version": "1.0.0",
        "capability_treatment": "outcome_distribution",
        "candidate_gates": {
            "require_zero_candidate_capability_failures": True,
            "require_no_pass_to_fail_transition": True,
            "require_no_negative_protected_slice_pairs": True,
            "minimum_primary_mean_delta": 0.0,
        },
    }
    _write_campaign(
        baseline, label="baseline", funding_fraction=0.3,
        eligibility="infeasible", seed_role="confirmation",
        confirmation_policy=policy,
    )
    _write_campaign(
        candidate, label="candidate", funding_fraction=0.5,
        eligibility="feasible", seed_role="confirmation",
        confirmation_policy=policy,
    )

    report = build_paired_comparison(
        baseline, candidate, seeds=[1], seed_role="confirmation",
    )

    assert report["schema"] == "scienceutopia.paired_system_comparison.v2"
    assert report["formal_comparison"]["status"] == "complete"
    assert report["formal_comparison"]["authorized_for_ranking"] is False
    assert report["formal_comparison"]["authorized_for_confirmatory_interpretation"] is True
    assert report["capability_outcome_distribution"]["baseline"]["fail"] == 1
    assert report["capability_outcome_distribution"]["candidate"]["pass"] == 1
    assert report["capability_outcome_distribution"]["paired_transitions"]["fail_to_pass"] == 1
    assert report["candidate_confirmation_decision"]["status"] == "confirmed_tradeoff"
    assert "Confirmation capability outcome" in render_markdown(report)


def test_cli_uses_seed_set_declared_for_requested_role(tmp_path):
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    output = tmp_path / "comparison.json"
    _write_campaign(
        baseline, label="baseline", funding_fraction=0.3,
        eligibility="feasible", seed_role="confirmation",
    )
    _write_campaign(
        candidate, label="candidate", funding_fraction=0.5,
        eligibility="feasible", seed_role="confirmation",
    )

    assert main([
        "--baseline-root", str(baseline),
        "--candidate-root", str(candidate),
        "--seed-role", "confirmation",
        "--json-output", str(output),
    ]) == 0
    report = json.loads(output.read_text())
    assert report["comparison"]["seeds"] == [1]
    assert report["comparison"]["pairing_key"] == "confirmation_seed"


def test_build_comparison_rejects_unregistered_design_change(tmp_path):
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write_campaign(baseline, label="baseline", funding_fraction=0.3,
                    eligibility="feasible")
    _write_campaign(candidate, label="candidate", funding_fraction=0.5,
                    eligibility="feasible")
    connection = sqlite3.connect(candidate / "registry.sqlite3")
    design = {"funding_budget_slots_frac": 0.5, "reviewer_capacity": 5}
    connection.execute("UPDATE runs SET design_json = ?", (json.dumps(design),))
    connection.commit()
    connection.close()

    with pytest.raises(ValueError, match="differs outside"):
        build_paired_comparison(baseline, candidate, seeds=[1])
