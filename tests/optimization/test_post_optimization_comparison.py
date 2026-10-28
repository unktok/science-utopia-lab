from copy import deepcopy
import hashlib
import json
from pathlib import Path
import statistics
import xml.etree.ElementTree as ET

import jsonschema
import pytest

from scripts.reports.metric_conditioned_post_optimization_comparison import main
from utopia.optimization.metric_conditioned_completion import REPORT_SCHEMA as COMPLETION_SCHEMA
from utopia.optimization.post_optimization_comparison import (
    REPORT_SCHEMA,
    build_post_optimization_comparison,
)


ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / "tests/fixtures/metric-conditioned-post-optimization-request.synthetic-test.json"
SCHEMA = ROOT / "research/specs/metric-conditioned-post-optimization-comparison-v1.schema.json"
ARMS = ("participation-arm", "review-burden-arm", "topic-diversity-arm")
LOSSES = ("participation-loss", "review-burden-loss", "topic-diversity-loss")
DEV_SEEDS = (11, 13, 17)
PROTECTED_SEEDS = (701, 709, 719, 727, 733)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _fingerprint(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _cell(base, arm, loss_id, proposal):
    values = [base - 0.1, base, base + 0.1]
    spread = statistics.pstdev(values)
    return {
        "loss": base + 0.25 * spread,
        "mean": statistics.fmean(values),
        "population_sd": spread,
        "seed_values": [
            {
                "seed": seed,
                "run_id": f"{arm}-p{proposal}-s{seed}",
                "loss": value,
                "execution_mode": "executed" if arm == ARMS[0] else "adopted",
            }
            for seed, value in zip(DEV_SEEDS, values)
        ],
        "uncertainty": {
            "method": "exact_seed_bootstrap_percentile",
            "resamples": 27,
            "ci95_low": base - 0.1,
            "ci95_high": base + 0.1,
        },
    }


def _completion_report():
    request = _load(REQUEST)
    fingerprints = request["winner_fingerprints"]
    winner_bases = {
        ARMS[0]: (1.0, 3.0, 2.0),
        ARMS[1]: (2.0, 1.0, 3.0),
        ARMS[2]: (3.0, 2.0, 1.0),
    }
    arms = {}
    frozen = []
    rankings = {loss_id: {"values": {}} for loss_id in LOSSES}
    matrix = {}
    for arm_index, arm in enumerate(ARMS):
        candidates = []
        for proposal in range(5):
            bases = tuple(value + (4 - proposal) for value in winner_bases[arm])
            cross = {
                loss_id: _cell(base, arm, loss_id, proposal)
                for loss_id, base in zip(LOSSES, bases)
            }
            candidate_key = f"{arm}/p{proposal}"
            candidate = {
                "candidate_key": candidate_key,
                "proposal_index": proposal,
                "phase": "initial" if proposal < 3 else "adaptive",
                "suggestion_id": f"suggestion-{arm}-{proposal}",
                "design_id": f"design-{arm}-{proposal}",
                "system_fingerprint": (
                    fingerprints[arm] if proposal == 4
                    else _fingerprint(f"{arm}-{proposal}")
                ),
                "source_candidate": {"synthetic": proposal},
                "run_ids": [f"{arm}-p{proposal}-s{seed}" for seed in DEV_SEEDS],
                "execution_provenance": (
                    {"executed": 3} if arm == ARMS[0] else {"adopted": 3}
                ),
                "cross_objective_losses": cross,
            }
            candidates.append(candidate)
            for loss_id in LOSSES:
                rankings[loss_id]["values"][candidate_key] = cross[loss_id]["loss"]
        winner = candidates[-1]
        own_loss = LOSSES[arm_index]
        arms[arm] = {
            "loss_spec": {
                "id": own_loss,
                "version": "synthetic-v1",
                "sha256": _fingerprint(own_loss),
            },
            "campaign_revision": f"revision-{arm}",
            "candidates": candidates,
            "frozen_winner_candidate_key": winner["candidate_key"],
            "execution": {
                "logical_runs": 15,
                "executed_runs": 15 if arm == ARMS[0] else 6,
                "adopted_runs": 0 if arm == ARMS[0] else 9,
                "attempt_status_counts": {
                    "complete": 15 if arm == ARMS[0] else 6,
                    **({"interrupted": 1} if arm == ARMS[1] else {}),
                },
                "physical_attempt_wall_seconds": 1500.0 + arm_index * 100,
                "artifact_links": [] if arm == ARMS[0] else [{"synthetic": True}] * 9,
            },
        }
        matrix[arm] = deepcopy(winner["cross_objective_losses"])
        frozen.append({
            "campaign_id": arm,
            "system_fingerprint": winner["system_fingerprint"],
            "design_id": winner["design_id"],
        })
    for loss_id in LOSSES:
        values = rankings[loss_id]["values"]
        order = sorted(values, key=lambda key: (values[key], key))
        rankings[loss_id].update({
            "ranks": {key: index + 1 for index, key in enumerate(order)},
            "order": order,
            "best_candidate_key": order[0],
            "best_design_id": order[0],
        })
    return {
        "schema": COMPLETION_SCHEMA,
        "study_id": "synthetic-post-optimization-study",
        "study_revision": "synthetic-complete-revision",
        "data_classification": "synthetic_test_fixture",
        "evidence_boundary": {
            "split": "development_only",
            "held_out_consumed": False,
            "held_out_seeds": list(PROTECTED_SEEDS),
            "verified_absent_paths": ["protected/a", "protected/b", "protected/c"],
            "interpretation": "Synthetic development-only fixture.",
        },
        "contract": {
            "arms": 3,
            "candidates_per_arm": 5,
            "development_seeds_per_candidate": 3,
            "logical_runs": 45,
            "distinct_losses": 3,
            "decision_policy": "report_only",
        },
        "provenance": {
            "source_commit": "f" * 40,
            "controlled_search_contract_sha256": {
                name: _fingerprint(name)
                for name in ("study_template", "fidelity", "seed_sets", "optimizer", "budget", "execution")
            },
            "manifest_path": "synthetic/manifest.json",
            "manifest_sha256": _fingerprint("manifest"),
            "winner_freeze_path": "synthetic/winner-freeze.json",
            "winner_freeze_sha256": _fingerprint("freeze"),
            "campaign_files": {
                arm: {
                    "snapshot_sha256": _fingerprint(f"{arm}-snapshot"),
                    "state_sha256": _fingerprint(f"{arm}-state"),
                    "registry_sha256": _fingerprint(f"{arm}-registry"),
                    "registry_report_sha256": _fingerprint(f"{arm}-report"),
                }
                for arm in ARMS
            },
        },
        "execution": {
            "logical_runs": 45,
            "executed_runs": 27,
            "adopted_runs": 18,
            "attempt_status_counts": {"complete": 27, "interrupted": 1, "failed": 2},
            "physical_attempt_wall_seconds": 4800.0,
        },
        "arms": arms,
        "frozen_winners": frozen,
        "development_cross_objective": {
            "candidate_rankings": rankings,
            "frozen_winner_matrix": matrix,
            "pairwise_rank_association": [],
            "winner_reversals": [],
        },
        "interpretation_guard": "Synthetic fixture; no universal winner.",
    }


def test_builds_matrix_pareto_uncertainty_runtime_and_provenance():
    request = _load(REQUEST)
    report = build_post_optimization_comparison(
        _completion_report(), request["winner_fingerprints"]
    )

    assert report["schema"] == REPORT_SCHEMA
    assert len(report["winner_matrix"]) == 3
    assert all(len(row["evaluations"]) == 3 for row in report["winner_matrix"].values())
    assert report["pareto"]["front_arms"] == list(ARMS)
    assert all(pair["relation"] == "trade_off" for pair in report["tradeoffs"])
    assert report["rank_reversal"]["observed"] is True
    assert report["execution"]["non_complete_physical_attempts"] == 3
    assert report["execution"]["global"]["executed_runs"] == 27
    assert report["execution"]["global"]["adopted_runs"] == 18
    assert report["authorization"]["held_out_artifacts_read"] is False
    assert report["authorization"]["held_out_seeds_consumed"] is False
    assert set(report["provenance"]["campaign_files"]) == set(ARMS)
    schema = _load(SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(report)


def test_explicit_fingerprint_mismatch_fails_closed():
    fingerprints = deepcopy(_load(REQUEST)["winner_fingerprints"])
    fingerprints[ARMS[0]] = "d" * 64

    with pytest.raises(ValueError, match="differs from the frozen winner"):
        build_post_optimization_comparison(_completion_report(), fingerprints)


def test_tampered_seed_summary_fails_closed():
    completion = _completion_report()
    arm = ARMS[0]
    key = completion["arms"][arm]["frozen_winner_candidate_key"]
    winner = next(
        item for item in completion["arms"][arm]["candidates"]
        if item["candidate_key"] == key
    )
    winner["cross_objective_losses"][LOSSES[0]]["mean"] += 1
    completion["development_cross_objective"]["frozen_winner_matrix"][arm] = deepcopy(
        winner["cross_objective_losses"]
    )

    with pytest.raises(ValueError, match="seed mean does not recompute"):
        build_post_optimization_comparison(
            completion, _load(REQUEST)["winner_fingerprints"]
        )


def test_pareto_dominance_is_computed_within_each_loss_only():
    completion = _completion_report()
    dominated_arm = ARMS[2]
    key = completion["arms"][dominated_arm]["frozen_winner_candidate_key"]
    winner = next(
        item for item in completion["arms"][dominated_arm]["candidates"]
        if item["candidate_key"] == key
    )
    winner["cross_objective_losses"] = {
        loss_id: _cell(5.0 + index, dominated_arm, loss_id, 4)
        for index, loss_id in enumerate(LOSSES)
    }
    completion["development_cross_objective"]["frozen_winner_matrix"][
        dominated_arm
    ] = deepcopy(winner["cross_objective_losses"])

    report = build_post_optimization_comparison(
        completion, _load(REQUEST)["winner_fingerprints"]
    )

    assert dominated_arm not in report["pareto"]["front_arms"]
    assert any(
        relation["dominated"] == dominated_arm
        for relation in report["pareto"]["dominance_relations"]
    )


def test_cli_writes_atomic_machine_and_paper_outputs_without_held_out_artifacts(tmp_path):
    completion_path = tmp_path / "completion.json"
    completion_path.write_text(
        json.dumps(_completion_report(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    protected = tmp_path / "held-out-evaluation" / "sentinel"
    protected.parent.mkdir()
    protected.write_bytes(b"never-read-or-modified")
    before = protected.stat().st_mtime_ns
    output = tmp_path / "output"
    arguments = ["--completion-report", str(completion_path)]
    for arm, fingerprint in _load(REQUEST)["winner_fingerprints"].items():
        arguments.extend(("--winner-fingerprint", f"{arm}={fingerprint}"))
    arguments.extend(("--output-dir", str(output)))

    assert main(arguments) == 0

    assert protected.read_bytes() == b"never-read-or-modified"
    assert protected.stat().st_mtime_ns == before
    assert (output / "cross-objective-matrix.csv").read_text().count("\n") == 10
    assert (output / "pareto-tradeoffs.csv").read_text().count("\n") == 10
    assert (output / "seed-uncertainty.csv").read_text().count("\n") == 28
    assert (output / "runtime-provenance.csv").read_text().count("\n") == 5
    svg = (output / "figures/post-optimization-comparison.svg").read_text()
    assert "SYNTHETIC TEST ONLY" in svg
    ET.fromstring(svg)
    assert "not held-out estimates" in (
        output / "post-optimization-comparison.tex"
    ).read_text()
    machine = _load(output / "post-optimization-comparison.json")
    emitted_seeds = {
        seed["seed"]
        for winner in machine["winner_matrix"].values()
        for cell in winner["evaluations"].values()
        for seed in cell["seed_values"]
    }
    assert emitted_seeds == set(DEV_SEEDS)
    assert emitted_seeds.isdisjoint(PROTECTED_SEEDS)
    assert _load(output / "artifact-manifest.json")["files"]


def test_package_refuses_overwrite(tmp_path):
    completion_path = tmp_path / "completion.json"
    completion_path.write_text(json.dumps(_completion_report()), encoding="utf-8")
    output = tmp_path / "existing"
    output.mkdir()
    args = ["--completion-report", str(completion_path)]
    for arm, fingerprint in _load(REQUEST)["winner_fingerprints"].items():
        args.extend(("--winner-fingerprint", f"{arm}={fingerprint}"))
    args.extend(("--output-dir", str(output)))
    with pytest.raises(FileExistsError, match="refuse to overwrite"):
        main(args)
