import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from utopia.optimization import metric_conditioned_study
from utopia.optimization.closed_loop import validate_campaign_spec
from utopia.optimization.harness import RunRegistry, load_study
from utopia.optimization.loss import load_loss_spec
from utopia.optimization.metric_conditioned_study import (
    MetricConditionedStudy,
    select_frozen_winner,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "research/specs/metric-conditioned-optimization-study-v1.json"
SCHEMA_PATH = ROOT / "research/specs/metric-conditioned-optimization-study-v1.schema.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_metric_conditioned_study_manifest_and_campaigns_are_valid():
    manifest = _load(MANIFEST_PATH)
    schema = _load(SCHEMA_PATH)
    Draft202012Validator(schema).validate(manifest)
    evaluator_spec = _load(ROOT / manifest["held_out_evaluator"]["spec"])
    assert evaluator_spec["evaluator"] == {
        "id": manifest["held_out_evaluator"]["id"],
        "version": manifest["held_out_evaluator"]["version"],
    }
    native_ids = {item["id"] for item in evaluator_spec["metrics"]}
    declared_ids = {item["id"] for item in manifest["held_out_metric_suite"]}
    assert native_ids.issubset(declared_ids)

    forbidden = set(manifest["forbidden_legacy_held_out_seeds"])
    optimization = set(manifest["common_optimization_seeds"])
    held_out = set(manifest["common_held_out_evaluation_seeds"])
    assert forbidden.isdisjoint(optimization | held_out)
    assert optimization.isdisjoint(held_out)
    assert forbidden == {523, 541, 547}

    campaigns = []
    losses = []
    loss_schema = _load(ROOT / "research/specs/loss-spec-v1.schema.json")
    for relative in manifest["campaigns"]:
        campaign = _load(ROOT / relative)
        validate_campaign_spec(campaign)
        study, space, _ = load_study(ROOT / campaign["study_template"])
        loss = load_loss_spec(ROOT / campaign["loss_spec"])
        Draft202012Validator(loss_schema).validate(loss)
        campaigns.append(campaign)
        losses.append(loss)

        assert campaign["fidelity"] == "longitudinal"
        assert campaign["fidelity"] in space["fidelities"]
        assert campaign["seed_sets"]["optimization"] == sorted(optimization)
        assert campaign["seed_sets"]["held_out_evaluation"] == sorted(held_out)
        assert len(optimization) >= loss["across_seeds"]["minimum_valid_runs"]
        assert study["execution"]["model"] == "qwen3:8b"

    assert len({loss["id"] for loss in losses}) == 3
    assert all(loss["status"] == "research" for loss in losses)

    common_fields = (
        "study_template",
        "fidelity",
        "seed_sets",
        "optimizer",
        "budget",
        "execution",
    )
    reference = campaigns[0]
    for campaign in campaigns[1:]:
        for field in common_fields:
            assert campaign[field] == reference[field]


def test_study_budget_and_policy_preserve_loss_evaluation_separation():
    manifest = _load(MANIFEST_PATH)
    campaigns = [_load(ROOT / relative) for relative in manifest["campaigns"]]

    optimization_runs = sum(
        campaign["budget"]["max_suggestions"]
        * len(campaign["seed_sets"]["optimization"])
        for campaign in campaigns
    )
    evaluation_runs = (
        len(campaigns) * len(manifest["common_held_out_evaluation_seeds"])
    )

    assert optimization_runs == 45
    assert evaluation_runs == 15
    assert manifest["decision_policy"] == "report_only"
    assert all(
        item["role"] in {"evaluation_metric", "shadow_diagnostic"}
        for item in manifest["held_out_metric_suite"]
    )
    assert all(
        seed not in manifest["common_optimization_seeds"]
        for seed in manifest["common_held_out_evaluation_seeds"]
    )


def test_frozen_winner_uses_loss_then_earliest_proposal_index():
    records = [
        {
            "status": "observed_complete",
            "suggestion": {"proposal_index": 2},
            "observation": {"loss": 0.2},
        },
        {
            "status": "observed_complete",
            "suggestion": {"proposal_index": 0},
            "observation": {"loss": 0.2},
        },
        {
            "status": "observed_complete",
            "suggestion": {"proposal_index": 1},
            "observation": {"loss": 0.4},
        },
    ]

    assert select_frozen_winner(records)["suggestion"]["proposal_index"] == 0


def test_held_out_registry_requires_three_arm_winner_freeze(tmp_path, monkeypatch):
    source_manifest = _load(MANIFEST_PATH)
    campaign_paths = []
    for source_relative in source_manifest["campaigns"]:
        campaign = _load(ROOT / source_relative)
        campaign["study_template"] = str(ROOT / campaign["study_template"])
        campaign["loss_spec"] = str(ROOT / campaign["loss_spec"])
        campaign["execution"]["output_root"] = str(tmp_path / "outputs")
        campaign["execution"]["require_clean_worktree"] = False
        path = tmp_path / f"{campaign['id']}.json"
        path.write_text(json.dumps(campaign), encoding="utf-8")
        campaign_paths.append(str(path))
    source_manifest["campaigns"] = campaign_paths
    manifest_path = tmp_path / "study.json"
    manifest_path.write_text(json.dumps(source_manifest), encoding="utf-8")

    study = MetricConditionedStudy(manifest_path)
    study.initialize()
    with pytest.raises(RuntimeError, match="freeze all arm winners"):
        study.plan_evaluation()

    baseline = _load(ROOT / "research/specs/example-design-v0.json")
    for campaign in study.campaigns:
        state = campaign._load_state()
        state["suggestions"] = []
        for index, loss in enumerate((0.5, 0.2, 0.2, 0.3, 0.4)):
            state["suggestions"].append({
                "suggestion": {
                    "suggestion_id": f"{campaign.spec['id']}-s{index}",
                    "proposal_index": index,
                },
                "source_candidate": baseline,
                "design_id": "baseline",
                "system_fingerprint": f"fp-{campaign.spec['id']}",
                "status": "observed_complete",
                "observation": {
                    "observation_id": f"o-{campaign.spec['id']}-{index}",
                    "suggestion_id": f"{campaign.spec['id']}-s{index}",
                    "status": "complete",
                    "loss": loss,
                },
            })
        campaign._save_state(state)

    frozen = study.freeze_winners()
    assert len(frozen["winners"]) == 3
    assert {winner["proposal_index"] for winner in frozen["winners"]} == {1}
    planned = study.plan_evaluation()
    assert planned["added_runs"] == 15
    assert planned["total_runs"] == 15
    assert study.audit()["passed"] is True

    registry = RunRegistry(study.evaluation_registry_path)
    try:
        rows = registry.rows()
        for row in rows:
            registry.start(row["run_id"])
            registry.finish(
                row["run_id"],
                status="complete",
                returncode=0,
                wall_seconds=1.0,
                error=None,
            )
    finally:
        registry.close()

    def fake_report(registry, constitution):
        rows = registry.rows()
        return {
            "objective_evaluations": [
                {
                    "run_id": row["run_id"],
                    "metrics": {
                        "active-researcher-fraction": {
                            "status": "measured",
                            "value": 0.8,
                            "slice_results": {
                                "low-resource-researchers": {
                                    "status": "measured",
                                    "value": 0.7,
                                }
                            },
                        },
                        "topic-entropy": {
                            "status": "measured",
                            "value": 0.5,
                            "slice_results": {},
                        },
                        "review-burden-per-active-researcher": {
                            "status": "measured",
                            "value": 1.2,
                            "slice_results": {
                                "low-resource-researchers": {
                                    "status": "measured",
                                    "value": 1.3,
                                }
                            },
                        },
                    },
                }
                for row in rows
            ],
            "completed_runs": [
                {
                    "run_id": row["run_id"],
                    "accepted": 2,
                    "total_resources": 100.0,
                }
                for row in rows
            ],
        }

    def fake_common_suite(*, run_id, output_root, candidate, objective_evaluation):
        metrics = dict(objective_evaluation["metrics"])
        metrics.update({
            "submission-count": {
                "metric_version": "1.0.0", "status": "measured", "value": 10,
            },
            "decision-count": {
                "metric_version": "1.0.0", "status": "measured", "value": 10,
            },
            "accepted-paper-count": {
                "metric_version": "1.0.0", "status": "measured", "value": 2,
            },
            "review-coverage": {
                "metric_version": "1.0.0", "status": "measured", "value": 0.9,
            },
            "attrition-fraction": {
                "metric_version": "1.0.0", "status": "measured", "value": 0.2,
            },
            "funding-and-resource-ledger": {
                "metric_version": "1.0.0",
                "status": "measured",
                "value": {
                    "allocations": {"status": "measured", "applied": 3},
                    "resource_inflow": {
                        "status": "measured", "grant_income": 60.0,
                        "industry_income": 0.0, "total_income": 60.0,
                    },
                    "ending_resources": {
                        "status": "measured", "mean": 100.0, "gini": 0.2,
                    },
                    "application_pipeline": {
                        "status": "measured", "totals": {"submitted": 20},
                    },
                },
            },
        })
        return {"run_id": run_id, "metrics": metrics}

    monkeypatch.setattr(metric_conditioned_study, "build_report", fake_report)
    monkeypatch.setattr(
        metric_conditioned_study, "evaluate_common_suite", fake_common_suite
    )
    report = study.report_evaluation()
    assert len(report["loss_by_frozen_winner"]) == 3
    assert all(
        len(losses) == 3
        and all(item["status"] == "complete" for item in losses.values())
        for losses in report["loss_by_frozen_winner"].values()
    )
    assert all(
        next(item for item in profiles if item["id"] == "review-coverage")[
            "complete"
        ]
        is True
        for profiles in report["held_out_metric_profiles"].values()
    )
    assert set(report["analyses"]) == {
        "rank_reversal",
        "paired_tradeoffs",
        "gaming_flags",
        "generalization",
        "secondary_resolution",
    }
    assert len(report["analyses"]["paired_tradeoffs"]) > 0
    assert len(report["analyses"]["secondary_resolution"]) > 0
