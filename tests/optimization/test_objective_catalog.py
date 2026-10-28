import copy
import json
from pathlib import Path

import pytest

from utopia.optimization.objective_catalog import (
    FROZEN_V1_LOSS_IDS,
    REQUIRED_CONSTRUCTS,
    load_objective_catalog,
    validate_objective_catalog,
)


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "research/objectives/catalog/objective-catalog-v1.json"
SCHEMA_PATH = ROOT / "research/objectives/catalog/objective-catalog-v1.schema.json"


def loaded():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return catalog, schema


def test_catalog_is_versioned_plural_and_loadable():
    catalog = load_objective_catalog(CATALOG_PATH)

    construct_ids = {item["id"] for item in catalog["constructs"]}
    assert REQUIRED_CONSTRUCTS <= construct_ids
    assert catalog["version"] == "1.0.0"
    assert catalog["normative_stance"]["universal_composite"] == "none"
    assert not any(item["default"] for item in catalog["composition_strategies"])


def test_future_candidates_cannot_mutate_or_reuse_frozen_loss_specs():
    catalog = load_objective_catalog(CATALOG_PATH)
    candidate_ids = {item["id"] for item in catalog["candidate_loss_families"]}

    assert candidate_ids.isdisjoint(FROZEN_V1_LOSS_IDS)
    assert {item["status"] for item in catalog["candidate_loss_families"]} == {
        "future-campaign-proposal"
    }
    for loss_id in FROZEN_V1_LOSS_IDS:
        assert (ROOT / "research/objectives/losses" / f"{loss_id}-v1.json").exists()


def test_citations_are_pinned_and_repo_local_paths_resolve():
    catalog = load_objective_catalog(CATALOG_PATH)

    for citation in catalog["citations"]:
        locator = citation["locator"]
        assert locator["section_or_lines"].strip()
        if citation["kind"] == "local-project-design":
            assert locator["commit"] == catalog["source_snapshot"]["science_utopia_commit"]
            assert (ROOT / locator["path_or_identifier"]).is_file()
        elif citation["kind"] == "local-survey-synthesis":
            assert locator["commit"] == catalog["source_snapshot"]["ai_scientist_survey_commit"]
            assert locator["url"].endswith(locator["path_or_identifier"])


def test_every_proxy_declares_fields_feasibility_goodhart_and_firewall():
    catalog = load_objective_catalog(CATALOG_PATH)

    for construct in catalog["constructs"]:
        for proxy in construct["observable_proxies"]:
            assert proxy["required_simulator_fields"]
            assert proxy["goodhart_risks"]
            assert proxy["implementation"]["next_step"]
            relation = proxy["held_out_diagnostic_relation"]
            if relation["classification"] == "optimization_input":
                assert relation["diagnostic_ids"] == []
                assert relation["firewall"] == "allocate_new_evidence_split"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda value: value["composition_strategies"][0].update(default=True),
            "universal default",
        ),
        (
            lambda value: value["constructs"][0]["citation_refs"].append("missing-source"),
            "unresolved references",
        ),
        (
            lambda value: value["candidate_loss_families"][0].update(
                id="topic-diversity-probe"
            ),
            "frozen v1",
        ),
        (
            lambda value: value["constructs"][1]["observable_proxies"][0][
                "held_out_diagnostic_relation"
            ].update(diagnostic_ids=["review-coverage"]),
            "names held-out diagnostics",
        ),
    ],
)
def test_semantic_validation_fails_closed(mutation, message):
    catalog, schema = loaded()
    invalid = copy.deepcopy(catalog)
    mutation(invalid)

    with pytest.raises(ValueError, match=message):
        validate_objective_catalog(invalid, schema)


def test_schema_rejects_missing_required_construct_metadata():
    catalog, schema = loaded()
    invalid = copy.deepcopy(catalog)
    del invalid["constructs"][0]["observable_proxies"][0]["goodhart_risks"]

    with pytest.raises(ValueError, match="goodhart_risks.*required"):
        validate_objective_catalog(invalid, schema)
