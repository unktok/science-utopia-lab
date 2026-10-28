"""Load and validate the plural, literature-traceable objective catalog.

The catalog is a research planning object, not an executable ``LossSpec``.
Semantic validation deliberately prevents future candidates and untouched
held-out diagnostics from being silently promoted into the active campaign.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


SCHEMA = "scienceutopia.objective-catalog.v1"
REQUIRED_CONSTRUCTS = {
    "epistemic-progress",
    "novelty",
    "robustness",
    "diversity",
    "participation",
    "efficiency",
    "public-value",
}
FROZEN_V1_LOSS_IDS = {
    "participation-review-tradeoff-probe",
    "topic-diversity-probe",
    "review-burden-probe",
}


def load_objective_catalog(
    catalog_path: str | Path, schema_path: str | Path | None = None
) -> dict[str, Any]:
    """Load a catalog and validate both its JSON shape and research semantics."""

    path = Path(catalog_path)
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if schema_path is None:
        schema_path = path.with_name("objective-catalog-v1.schema.json")
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validate_objective_catalog(catalog, schema)
    return catalog


def validate_objective_catalog(
    catalog: Mapping[str, Any], schema: Mapping[str, Any]
) -> None:
    """Fail closed on broken references, leakage, or a privileged composite."""

    errors = [
        f"schema: {error.message}"
        for error in Draft202012Validator(schema).iter_errors(catalog)
    ]
    if errors:
        raise ValueError("Invalid objective catalog: " + "; ".join(sorted(errors)))

    citations = _unique_ids(catalog["citations"], "citation", errors)
    constructs = _unique_ids(catalog["constructs"], "construct", errors)
    proposals = _unique_ids(catalog["candidate_loss_families"], "candidate loss", errors)

    missing = REQUIRED_CONSTRUCTS - constructs
    if missing:
        errors.append(f"required constructs are missing: {sorted(missing)!r}")

    for construct in catalog["constructs"]:
        prefix = f"construct {construct['id']!r}"
        _check_refs(construct["citation_refs"], citations, prefix, errors)
        proxy_ids: set[str] = set()
        for proxy in construct["observable_proxies"]:
            proxy_id = proxy["id"]
            if proxy_id in proxy_ids:
                errors.append(f"{prefix} has duplicate proxy id {proxy_id!r}")
            proxy_ids.add(proxy_id)
            _check_refs(proxy["citation_refs"], citations, f"proxy {proxy_id!r}", errors)
            relation = proxy["held_out_diagnostic_relation"]
            if relation["classification"] == "optimization_input":
                if relation["diagnostic_ids"]:
                    errors.append(
                        f"proxy {proxy_id!r} is an optimization input but names held-out "
                        "diagnostics"
                    )
                if relation["firewall"] != "allocate_new_evidence_split":
                    errors.append(
                        f"proxy {proxy_id!r} optimization input must allocate a new evidence split"
                    )

    for proposal in catalog["candidate_loss_families"]:
        prefix = f"candidate loss {proposal['id']!r}"
        if proposal["status"] != "future-campaign-proposal":
            errors.append(f"{prefix} is not future-only")
        if proposal["id"] in FROZEN_V1_LOSS_IDS:
            errors.append(f"{prefix} reuses a frozen v1 LossSpec id")
        _check_refs(proposal["construct_refs"], constructs, prefix, errors)
        _check_refs(proposal["citation_refs"], citations, prefix, errors)

    default_composites = [
        item["id"] for item in catalog["composition_strategies"] if item["default"]
    ]
    if default_composites:
        errors.append(
            "composition strategies must not designate a universal default: "
            f"{default_composites!r}"
        )

    if errors:
        raise ValueError("Invalid objective catalog: " + "; ".join(sorted(errors)))


def _unique_ids(items: list[Mapping[str, Any]], label: str, errors: list[str]) -> set[str]:
    seen: set[str] = set()
    for item in items:
        item_id = item["id"]
        if item_id in seen:
            errors.append(f"duplicate {label} id {item_id!r}")
        seen.add(item_id)
    return seen


def _check_refs(
    refs: list[str], targets: set[str], prefix: str, errors: list[str]
) -> None:
    missing = sorted(set(refs) - targets)
    if missing:
        errors.append(f"{prefix} has unresolved references {missing!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate objective catalog v1")
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--schema", type=Path)
    args = parser.parse_args()
    load_objective_catalog(args.catalog, args.schema)
    print(f"valid objective catalog: {args.catalog}")


if __name__ == "__main__":
    main()
