import json
from pathlib import Path

import pytest

from utopia.optimization import closed_loop
from utopia.optimization.closed_loop import ClosedLoopCampaign
from utopia.optimization.harness import RunRegistry


ROOT = Path(__file__).resolve().parents[2]


def _campaign_spec(tmp_path, *, campaign_id="controller-test"):
    return {
        "schema": "scienceutopia.closed-loop-campaign.v1",
        "id": campaign_id,
        "version": "1.0.0",
        "status": "engineering_demo",
        "study_template": str(ROOT / "research/specs/study-v2-smoke.json"),
        "loss_spec": str(
            ROOT
            / "research/objectives/losses/engineering-continuity-demo-v1.json"
        ),
        "fidelity": "smoke",
        "seed_sets": {
            "optimization": [503, 509, 521],
            "held_out_evaluation": [523, 541, 547],
        },
        "optimizer": {
            "kind": "adaptive_random_search",
            "seed": 20261027,
            "initial_random": 2,
            "mutation_scale": 0.2,
        },
        "budget": {
            "max_suggestions": 3,
            "initial_batch": 2,
            "adaptive_batch": 1,
        },
        "execution": {
            "workers": 1,
            "output_root": str(tmp_path / "outputs"),
            "require_clean_worktree": False,
        },
    }


def _write_campaign(tmp_path, **kwargs):
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(_campaign_spec(tmp_path, **kwargs)))
    return path


def _complete_all_runs(controller):
    registry = RunRegistry(controller.paths.registry)
    try:
        for row in registry.rows():
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


def test_persistent_campaign_closes_result_dependent_loop(tmp_path, monkeypatch):
    controller = ClosedLoopCampaign(_write_campaign(tmp_path))
    initialized = controller.initialize()
    initial = controller.suggest()

    assert initialized["budget"] == {"used": 0, "maximum": 3}
    assert len(initial) == 2
    assert {item["suggestion"]["phase"] for item in initial} == {"initial"}
    assert controller.status()["runs"] == {"planned": 6}
    with pytest.raises(RuntimeError, match="resolve pending"):
        controller.suggest(1)

    # A fresh object reconstructs the optimizer and job ledger from disk.
    resumed = ClosedLoopCampaign(controller.campaign_path)
    assert resumed.status()["suggestions"] == {"planned": 2}
    _complete_all_runs(resumed)
    better_design = initial[1]["design_id"]

    def fake_report(registry, constitution):
        evaluations = []
        for row in registry.rows("status='complete'"):
            active_fraction = 0.9 if row["design_id"] == better_design else 0.5
            evaluations.append({
                "run_id": row["run_id"],
                "metrics": {
                    "active-researcher-fraction": {
                        "status": "measured",
                        "value": active_fraction,
                    },
                    "review-burden-per-active-researcher": {
                        "status": "measured",
                        "value": 1.0,
                    },
                },
            })
        return {"objective_evaluations": evaluations}

    monkeypatch.setattr(closed_loop, "build_report", fake_report)
    observations = resumed.observe_ready()

    assert len(observations) == 2
    assert all(item["status"] == "complete" for item in observations)
    better_observation = next(
        item
        for item in observations
        if item["metadata"]["design_id"] == better_design
    )
    adaptive = resumed.suggest()[0]

    assert adaptive["suggestion"]["phase"] == "adaptive"
    assert (
        adaptive["suggestion"]["based_on_observation_id"]
        == better_observation["observation_id"]
    )
    assert resumed.status()["budget"] == {"used": 3, "maximum": 3}
    assert resumed.status()["held_out_evaluation_seeds_consumed"] is False
    registry = RunRegistry(resumed.paths.registry)
    try:
        assert {row["seed_role"] for row in registry.rows()} == {"optimization"}
        assert {row["seed"] for row in registry.rows()} == {503, 509, 521}
    finally:
        registry.close()


def test_missing_loss_input_becomes_invalid_not_numeric_penalty(tmp_path, monkeypatch):
    controller = ClosedLoopCampaign(
        _write_campaign(tmp_path, campaign_id="invalid-observation-test")
    )
    controller.initialize()
    controller.suggest()
    _complete_all_runs(controller)

    def incomplete_report(registry, constitution):
        rows = registry.rows("status='complete'")
        # Each design has three completed runs, but only two have usable metrics.
        evaluations = []
        per_design = {}
        for row in rows:
            used = per_design.get(row["design_id"], 0)
            per_design[row["design_id"]] = used + 1
            if used < 2:
                evaluations.append({
                    "run_id": row["run_id"],
                    "metrics": {
                        "active-researcher-fraction": {
                            "status": "measured",
                            "value": 0.8,
                        },
                        "review-burden-per-active-researcher": {
                            "status": "measured",
                            "value": 1.0,
                        },
                    },
                })
        return {"objective_evaluations": evaluations}

    monkeypatch.setattr(closed_loop, "build_report", incomplete_report)
    observations = controller.observe_ready()

    assert len(observations) == 2
    assert {item["status"] for item in observations} == {"invalid"}
    assert all(item["loss"] is None for item in observations)
    assert controller.status()["incumbent"] is None


def test_campaign_rejects_overlapping_optimization_and_held_out_seeds(tmp_path):
    spec = _campaign_spec(tmp_path)
    spec["seed_sets"]["held_out_evaluation"] = [521, 523]
    path = tmp_path / "overlap.json"
    path.write_text(json.dumps(spec))

    with pytest.raises(ValueError, match="disjoint"):
        ClosedLoopCampaign(path)


def test_exact_loss_tie_retains_earliest_proposal(tmp_path, monkeypatch):
    controller = ClosedLoopCampaign(_write_campaign(tmp_path, campaign_id="tie-test"))
    controller.initialize()
    suggestions = controller.suggest()
    _complete_all_runs(controller)

    def tied_report(registry, constitution):
        return {
            "objective_evaluations": [
                {
                    "run_id": row["run_id"],
                    "metrics": {
                        "active-researcher-fraction": {
                            "status": "measured",
                            "value": 0.8,
                        },
                        "review-burden-per-active-researcher": {
                            "status": "measured",
                            "value": 1.0,
                        },
                    },
                }
                for row in registry.rows("status='complete'")
            ]
        }

    monkeypatch.setattr(closed_loop, "build_report", tied_report)
    controller.observe_ready()

    assert (
        controller.status()["incumbent"]["suggestion_id"]
        == suggestions[0]["suggestion"]["suggestion_id"]
    )


def test_production_campaign_rejects_dirty_source_tree(tmp_path):
    spec = _campaign_spec(tmp_path)
    spec["execution"]["require_clean_worktree"] = True
    path = tmp_path / "clean-required.json"
    path.write_text(json.dumps(spec))
    controller = ClosedLoopCampaign(path)
    controller.source = {
        "commit": controller.source["commit"],
        "tree_dirty": True,
        "dirty_paths": [" M utopia/example.py"],
    }

    with pytest.raises(RuntimeError, match="requires a clean worktree"):
        controller.initialize()
