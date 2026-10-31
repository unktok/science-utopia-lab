"""Small source-code search slice over real paper-tracker state transitions.

Workload is deterministic fixture data, not a live Qwen researcher society.
The source-generating optimizer may invent algorithms, memory and extra artifact
schemas; graph wiring here is an explicit fixed integration harness.
"""
from __future__ import annotations

from typing import Any

from utopia.optimization.blackbox import Observation, Suggestion
from utopia.optimization.production_structural import production_structural_registry, production_structural_space
from utopia.system import (ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily,
                           MechanismSpec, PortSpec, ScheduleSpec, SystemSpec)
from utopia.system.code_mechanisms import (CODE_IMPLEMENTATION, DockerCodeExecutor,
                                          register_code_mechanisms, validate_code_artifact)
from utopia.system.production.publication import PAPER_TRACKER_PUBLICATION
from utopia.system.runtime import DeterministicGraphRunner, MechanismEvent, MechanismResult


INPUT_SCHEMAS = {"review_batches": {
    "type": "object", "required": ["batch_id", "papers", "reviews"],
    "properties": {"batch_id": {"type": "string"}, "papers": {
        "type": "array", "items": {"type": "object", "required": ["id", "author_id"]}},
        "reviews": {"type": "object"}},
}}
REQUIRED_OUTPUTS = {"decisions": {
    "type": "object", "required": ["batch_id", "paper_id", "decision", "paper"],
    "properties": {"batch_id": {"type": "string"}, "paper_id": {"type": "string"},
                   "decision": {"enum": ["accept", "reject"]}, "paper": {"type": "object"}},
}}


def code_lab_system(artifact: dict[str, Any], image_id: str) -> SystemSpec:
    validate_code_artifact(artifact)
    if artifact["inputs"] != INPUT_SCHEMAS or artifact["outputs"].get("decisions") != REQUIRED_OUTPUTS["decisions"]:
        raise ValueError("code lab requires paper-batch/publication compatibility ports")
    base = production_structural_space().decode(production_structural_space().sample(seed=911, proposal_index=0))
    workload = next(node for node in base.mechanisms if node.mechanism_id == "workload")
    extras = [port for port in artifact["outputs"] if port != "decisions"]
    outputs = (PortSpec("decisions", ChannelKind.DECISION, "paper-decision"), *(
        PortSpec(port, ChannelKind.ARTIFACT, "generated-" + port) for port in extras))
    inventor = MechanismSpec("invented-institution", MechanismFamily.CUSTOM, CODE_IMPLEMENTATION,
                            inputs=(PortSpec("review_batches", ChannelKind.ARTIFACT, "review-batch"),),
                            outputs=outputs, parameters={"code_artifact": artifact, "runtime_image_id": image_id})
    publisher = MechanismSpec("publication", MechanismFamily.PUBLICATION, PAPER_TRACKER_PUBLICATION,
                              inputs=(PortSpec("decisions", ChannelKind.DECISION, "paper-decision"),),
                              outputs=(PortSpec("records", ChannelKind.ARTIFACT, "publication-record"),))
    ledger = MechanismSpec("artifact-ledger", MechanismFamily.CUSTOM, "code-lab.artifact-ledger.v1",
                           inputs=tuple(PortSpec(port, ChannelKind.ARTIFACT, "generated-" + port,
                                                 required=False) for port in extras))
    return SystemSpec(
        "generated-code-lab", 1, agent_types=base.agent_types,
        artifact_types=(*base.artifact_types, *(
            ArtifactTypeSpec("generated-" + port, "LLM-invented payload schema") for port in extras)),
        mechanisms=(workload, inventor, publisher, ledger),
        connections=(ConnectionSpec("workload", "review_batches", "invented-institution", "review_batches", ChannelKind.ARTIFACT),
                     ConnectionSpec("invented-institution", "decisions", "publication", "decisions", ChannelKind.DECISION),
                     *(ConnectionSpec("invented-institution", port, "artifact-ledger", port, ChannelKind.ARTIFACT)
                       for port in extras)),
        schedules=tuple(ScheduleSpec(node.mechanism_id, index) for index, node in enumerate((workload, inventor, publisher, ledger))),
        initial_state={"seed": 911},
        metadata={"boundary": "generated-Python-to-production-PaperTracker", "workload": "deterministic-fixture"},
    )


def _ledger(context):
    records = list(context.state.get("records", []))
    events = []
    for port, values in context.inputs.items():
        for value in values:
            record = {"port": port, "period": context.period, "payload": dict(value.payload)}
            records.append(record)
            events.append(MechanismEvent("generated.artifact_recorded", payload=record))
    return MechanismResult(events=tuple(events), next_state={"records": records})


def run_code_lab(artifact: dict[str, Any], executor: DockerCodeExecutor, *, periods: int = 2,
                 checkpoint: Any = None) -> dict[str, Any]:
    spec = code_lab_system(artifact, executor.image_id)
    registry = production_structural_registry()
    receipts = []
    register_code_mechanisms(registry, executor, receipts)
    registry.register("code-lab.artifact-ledger.v1", 1, _ledger)
    result = DeterministicGraphRunner(spec, registry).run(periods=periods, checkpoint=checkpoint)
    state = result.checkpoint.mechanism_states
    counts = state.get("publication", {}).get("status_counts", {"accept": 0, "reject": 0})
    summary = {
        "accepted": counts["accept"], "rejected": counts["reject"],
        "publication_records": sum(counts.values()),
        "invented_artifacts": len(state.get("artifact-ledger", {}).get("records", [])),
        "blocked_invocations": sum(row.status == "blocked" for row in result.trace),
    }
    return {"system": spec.to_dict(), "system_fingerprint": spec.fingerprint,
            "summary": summary, "checkpoint": result.checkpoint.to_dict(),
            "events": [event.to_dict() for event in result.events],
            "event_stream_hash": result.event_stream_hash, "execution_receipts": receipts}


def code_lab_observation(suggestion: Suggestion, execution: dict[str, Any], *, objective: str) -> Observation:
    counts = execution["summary"]
    if objective == "accepted-record-count":
        loss = -float(counts["accepted"])
    elif objective == "rejected-record-count":
        loss = -float(counts["rejected"])
    else:
        raise ValueError("unknown engineering objective")
    if execution["system"] != suggestion.candidate:
        raise ValueError("execution and suggested SystemSpec differ")
    # No implicit fairness guard, scientific validity promise or acceptance veto.
    return Observation("observation-" + suggestion.suggestion_id, suggestion.suggestion_id,
                       suggestion.candidate, "complete", loss,
                       {"objective": objective, "summary": counts,
                        "event_stream_hash": execution["event_stream_hash"],
                        "system_fingerprint": execution["system_fingerprint"]})
