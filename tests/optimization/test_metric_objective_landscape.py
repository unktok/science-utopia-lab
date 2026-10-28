import copy
import json
from pathlib import Path

import pytest

from utopia.optimization.metric_objective_landscape import (
    CURRENT_LOSS_HASHES,
    REQUIRED_FUTURE_CONSTRUCTS,
    load_metric_objective_landscape,
    validate_metric_objective_landscape,
    verify_current_loss_sources,
)


ROOT = Path(__file__).resolve().parents[2]
LANDSCAPE = ROOT / "research/objectives/landscape/metric-objective-landscape-v1.json"
SCHEMA = ROOT / "research/objectives/landscape/metric-objective-landscape-v1.schema.json"


def loaded():
    return (
        json.loads(LANDSCAPE.read_text(encoding="utf-8")),
        json.loads(SCHEMA.read_text(encoding="utf-8")),
    )


def test_landscape_is_plural_prospective_and_source_pinned():
    value = load_metric_objective_landscape(LANDSCAPE)
    verify_current_loss_sources(value, ROOT)

    assert value["status"] == "prospective-report-only"
    assert value["governance"]["active_campaign_effect"] == "none"
    assert value["governance"]["universal_composite"] == "none"
    assert {item["id"] for item in value["current_loss_audit"]} == set(CURRENT_LOSS_HASHES)
    assert REQUIRED_FUTURE_CONSTRUCTS <= {item["id"] for item in value["metric_cards"]}


def test_all_current_losses_cover_construct_risks_distribution_time_and_policy():
    value = load_metric_objective_landscape(LANDSCAPE)
    for audit in value["current_loss_audit"]:
        assert audit["construct_claim"]
        assert audit["measurement_model"]["assumptions"]
        assert audit["goodhart_and_gaming"]
        assert audit["distribution"]["blind_spots"]
        assert audit["time_horizon"]["blind_spots"]
        assert audit["state_policy_relation"]["insufficient_for"]
        assert audit["disposition"] == "contrastive-probe-not-policy-recommendation"


def test_topic_entropy_is_explicitly_non_normative_and_partial():
    value = load_metric_objective_landscape(LANDSCAPE)
    entropy = next(item for item in value["current_loss_audit"] if item["id"] == "topic-diversity-probe")
    assert entropy["measurement_model"]["variety_balance_only"] is True
    assert "not scientific diversity" in entropy["measurement_model"]["valid_interpretation"]
    assert any(
        edge["source"] == "l-topic-diversity"
        and edge["target"] == "c-diversity"
        and edge["relation"] == "must-not-be-equated-with"
        for edge in value["objective_graph"]["edges"]
    )


def test_graph_references_and_future_promotion_boundaries_are_closed():
    value = load_metric_objective_landscape(LANDSCAPE)
    nodes = {item["id"] for item in value["objective_graph"]["nodes"]}
    assert all(edge["source"] in nodes and edge["target"] in nodes for edge in value["objective_graph"]["edges"])
    for card in value["metric_cards"]:
        if card["campaign_role"] == "optimization-candidate":
            assert card["promotion_boundary"] == "new-preregistered-campaign-and-evidence-split"


def test_citations_are_snapshot_pinned_and_local_project_paths_resolve():
    value = load_metric_objective_landscape(LANDSCAPE)
    for citation in value["citations"]:
        locator = citation["locator"]
        if citation["kind"] == "local-project-design":
            assert locator["commit"] == value["source_snapshot"]["science_utopia_commit"]
            assert (ROOT / locator["path_or_identifier"]).is_file()
        elif citation["kind"] == "local-survey-synthesis":
            assert locator["commit"] == value["source_snapshot"]["ai_scientist_survey_commit"]
            assert locator["url"].endswith(locator["path_or_identifier"])


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["governance"].update(active_campaign_effect="mutates-v1"), "active_campaign_effect"),
        (lambda value: value["current_loss_audit"][0].update(source_sha256="0" * 64), "changed source hash"),
        (lambda value: value["current_loss_audit"][1]["measurement_model"].update(variety_balance_only=False), "variety/balance"),
        (lambda value: value["objective_graph"]["edges"][0].update(target="missing"), "unresolved endpoint"),
        (lambda value: value["metric_cards"][0].update(promotion_boundary="remain-report-only"), "promotion boundary"),
    ],
)
def test_semantic_validator_fails_closed(mutation, message):
    value, schema = loaded()
    invalid = copy.deepcopy(value)
    mutation(invalid)
    with pytest.raises(ValueError, match=message):
        validate_metric_objective_landscape(invalid, schema)


def test_artifact_does_not_name_runtime_or_reserved_seed_material():
    serialized = LANDSCAPE.read_text(encoding="utf-8").lower()
    assert "registry.sqlite" not in serialized
    assert "held_out_seed" not in serialized
    assert "heldout_seed" not in serialized

