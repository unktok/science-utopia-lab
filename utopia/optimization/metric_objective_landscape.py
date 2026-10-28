"""Validate the prospective Metric / Objective Landscape v1.

This artifact audits measurement choices and proposes future metric cards.  It
is intentionally not an executable LossSpec registry and cannot affect the
active metric-conditioned campaign.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


SCHEMA = "scienceutopia.metric-objective-landscape.v1"
CURRENT_LOSS_HASHES = {
    "participation-review-tradeoff-probe": "7120b365374a115aebffcf4706cd5694b90ac474a6878d54085cb2bc47431530",
    "topic-diversity-probe": "d1f8986310d7852214ef2aa14529a24a4dbeab208b783e9f5fa560c6e6aeabaf",
    "review-burden-probe": "dba135e3ea35e3b59cd57eb3f0ae82b03d83077f13c1c1253aa33e55655c1679",
}
REQUIRED_FUTURE_CONSTRUCTS = {
    "verification-weighted-epistemic-progress",
    "replication-correction-capacity",
    "possibility-portfolio",
    "disparity-aware-diversity",
    "typed-participation-and-authority",
    "distributed-process-burden",
    "verified-resource-efficiency",
    "long-horizon-capability-and-option-value",
    "mission-and-public-value",
}
FORBIDDEN_TOKENS = ("held-out seed", "held_out_seed", "heldout_seed", "registry.sqlite")


def load_metric_objective_landscape(
    landscape_path: str | Path, schema_path: str | Path | None = None
) -> dict[str, Any]:
    path = Path(landscape_path)
    landscape = json.loads(path.read_text(encoding="utf-8"))
    if schema_path is None:
        schema_path = path.with_name("metric-objective-landscape-v1.schema.json")
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validate_metric_objective_landscape(landscape, schema)
    return landscape


def validate_metric_objective_landscape(
    landscape: Mapping[str, Any], schema: Mapping[str, Any]
) -> None:
    errors = [
        f"schema: {error.message}"
        for error in Draft202012Validator(schema).iter_errors(landscape)
    ]
    if landscape.get("schema") != SCHEMA:
        errors.append(f"unexpected schema {landscape.get('schema')!r}")
    if landscape.get("governance", {}).get("active_campaign_effect") != "none":
        errors.append("active_campaign_effect must be none")
    if landscape.get("governance", {}).get("universal_composite") != "none":
        errors.append("universal_composite must be none")

    citations = _unique_ids(landscape.get("citations", []), "citation", errors)
    audits = _unique_ids(landscape.get("current_loss_audit", []), "loss audit", errors)
    cards = _unique_ids(landscape.get("metric_cards", []), "metric card", errors)
    nodes = _unique_ids(landscape.get("objective_graph", {}).get("nodes", []), "graph node", errors)
    _unique_ids(landscape.get("objective_graph", {}).get("edges", []), "graph edge", errors)

    if audits != set(CURRENT_LOSS_HASHES):
        errors.append(f"current loss audit must contain exactly {sorted(CURRENT_LOSS_HASHES)!r}")
    missing = REQUIRED_FUTURE_CONSTRUCTS - cards
    if missing:
        errors.append(f"required future constructs missing: {sorted(missing)!r}")

    for audit in landscape.get("current_loss_audit", []):
        loss_id = audit["id"]
        if audit["source_sha256"] != CURRENT_LOSS_HASHES.get(loss_id):
            errors.append(f"loss audit {loss_id!r} has a changed source hash")
        if audit["disposition"] != "contrastive-probe-not-policy-recommendation":
            errors.append(f"loss audit {loss_id!r} is not explicitly contrastive")
        _check_refs(audit["citation_refs"], citations, f"loss audit {loss_id!r}", errors)
    entropy = next((item for item in landscape.get("current_loss_audit", []) if item["id"] == "topic-diversity-probe"), None)
    if entropy and not entropy["measurement_model"].get("variety_balance_only", False):
        errors.append("topic entropy must be marked as variety/balance only")

    for card in landscape.get("metric_cards", []):
        prefix = f"metric card {card['id']!r}"
        _check_refs(card["citation_refs"], citations, prefix, errors)
        if card["campaign_role"] == "optimization-candidate" and card["promotion_boundary"] != "new-preregistered-campaign-and-evidence-split":
            errors.append(f"{prefix} lacks a new-campaign promotion boundary")

    snapshot = landscape.get("source_snapshot", {})
    for citation in landscape.get("citations", []):
        locator = citation["locator"]
        if citation["kind"] == "local-project-design":
            if locator.get("commit") != snapshot.get("science_utopia_commit"):
                errors.append(f"citation {citation['id']!r} is not pinned to the project snapshot")
        elif citation["kind"] == "local-survey-synthesis":
            if locator.get("commit") != snapshot.get("ai_scientist_survey_commit"):
                errors.append(f"citation {citation['id']!r} is not pinned to the survey snapshot")
            if not locator.get("url", "").endswith(locator["path_or_identifier"]):
                errors.append(f"citation {citation['id']!r} URL does not resolve its pinned path")

    for edge in landscape.get("objective_graph", {}).get("edges", []):
        if edge["source"] not in nodes or edge["target"] not in nodes:
            errors.append(f"graph edge {edge['id']!r} has an unresolved endpoint")
        if edge["source"] == edge["target"]:
            errors.append(f"graph edge {edge['id']!r} is a self-loop")

    serialized = json.dumps(landscape, sort_keys=True).lower()
    for token in FORBIDDEN_TOKENS:
        if token in serialized:
            errors.append(f"forbidden active/held-out token appears: {token!r}")
    if errors:
        raise ValueError("Invalid metric/objective landscape: " + "; ".join(sorted(errors)))


def verify_current_loss_sources(landscape: Mapping[str, Any], root: str | Path) -> None:
    """Verify only the versioned source LossSpecs in this checkout.

    No runtime registry, campaign worktree, or evaluation split is opened.
    """
    root_path = Path(root)
    errors: list[str] = []
    for audit in landscape["current_loss_audit"]:
        source = root_path / audit["source_path"]
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != audit["source_sha256"]:
            errors.append(f"{audit['id']}: expected {audit['source_sha256']}, got {digest}")
    if errors:
        raise ValueError("Frozen LossSpec source mismatch: " + "; ".join(errors))


def _unique_ids(items: list[Mapping[str, Any]], label: str, errors: list[str]) -> set[str]:
    seen: set[str] = set()
    for item in items:
        item_id = item["id"]
        if item_id in seen:
            errors.append(f"duplicate {label} id {item_id!r}")
        seen.add(item_id)
    return seen


def _check_refs(refs: list[str], targets: set[str], prefix: str, errors: list[str]) -> None:
    missing = sorted(set(refs) - targets)
    if missing:
        errors.append(f"{prefix} has unresolved citations {missing!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Metric / Objective Landscape v1")
    parser.add_argument("landscape", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    landscape = load_metric_objective_landscape(args.landscape, args.schema)
    if args.root:
        verify_current_loss_sources(landscape, args.root)
    print(f"valid metric/objective landscape: {args.landscape}")


if __name__ == "__main__":
    main()
