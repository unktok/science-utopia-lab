"""Synthetic, non-experimental SystemSpec bundle for the game design console."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from typing import Any

from .model import (
    ArtifactTypeSpec,
    ChannelKind,
    ConnectionSpec,
    MechanismFamily,
    MechanismSpec,
    PortSpec,
    ScheduleSpec,
    SystemSpec,
)
from .validation import ValidationReport, validate_system_spec


SANDBOX_SCHEMA_VERSION = "scienceutopia.system-sandbox.v1"


def _mechanisms() -> tuple[MechanismSpec, ...]:
    return (
        MechanismSpec(
            "government",
            MechanismFamily.GOVERNANCE,
            "sandbox.governance.ministry-priorities-v1",
            inputs=(PortSpec("feedback", ChannelKind.SIGNAL, required=False),),
            outputs=(PortSpec("mandate", ChannelKind.CONSTRAINT),),
        ),
        MechanismSpec(
            "funding",
            MechanismFamily.FUNDING,
            "sandbox.funding.proposal-competition-v1",
            inputs=(PortSpec("mandate", ChannelKind.CONSTRAINT, required=False),),
            outputs=(PortSpec("budget", ChannelKind.RESOURCE),),
        ),
        MechanismSpec(
            "evaluation",
            MechanismFamily.EVALUATION,
            "sandbox.evaluation.peer-panel-v1",
            inputs=(
                PortSpec("mandate", ChannelKind.CONSTRAINT),
                PortSpec("budget", ChannelKind.RESOURCE),
            ),
            outputs=(PortSpec("decision", ChannelKind.DECISION),),
        ),
        MechanismSpec(
            "publication",
            MechanismFamily.PUBLICATION,
            "sandbox.publication.curated-archive-v1",
            inputs=(PortSpec("decision", ChannelKind.DECISION),),
            outputs=(PortSpec("record", ChannelKind.ARTIFACT, "publication-record"),),
        ),
        MechanismSpec(
            "communication",
            MechanismFamily.COMMUNICATION,
            "sandbox.communication.open-network-v1",
            inputs=(PortSpec("record", ChannelKind.ARTIFACT, "publication-record"),),
            outputs=(PortSpec("feedback", ChannelKind.SIGNAL),),
        ),
    )


def _connections() -> tuple[ConnectionSpec, ...]:
    return (
        ConnectionSpec("government", "mandate", "evaluation", "mandate", ChannelKind.CONSTRAINT),
        ConnectionSpec("government", "mandate", "funding", "mandate", ChannelKind.CONSTRAINT),
        ConnectionSpec("funding", "budget", "evaluation", "budget", ChannelKind.RESOURCE, 1),
        ConnectionSpec("evaluation", "decision", "publication", "decision", ChannelKind.DECISION),
        ConnectionSpec("publication", "record", "communication", "record", ChannelKind.ARTIFACT, 1),
        ConnectionSpec("communication", "feedback", "government", "feedback", ChannelKind.SIGNAL, 1),
    )


def sandbox_system_spec() -> SystemSpec:
    """Return the structurally valid starting graph; it is not an experiment."""

    return SystemSpec(
        system_id="noctiluca-synthetic-sandbox",
        version=1,
        artifact_types=(ArtifactTypeSpec("publication-record", "Synthetic publication record"),),
        mechanisms=_mechanisms(),
        connections=_connections(),
        schedules=tuple(
            ScheduleSpec(mechanism_id, phase, "annual")
            for phase, mechanism_id in enumerate(
                ("government", "funding", "evaluation", "publication", "communication")
            )
        ),
        metadata={
            "claim_boundary": "structure-only synthetic sandbox; no simulation or policy result",
            "source_kind": "synthetic_system_design_sandbox",
        },
    )


def _issues(report: ValidationReport) -> list[dict[str, str]]:
    return [
        {
            "code": issue.code,
            "path": issue.path,
            "message": issue.message,
            "severity": issue.severity,
        }
        for issue in report.issues
    ]


def _validation(spec: SystemSpec) -> dict[str, Any]:
    report = validate_system_spec(spec)
    return {"valid": report.valid, "issues": _issues(report)}


def _node_catalog() -> list[dict[str, Any]]:
    return [
        {
            "mechanism_id": "government",
            "label": "GOVERNMENT",
            "asset_key": "system_government",
            "description": "Sets constraints and receives public signals.",
            "x": 50,
            "y": 8,
            "implementations": [
                {"id": "sandbox.governance.ministry-priorities-v1", "label": "MINISTRY PRIORITIES"},
                {"id": "sandbox.governance.citizen-council-v1", "label": "CITIZEN COUNCIL"},
            ],
        },
        {
            "mechanism_id": "evaluation",
            "label": "EVALUATION",
            "asset_key": "system_evaluation",
            "description": "Converts resources and constraints into decisions.",
            "x": 50,
            "y": 42,
            "implementations": [
                {"id": "sandbox.evaluation.peer-panel-v1", "label": "PEER PANEL"},
                {"id": "sandbox.evaluation.partial-lottery-v1", "label": "PARTIAL LOTTERY"},
            ],
        },
        {
            "mechanism_id": "publication",
            "label": "PUBLICATION",
            "asset_key": "system_publication",
            "description": "Turns decisions into durable public records.",
            "x": 78,
            "y": 70,
            "implementations": [
                {"id": "sandbox.publication.curated-archive-v1", "label": "CURATED ARCHIVE"},
                {"id": "sandbox.publication.open-repository-v1", "label": "OPEN REPOSITORY"},
            ],
        },
        {
            "mechanism_id": "communication",
            "label": "COMMUNICATION",
            "asset_key": "system_communication",
            "description": "Circulates records and returns social signals.",
            "x": 22,
            "y": 70,
            "implementations": [
                {"id": "sandbox.communication.open-network-v1", "label": "OPEN NETWORK"},
                {"id": "sandbox.communication.curated-broadcast-v1", "label": "CURATED BROADCAST"},
            ],
        },
        {
            "mechanism_id": "funding",
            "label": "FUNDING",
            "asset_key": "system_funding",
            "description": "Allocates resources under optional constraints.",
            "x": 16,
            "y": 36,
            "implementations": [
                {"id": "sandbox.funding.proposal-competition-v1", "label": "PROPOSAL COMPETITION"},
                {"id": "sandbox.funding.equal-block-v1", "label": "EQUAL BLOCK GRANTS"},
            ],
        },
    ]


def _edge_catalog(spec: SystemSpec) -> list[dict[str, Any]]:
    labels = (
        "POLICY MANDATE",
        "BUDGET CONSTRAINT",
        "RESEARCH RESOURCE",
        "EVALUATION DECISION",
        "PUBLIC RECORD",
        "PUBLIC SIGNAL",
    )
    return [
        {
            "edge_id": f"edge:{index}",
            "label": label,
            "connection": connection,
            "allowed_latencies": [0, 1, 2],
        }
        for index, (label, connection) in enumerate(zip(labels, spec.to_dict()["connections"], strict=True))
    ]


def build_system_sandbox_bundle() -> dict[str, Any]:
    """Build the portable contract and Python-authoritative parity fixtures."""

    spec = sandbox_system_spec()
    base = spec.to_dict()
    disconnected = replace(
        spec,
        connections=tuple(
            edge
            for edge in spec.connections
            if not (edge.source_mechanism == "evaluation" and edge.target_mechanism == "publication")
        ),
    )
    bundle: dict[str, Any] = {
        "schema_version": SANDBOX_SCHEMA_VERSION,
        "truth_status": "synthetic",
        "source_kind": "synthetic_system_design_sandbox",
        "disclosure": (
            "SYNTHETIC SANDBOX — structure exploration only. No simulation has run, "
            "and no scientific, optimization, or policy result is shown."
        ),
        "system_spec_contract": "research/specs/system-spec-v1.schema.json",
        "validator_contract": "utopia.system.validation.validate_system_spec",
        "base_spec": base,
        "node_catalog": _node_catalog(),
        "edge_catalog": _edge_catalog(spec),
        "authoritative_fixtures": [
            {
                "id": "base-valid",
                "spec": base,
                "fingerprint": spec.fingerprint,
                "validation": _validation(spec),
            },
            {
                "id": "publication-input-disconnected",
                "spec": disconnected.to_dict(),
                "fingerprint": disconnected.fingerprint,
                "validation": _validation(disconnected),
            },
        ],
    }
    canonical = json.dumps(bundle, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    bundle["bundle_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return bundle
