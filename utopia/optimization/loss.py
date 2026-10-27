"""Versioned optimization-loss evaluation, separate from held-out metrics."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence


SCHEMA = "scienceutopia.loss-spec.v1"
RESULT_SCHEMA = "scienceutopia.loss-evaluation.v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def loss_spec_sha256(spec: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(spec).encode()).hexdigest()


def load_loss_spec(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("LossSpec must be a JSON object")
    validate_loss_spec(value)
    return value


def validate_loss_spec(spec: Mapping[str, Any]) -> None:
    errors: list[str] = []
    if spec.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA!r}")
    for name in ("id", "version", "status", "optimization_seed_role"):
        if not isinstance(spec.get(name), str) or not spec[name]:
            errors.append(f"{name} must be a non-empty string")
    if spec.get("direction") != "minimize":
        errors.append("direction must be 'minimize'; maximize signals use negative terms")
    per_run = spec.get("per_run")
    if not isinstance(per_run, dict):
        errors.append("per_run must be an object")
    else:
        intercept = per_run.get("intercept")
        if not _finite_number(intercept):
            errors.append("per_run.intercept must be finite")
        terms = per_run.get("terms")
        if not isinstance(terms, list) or not terms:
            errors.append("per_run.terms must be a non-empty array")
        else:
            seen: set[tuple[str, str | None]] = set()
            for index, term in enumerate(terms):
                if not isinstance(term, dict):
                    errors.append(f"per_run.terms[{index}] must be an object")
                    continue
                metric_id = term.get("metric_id")
                slice_id = term.get("slice_id")
                if not isinstance(metric_id, str) or not metric_id:
                    errors.append(f"per_run.terms[{index}].metric_id is required")
                if slice_id is not None and (
                    not isinstance(slice_id, str) or not slice_id
                ):
                    errors.append(
                        f"per_run.terms[{index}].slice_id must be null or non-empty"
                    )
                if not _finite_number(term.get("coefficient")):
                    errors.append(f"per_run.terms[{index}].coefficient must be finite")
                identity = (metric_id, slice_id)
                if identity in seen:
                    errors.append(f"duplicate loss input {identity!r}")
                seen.add(identity)
    across = spec.get("across_seeds")
    if not isinstance(across, dict):
        errors.append("across_seeds must be an object")
    else:
        if across.get("aggregation") != "mean_plus_population_sd":
            errors.append(
                "across_seeds.aggregation must be 'mean_plus_population_sd'"
            )
        if not _finite_number(across.get("dispersion_weight")) or (
            across.get("dispersion_weight", -1) < 0
        ):
            errors.append("across_seeds.dispersion_weight must be finite and nonnegative")
        minimum = across.get("minimum_valid_runs")
        if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
            errors.append("across_seeds.minimum_valid_runs must be a positive integer")
    if errors:
        raise ValueError("Invalid LossSpec: " + "; ".join(errors))


def _finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _metric_value(evaluation: Mapping[str, Any], term: Mapping[str, Any]) -> float:
    metric_id = term["metric_id"]
    metric = evaluation.get("metrics", {}).get(metric_id)
    if not isinstance(metric, dict) or metric.get("status") != "measured":
        raise ValueError(f"metric {metric_id!r} is not measured")
    slice_id = term.get("slice_id")
    if slice_id is None:
        value = metric.get("value")
    else:
        sliced = metric.get("slice_results", {}).get(slice_id)
        if not isinstance(sliced, dict) or sliced.get("status") != "measured":
            raise ValueError(f"metric {metric_id!r} slice {slice_id!r} is not measured")
        value = sliced.get("value")
    if not _finite_number(value):
        raise ValueError(f"metric {metric_id!r} does not contain a finite numeric value")
    return float(value)


def evaluate_loss(
    spec: Mapping[str, Any], evaluations: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Evaluate one design across optimization-seed run evaluations.

    Missing or unmeasured inputs reject a run from the aggregate; they are never
    converted into an arbitrary penalty. The caller is responsible for applying
    technical ``ValiditySpec`` checks before supplying evaluations.
    """

    validate_loss_spec(spec)
    per_run: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for evaluation in evaluations:
        run_id = evaluation.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            rejected.append({"run_id": None, "reason": "run_id is missing"})
            continue
        try:
            components = []
            value = float(spec["per_run"]["intercept"])
            for term in spec["per_run"]["terms"]:
                measured = _metric_value(evaluation, term)
                contribution = float(term["coefficient"]) * measured
                value += contribution
                components.append({
                    "metric_id": term["metric_id"],
                    "slice_id": term.get("slice_id"),
                    "value": measured,
                    "coefficient": float(term["coefficient"]),
                    "contribution": contribution,
                })
            if not math.isfinite(value):
                raise ValueError("per-run loss is not finite")
            per_run.append({
                "run_id": run_id,
                "loss": value,
                "components": components,
            })
        except ValueError as error:
            rejected.append({"run_id": run_id, "reason": str(error)})

    losses = [item["loss"] for item in per_run]
    minimum = spec["across_seeds"]["minimum_valid_runs"]
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "loss_spec": {
            "id": spec["id"],
            "version": spec["version"],
            "sha256": loss_spec_sha256(spec),
        },
        "valid_runs": len(losses),
        "minimum_valid_runs": minimum,
        "per_run": per_run,
        "rejected_runs": rejected,
    }
    if len(losses) < minimum:
        result.update({
            "status": "insufficient_valid_runs",
            "loss": None,
            "mean": None,
            "population_sd": None,
        })
        return result
    mean = statistics.fmean(losses)
    population_sd = statistics.pstdev(losses)
    loss = mean + float(spec["across_seeds"]["dispersion_weight"]) * population_sd
    result.update({
        "status": "complete",
        "loss": loss,
        "mean": mean,
        "population_sd": population_sd,
    })
    return result
