from copy import deepcopy
from types import SimpleNamespace

import pytest

from utopia.system.code_proposals import propose_local_code
from utopia.system.code_mechanisms import canonical, sha


def response(value):
    return SimpleNamespace(raise_for_status=lambda: None, json=lambda: value)


def proposal():
    return {"label": "New algorithm", "rationale": "History dependent sorting",
            "source": "def step(context):\n    return {'outputs': {'out': []}, 'state': {}}",
            "additional_outputs": {}, "state_schema": {"type": "object"}}


def prepare(monkeypatch, proposals):
    calls = []
    monkeypatch.setattr("utopia.system.code_proposals.requests.get", lambda *a, **k:
                        response({"models": [{"name": "qwen3:8b", "digest": "model-hash"}]}))
    def post(*args, **kwargs):
        calls.append(deepcopy(kwargs["json"]))
        return response({"message": {"content": canonical(proposals[len(calls)-1]).decode()}})
    monkeypatch.setattr("utopia.system.code_proposals.requests.post", post)
    return calls


def test_actual_failure_repair_and_result_history(monkeypatch):
    bad = proposal()
    bad["source"] = "def wrong(context): pass"
    calls = prepare(monkeypatch, [bad, proposal()])
    history = [{"loss": -2, "accepted": 2}]
    run = propose_local_code(task="Invent", input_schemas={}, required_outputs={"out": {}},
                             history=history, validate_executable=lambda a: {"executed": True})
    assert len(calls) == 2
    assert "top-level" in calls[1]["messages"][-1]["content"]
    assert run["evidence"] == {"executed": True}
    assert run["receipt"]["history_sha256"] == sha(history)
    assert [a["status"] for a in run["attempts"]] == ["invalid", "complete"]


def test_executable_feedback_not_just_syntax(monkeypatch):
    calls = prepare(monkeypatch, [proposal(), proposal()])
    probes = []
    def probe(value):
        probes.append(value)
        if len(probes) == 1:
            raise ValueError("actual production adapter rejected missing paper_id")
        return {"production_records": 5}
    run = propose_local_code(task="Invent", input_schemas={}, required_outputs={"out": {}},
                             history=[], validate_executable=probe)
    assert "missing paper_id" in calls[1]["messages"][-1]["content"]
    assert run["evidence"]["production_records"] == 5


def test_no_fallback_after_failed_probes(monkeypatch):
    prepare(monkeypatch, [proposal()])
    def fail(value):
        raise ValueError("genuine failure")
    with pytest.raises(ValueError, match="exhausted repairs"):
        propose_local_code(task="Invent", input_schemas={}, required_outputs={"out": {}},
                           history=[], validate_executable=fail, max_attempts=1)
