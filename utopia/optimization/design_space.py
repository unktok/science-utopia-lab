"""Validate a bounded institutional design before launching an expensive run."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def load_space(path: str | Path) -> dict[str, Any]:
    space = _load_json(path)
    if space.get("id") not in {"evaluation-v0", "evaluation-v1"} or space.get("version") != 1:
        raise ValueError("Unsupported design-space id or version")
    variables = space.get("variables")
    if not isinstance(variables, dict) or not variables:
        raise ValueError("Design space must define variables")
    return space


def load_candidate(path: str | Path) -> dict[str, Any]:
    return _load_json(path)


def _is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def validate_candidate(space: Mapping[str, Any], candidate: Mapping[str, Any]) -> None:
    variables = space["variables"]
    missing = sorted(set(variables) - set(candidate))
    extra = sorted(set(candidate) - set(variables))
    errors = []
    if missing:
        errors.append(f"missing variables: {', '.join(missing)}")
    if extra:
        errors.append(f"unknown variables: {', '.join(extra)}")

    for name, rule in variables.items():
        if name not in candidate:
            continue
        value = candidate[name]
        kind = rule.get("type")
        if kind == "integer":
            valid_type = not isinstance(value, bool) and isinstance(value, int)
        elif kind == "float":
            valid_type = _is_number(value)
        elif kind == "categorical":
            valid_type = isinstance(value, str)
        else:
            errors.append(f"{name}: unsupported variable type {kind!r}")
            continue
        if not valid_type:
            errors.append(f"{name}: expected {kind}, got {value!r}")
            continue
        if kind in {"integer", "float"}:
            if value < rule["minimum"] or value > rule["maximum"]:
                errors.append(
                    f"{name}: {value!r} outside [{rule['minimum']}, {rule['maximum']}]"
                )
        elif value not in rule["choices"]:
            errors.append(f"{name}: {value!r} not in {rule['choices']!r}")

    if errors:
        raise ValueError("Invalid design candidate: " + "; ".join(errors))


def candidate_to_cli(space: Mapping[str, Any], candidate: Mapping[str, Any], *, years: int) -> list[str]:
    """Translate a validated v0 candidate into existing ScienceUtopia CLI flags."""
    validate_candidate(space, candidate)
    if isinstance(years, bool) or not isinstance(years, int) or years < 1:
        raise ValueError("years must be a positive integer")
    fixed = space["fixed_arguments"]
    rate_schedule = ",".join(str(candidate["acceptance_rate"]) for _ in range(years))
    flags = [
        "--experiment_name", str(fixed["experiment_name"]),
        "--population_mode", str(fixed["population_mode"]),
        "--researchers_per_institution", str(fixed["researchers_per_institution"]),
        "--funding_allocation_mode", str(fixed["funding_allocation_mode"]),
        "--funding_budget_mode", str(fixed["funding_budget_mode"]),
        "--acceptance_tiebreak", str(fixed["acceptance_tiebreak"]),
        "--acceptance_mode", str(fixed["acceptance_mode"]),
        "--rag_device", str(fixed["rag_device"]),
        "--acceptance_rate_schedule", rate_schedule,
        "--reviews_per_paper", str(candidate["reviews_per_paper"]),
        "--reviewer_capacity", str(candidate["reviewer_capacity"]),
        "--reviewer_matching", str(candidate["reviewer_matching"]),
        "--review_policy", str(candidate["review_policy"]),
        "--funding_budget_slots_frac", str(candidate["funding_budget_slots_frac"]),
        "--funding_application_cost", str(candidate["funding_application_cost"]),
        "--resubmission_cost", str(candidate["resubmission_cost"]),
    ]
    if fixed.get("population_resource_profile"):
        flags.extend([
            "--population_resource_profile", str(fixed["population_resource_profile"])
        ])
    for name in ("log_funding_applications", "log_resource_ledger"):
        if fixed.get(name):
            flags.append("--" + name)
    return flags


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", required=True, type=Path)
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--years", required=True, type=int)
    parser.add_argument("--print-cli", action="store_true")
    args = parser.parse_args(argv)
    space, candidate = load_space(args.space), load_candidate(args.design)
    flags = candidate_to_cli(space, candidate, years=args.years)
    print(json.dumps({"status": "valid", "space": space["id"], "design": candidate}, sort_keys=True))
    if args.print_cli:
        print(" ".join(flags))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

