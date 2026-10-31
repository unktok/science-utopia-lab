from types import SimpleNamespace

import pytest

from utopia.optimization.generative_system import program_from_expression, seed_generative_system
from utopia.system.program_proposals import attach_generated_proposal, generate_local_proposal
from utopia.system.program_world import initial_world


def response(value):
    return SimpleNamespace(raise_for_status=lambda: None, json=lambda: value)


def test_validated_model_proposal_is_an_executable_new_custom_mechanism(monkeypatch):
    import json
    import utopia.system.program_proposals as proposals
    world = initial_world(811)
    proposal = {
        "label": "Replication commons", "rationale": "Share replicable work",
        "effects": {"learning": 0.5},
        "world": {key: world[key] for key in ("quality", "novelty", "resources", "knowledge")},
        "program": program_from_expression({"input": "knowledge"}),
    }
    monkeypatch.setattr(proposals.requests, "get", lambda *a, **k: response({
        "models": [{"name": "qwen3:8b", "digest": "abc"}],
    }))
    monkeypatch.setattr(proposals.requests, "post", lambda *a, **k: response({
        "message": {"content": json.dumps(proposal)}, "eval_count": 200,
    }))
    generated = generate_local_proposal()
    assert generated["receipt"]["model_digest"] == "abc"
    assert generated["world"]["source"]["kind"] == "local-qwen-generated-attributes"
    system = attach_generated_proposal(seed_generative_system(), generated)
    assert len(system.mechanisms) == 5
    assert system.mechanisms[-1].parameters["label"] == "Replication commons"
    assert system.mechanisms[-1].parameters["program"] == proposal["program"]


def test_invalid_model_program_never_falls_back_to_an_existing_mechanism(monkeypatch):
    import utopia.system.program_proposals as proposals
    monkeypatch.setattr(proposals.requests, "get", lambda *a, **k: response({
        "models": [{"name": "qwen3:8b", "digest": "abc"}],
    }))
    calls = []

    def invalid(*args, **kwargs):
        calls.append(1)
        return response({"message": {"content": '{"python": "print(1)"}'}})

    monkeypatch.setattr(proposals.requests, "post", invalid)
    with pytest.raises(ValueError, match="failed validation twice"):
        generate_local_proposal()
    assert len(calls) == 2

