"""Offline tamper rejection for recorded generated-source evidence."""
from copy import deepcopy
import json

import pytest

from scripts.reports.code_mechanism_lab import verify_run
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.code_lab import (INPUT_SCHEMAS, REQUIRED_OUTPUTS, code_lab_observation,
                                          code_lab_system)
from utopia.system.code_mechanisms import CODE_SCHEMA, canonical, sha
from utopia.replay.events import EventEnvelope


def fixture_report():
    # Entirely synthetic evidence fixture: no claim these are model proposals.
    image = "sha256:" + "1" * 64
    artifact = {"schema": CODE_SCHEMA, "label": "Synthetic evidence fixture",
                "source": "def step(context):\n    return {'outputs': {'decisions': []}, 'state': {}}",
                "inputs": INPUT_SCHEMAS, "outputs": REQUIRED_OUTPUTS, "state_schema": {"type": "object"}}
    spec = code_lab_system(artifact, image)
    receipts = [{"image_id": image, "artifact_sha256": sha(artifact),
                 "context_sha256": "context-" + str(period), "result_sha256": "result-" + str(period),
                 "period": period, "mechanism_id": "invented-institution", "wall_seconds": 0.1}
                for period in range(2)]
    events = [EventEnvelope.create(sequence=i, year=i, phase=1, event_type="generated.code_executed",
                                   payload={k: r[k] for k in ("image_id", "artifact_sha256", "context_sha256", "result_sha256")}).to_dict()
              for i, r in enumerate(receipts)]
    evidence = {"system": spec.to_dict(), "system_fingerprint": spec.fingerprint,
                "checkpoint": {"system_fingerprint": spec.fingerprint, "mechanism_states": {
                    "publication": {"status_counts": {"accept": 0, "reject": 0}}}},
                "summary": {"accepted": 0, "rejected": 0, "publication_records": 0,
                            "invented_artifacts": 0, "blocked_invocations": 0},
                "events": events, "event_stream_hash": sha(events), "execution_receipts": receipts}
    def proposal(history):
        request = {"messages": [{"role": "user", "content": "PREVIOUS ACTUAL OBSERVATIONS:\n" + json.dumps(history)}]}
        raw = {"message": {"content": canonical({"source": artifact["source"], "label": artifact["label"],
                                                "state_schema": artifact["state_schema"], "new_port_schemas": {},
                                                "rationale": "test fixture"}).decode()}}
        receipt = {"request_sha256": sha(request), "response_sha256": sha(raw), "history_sha256": sha(history)}
        return {"artifact": artifact, "rationale": "test fixture", "receipt": receipt,
                "attempts": [{"request": request, "response": raw, "receipt": receipt, "status": "complete"}],
                "evidence": evidence}
    report = {"schema": "scienceutopia.generated-code-lab.v1", "dirty_development": False,
              "image_id": image, "proposals": [proposal([])], "rounds": []}
    for objective in ("accepted-record-count", "rejected-record-count"):
        initial = Suggestion("initial-" + objective, spec.to_dict(), 0, "initial")
        observed = code_lab_observation(initial, evidence, objective=objective)
        revised = Suggestion("revision-" + objective, spec.to_dict(), 1, "revision", observed.observation_id)
        outcome = code_lab_observation(revised, evidence, objective=objective)
        history = [{"source": artifact["source"], "artifact": artifact, "observation": observed.to_dict()}]
        report["proposals"].append(proposal(history))
        report["rounds"].append({"objective": objective, "observations": [observed.to_dict(), outcome.to_dict()],
                                 "suggestions": [initial.to_dict(), revised.to_dict()],
                                 "replay_passed": True, "checkpoint_resume_passed": True})
    return deepcopy(report)


def test_offline_provenance_verification():
    verify_run(fixture_report())


@pytest.mark.parametrize("tamper", ["source", "request", "loss", "state", "events", "image", "history"])
def test_reject_tampered_evidence(tamper):
    report = fixture_report()
    if tamper == "source":
        report["proposals"][0]["artifact"]["source"] += "\n# altered"
    elif tamper == "request":
        report["proposals"][0]["attempts"][0]["request"]["changed"] = True
    elif tamper == "loss":
        report["rounds"][0]["observations"][0]["loss"] = -1000
    elif tamper == "state":
        report["proposals"][0]["evidence"]["checkpoint"]["mechanism_states"]["publication"]["status_counts"]["accept"] = 3
    elif tamper == "events":
        report["proposals"][0]["evidence"]["events"][0]["payload"]["fabricated"] = True
    elif tamper == "image":
        report["image_id"] = "different-image"
    else:
        report["rounds"][0]["suggestions"][1]["based_on_observation_id"] = "unobserved"
    with pytest.raises(ValueError):
        verify_run(report)
