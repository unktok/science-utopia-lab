"""Verified simulator-campaign workloads for the generic mechanism graph."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from utopia.replay.converter import ArtifactBundle, convert_artifacts
from utopia.replay.events import (
    SCHEMA_VERSION as EVENT_SCHEMA_VERSION,
    EventEnvelope,
    canonical_event_stream_hash,
    validate_references,
)
from utopia.system.model import (
    ArtifactTypeSpec,
    ChannelKind,
    ConnectionSpec,
    MechanismFamily,
    MechanismSpec,
    PortSpec,
    ScheduleSpec,
    SystemSpec,
)
from utopia.system.runtime import (
    DeliveredValue,
    GraphRuntimeError,
    MechanismContext,
    MechanismEvent,
    MechanismRegistry,
    MechanismResult,
    MechanismValue,
)
from utopia.system.validation import validate_system_spec


SIMULATOR_WORKLOAD_BRIDGE = "production.workload.simulator-campaign-bridge-v1"
SIMULATOR_EVENT_RECEIVER = "production.workload.simulator-event-receiver-v1"
CAMPAIGN_SOURCE_SCHEMA_VERSION = "scienceutopia.game-campaign-source.v1"
CAMPAIGN_BUNDLE_SCHEMA_VERSION = "scienceutopia.simulator-campaign-bundle.v1"
EVENT_BATCH_SCHEMA_VERSION = "scienceutopia.simulator-event-batch.v1"
BRIDGE_STATE_SCHEMA_VERSION = "scienceutopia.simulator-bridge-state.v1"
RECEIVER_STATE_SCHEMA_VERSION = "scienceutopia.simulator-receiver-state.v1"

_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_COMMIT = re.compile(r"[0-9a-f]{40}")
_CONSUMER_FAMILIES = (
    MechanismFamily.EVALUATION,
    MechanismFamily.PUBLICATION,
    MechanismFamily.FUNDING,
    MechanismFamily.GOVERNANCE,
    MechanismFamily.COMMUNICATION,
)


@dataclass(frozen=True)
class SimulatorCampaignBundle:
    """Relocatable verified campaign identity plus canonical source events."""

    campaign_id: str
    campaign_revision: str
    run_id: str
    seed: int
    source_commit: str
    protocol_tag: str
    source_manifest_sha256: str
    source_file_sha256: Mapping[str, str]
    event_stream_hash: str
    events: tuple[EventEnvelope, ...]
    claim_boundary: str
    schema_version: str = CAMPAIGN_BUNDLE_SCHEMA_VERSION

    def identity_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "campaign_id": self.campaign_id,
            "campaign_revision": self.campaign_revision,
            "run_id": self.run_id,
            "seed": self.seed,
            "source_commit": self.source_commit,
            "protocol_tag": self.protocol_tag,
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_file_sha256": dict(sorted(self.source_file_sha256.items())),
            "event_stream_hash": self.event_stream_hash,
        }

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.identity_dict())


def load_verified_simulator_campaign(
    source_manifest: Path,
    campaign_root: Path,
    project_root: Path,
) -> SimulatorCampaignBundle:
    """Read and verify a frozen simulator campaign without modifying it."""

    source = _read_json_object(source_manifest, "campaign source manifest")
    required_source = {
        "schema_version",
        "status",
        "campaign_id",
        "campaign_revision",
        "source_commit",
        "protocol_tag",
        "campaign_result",
        "run",
        "files",
        "claim_boundary",
    }
    if set(source) != required_source:
        raise GraphRuntimeError("campaign source fields do not match v1 schema")
    if source.get("schema_version") != CAMPAIGN_SOURCE_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported campaign source schema")
    if source.get("status") != "completed":
        raise GraphRuntimeError("simulator campaign source is not complete")
    commit = _git_commit(source.get("source_commit"), "source_commit")
    run = _mapping(source.get("run"), "campaign source run")
    if set(run) != {"id", "suggestion_id", "seed", "status"}:
        raise GraphRuntimeError("campaign source run fields do not match v1 schema")
    if run.get("status") != "complete":
        raise GraphRuntimeError("selected simulator campaign run is not complete")
    seed = run.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise GraphRuntimeError("campaign source seed must be a non-negative integer")
    campaign_result_path = _checked_file(
        project_root,
        source.get("campaign_result"),
        "campaign_result",
    )
    result = _read_json_object(campaign_result_path, "campaign result")
    campaign = _mapping(result.get("campaign"), "campaign result campaign")
    if (
        campaign.get("id") != source.get("campaign_id")
        or campaign.get("revision") != source.get("campaign_revision")
        or campaign.get("source_commit") != commit
        or not campaign.get("completed_utc")
    ):
        raise GraphRuntimeError("completed campaign result identity does not match source")
    suggestion = next(
        (
            row
            for row in result.get("suggestions", [])
            if isinstance(row, Mapping)
            and row.get("suggestion_id") == run.get("suggestion_id")
        ),
        None,
    )
    if not isinstance(suggestion, Mapping) or suggestion.get("status") != "complete":
        raise GraphRuntimeError("selected simulator suggestion is not complete")
    run_result = next(
        (
            row
            for row in suggestion.get("runs", [])
            if isinstance(row, Mapping)
            and row.get("run_id") == run.get("id")
            and row.get("seed") == seed
        ),
        None,
    )
    if run_result is None:
        raise GraphRuntimeError("selected simulator run is absent from campaign result")

    files = _mapping(source.get("files"), "campaign source files")
    required_files = {
        "run_manifest",
        "integrity",
        "checkpoint",
        "resource_ledger",
        "resource_balances",
    }
    if set(files) != required_files:
        raise GraphRuntimeError("campaign source files do not match v1 schema")
    paths = {
        name: _checked_file(campaign_root, files[name], f"files.{name}")
        for name in sorted(required_files)
    }
    run_manifest = _read_json_object(paths["run_manifest"], "run manifest")
    args = _mapping(run_manifest.get("args"), "run manifest args")
    if (
        run_manifest.get("status") != "complete"
        or run_manifest.get("git_commit") != commit
        or run_manifest.get("git_dirty_files") not in ("", [])
        or args.get("run_id") != run.get("id")
        or args.get("seed") != seed
    ):
        raise GraphRuntimeError("native simulator run manifest identity is invalid")
    try:
        with paths["integrity"].open(encoding="utf-8") as stream:
            integrity = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        raise GraphRuntimeError(f"cannot read simulator integrity report: {error}") from error
    if (
        not isinstance(integrity, list)
        or not integrity
        or any(
            not isinstance(row, Mapping)
            or not row.get("passed")
            or row.get("failures")
            for row in integrity
        )
    ):
        raise GraphRuntimeError("native simulator integrity report did not pass")
    try:
        events = tuple(
            convert_artifacts(
                ArtifactBundle(
                    checkpoint=paths["checkpoint"],
                    resource_ledger=paths["resource_ledger"],
                    resource_balances=paths["resource_balances"],
                )
            )
        )
    except (OSError, TypeError, ValueError) as error:
        raise GraphRuntimeError(f"cannot convert simulator campaign: {error}") from error
    if not events:
        raise GraphRuntimeError("verified simulator campaign has no canonical events")
    events = tuple(
        _parse_canonical_event(event.to_dict(), expected_sequence=index)
        for index, event in enumerate(events)
    )
    event_ids = [event.event_id for event in events]
    if len(event_ids) != len(set(event_ids)):
        raise GraphRuntimeError("verified simulator event ids are duplicated")
    reference_errors = validate_references(events)
    if reference_errors:
        raise GraphRuntimeError(
            "verified simulator event references are invalid: " + reference_errors[0]
        )
    stream_hash = canonical_event_stream_hash(events)
    normalized_hashes = {
        name: _sha256(_mapping(files[name], name).get("sha256"), f"{name} hash")
        for name in sorted(files)
    }
    bundle = SimulatorCampaignBundle(
        campaign_id=_nonempty_string(source.get("campaign_id"), "campaign_id"),
        campaign_revision=_nonempty_string(
            source.get("campaign_revision"), "campaign_revision"
        ),
        run_id=_nonempty_string(run.get("id"), "run id"),
        seed=seed,
        source_commit=commit,
        protocol_tag=_nonempty_string(source.get("protocol_tag"), "protocol_tag"),
        source_manifest_sha256=_file_sha256(source_manifest),
        source_file_sha256=normalized_hashes,
        event_stream_hash=_sha256(stream_hash, "event stream hash"),
        events=events,
        claim_boundary=_nonempty_string(
            source.get("claim_boundary"), "claim_boundary"
        ),
    )
    return bundle


def register_simulator_workload_bridge(
    registry: MechanismRegistry,
    bundle: SimulatorCampaignBundle,
) -> None:
    """Register one campaign-bound source and its generic typed receiver."""

    registry.register(
        SIMULATOR_WORKLOAD_BRIDGE,
        1,
        lambda context: simulator_workload_bridge(context, bundle),
    )
    registry.register(SIMULATOR_EVENT_RECEIVER, 1, simulator_event_receiver)


def simulator_bridge_system_spec(
    bundle: SimulatorCampaignBundle,
    *,
    batch_size: int = 16,
    latencies: Mapping[str, int] | None = None,
) -> SystemSpec:
    """Build a five-family executable graph over one verified campaign."""

    normalized_batch_size = _positive_int(batch_size, "batch_size")
    latency_values = {
        "evaluation": 0,
        "publication": 1,
        "funding": 1,
        "governance": 2,
        "communication": 0,
    }
    if latencies is not None:
        if set(latencies) != set(latency_values):
            raise GraphRuntimeError("simulator bridge latencies require all five families")
        latency_values = {
            key: _nonnegative_int(value, f"{key} latency")
            for key, value in latencies.items()
        }
    bridge_parameters = {
        "campaign_fingerprint": bundle.fingerprint,
        "event_stream_hash": bundle.event_stream_hash,
        "batch_size": normalized_batch_size,
    }
    bridge = MechanismSpec(
        "simulator-bridge",
        MechanismFamily.CUSTOM,
        SIMULATOR_WORKLOAD_BRIDGE,
        outputs=(
            PortSpec(
                "event_batches",
                ChannelKind.SIGNAL,
                "simulator-event-batch",
                required=False,
            ),
        ),
        parameters=bridge_parameters,
    )
    consumers = tuple(
        MechanismSpec(
            f"{family.value}-simulator-consumer",
            family,
            SIMULATOR_EVENT_RECEIVER,
            inputs=(
                PortSpec(
                    "event_batches",
                    ChannelKind.SIGNAL,
                    "simulator-event-batch",
                    required=False,
                ),
            ),
            parameters={
                "campaign_fingerprint": bundle.fingerprint,
                "event_stream_hash": bundle.event_stream_hash,
                "source_bridge_id": "simulator-bridge",
                "receiver_role": family.value,
            },
        )
        for family in _CONSUMER_FAMILIES
    )
    spec = SystemSpec(
        system_id="simulator-backed-mechanism-graph",
        version=1,
        artifact_types=(ArtifactTypeSpec("simulator-event-batch"),),
        mechanisms=(bridge, *consumers),
        connections=tuple(
            ConnectionSpec(
                "simulator-bridge",
                "event_batches",
                consumer.mechanism_id,
                "event_batches",
                ChannelKind.SIGNAL,
                latency=latency_values[consumer.family.value],
            )
            for consumer in consumers
        ),
        schedules=(
            ScheduleSpec("simulator-bridge", 0),
            *(
                ScheduleSpec(consumer.mechanism_id, 1)
                for consumer in consumers
            ),
        ),
        global_invariants=(
            "verified-simulator-campaign-fingerprint",
            "canonical-source-event-identity",
            "graph-local-causal-lineage",
            "fingerprint-bound-checkpoints",
        ),
        metadata={
            "purpose": "simulator-backed-workload-bridge",
            "campaign_fingerprint": bundle.fingerprint,
            "source_event_stream_hash": bundle.event_stream_hash,
            "scientific_preference": "not-defined",
        },
    )
    validate_system_spec(spec).require_valid()
    return spec


def simulator_workload_bridge(
    context: MechanismContext,
    bundle: SimulatorCampaignBundle,
) -> MechanismResult:
    """Emit the next verified source-event batch into a generic graph."""

    batch_size = _verify_bridge_parameters(context.mechanism.parameters, bundle)
    state = _restore_bridge_state(context.state, bundle, batch_size)
    if state["next_source_index"] == len(bundle.events):
        return MechanismResult(next_state=state)
    start = state["next_source_index"]
    end = min(len(bundle.events), start + batch_size)
    source_events = bundle.events[start:end]
    sequence = state["next_batch_sequence"]
    batch = _build_event_batch(
        context,
        bundle,
        source_events,
        sequence=sequence,
        start=start,
        end=end,
    )
    state["next_source_index"] = end
    state["next_batch_sequence"] += 1
    state["emitted_batch_ids"].append(batch["batch_id"])
    state["emitted_source_event_ids"].extend(batch["source_event_ids"])
    state["complete"] = end == len(bundle.events)
    state["last_batch_fingerprint"] = _fingerprint(batch)
    return MechanismResult(
        outputs={
            "event_batches": (
                MechanismValue(batch, artifact_ids=(batch["batch_id"],)),
            )
        },
        events=(
            MechanismEvent(
                "simulator.workload_batch_emitted",
                artifact_ids=(batch["batch_id"],),
                payload={
                    "batch_id": batch["batch_id"],
                    "batch_sequence": sequence,
                    "campaign_fingerprint": bundle.fingerprint,
                    "source_start_index": start,
                    "source_end_index": end,
                    "source_event_ids": batch["source_event_ids"],
                },
                provenance={
                    "production_adapter": SIMULATOR_WORKLOAD_BRIDGE,
                    "source_event_stream_hash": bundle.event_stream_hash,
                    "source_commit": bundle.source_commit,
                },
            ),
        ),
        next_state=state,
    )


def simulator_event_receiver(context: MechanismContext) -> MechanismResult:
    """Receive contiguous simulator batches with fail-closed provenance."""

    expected = _receiver_parameters(context.mechanism.parameters)
    state = _restore_receiver_state(context.state, expected)
    events: list[MechanismEvent] = []
    for delivered in context.inputs.get("event_batches", ()):
        batch = validate_delivered_event_batch(
            delivered,
            system_fingerprint=context.system_fingerprint,
            campaign_fingerprint=expected["campaign_fingerprint"],
            event_stream_hash=expected["event_stream_hash"],
            source_bridge_id=expected["source_bridge_id"],
        )
        if batch["batch_sequence"] != state["next_batch_sequence"]:
            raise GraphRuntimeError("simulator batch sequence is stale, skipped, or replayed")
        if batch["source_start_index"] != state["next_source_index"]:
            raise GraphRuntimeError("simulator source event range is not contiguous")
        if batch["batch_id"] in state["received_batch_ids"]:
            raise GraphRuntimeError("simulator batch id was already received")
        prior_event_ids = set(state["received_source_event_ids"])
        if any(event_id in prior_event_ids for event_id in batch["source_event_ids"]):
            raise GraphRuntimeError("simulator source event was already received")
        state["received_batch_ids"].append(batch["batch_id"])
        state["received_source_event_ids"].extend(batch["source_event_ids"])
        state["next_source_index"] = batch["source_end_index"]
        state["next_batch_sequence"] += 1
        for source_event in batch["source_events"]:
            event_type = source_event["event_type"]
            state["event_type_counts"][event_type] = (
                state["event_type_counts"].get(event_type, 0) + 1
            )
        events.append(
            MechanismEvent(
                "simulator.workload_batch_received",
                artifact_ids=(batch["batch_id"],),
                payload={
                    "batch_id": batch["batch_id"],
                    "batch_sequence": batch["batch_sequence"],
                    "receiver_role": expected["receiver_role"],
                    "source_event_count": len(batch["source_events"]),
                    "source_event_ids": batch["source_event_ids"],
                    "event_types": sorted(
                        {event["event_type"] for event in batch["source_events"]}
                    ),
                },
                provenance={
                    "production_adapter": SIMULATOR_EVENT_RECEIVER,
                    "campaign_fingerprint": batch["campaign_fingerprint"],
                    "source_event_stream_hash": batch["source_event_stream_hash"],
                },
            )
        )
    return MechanismResult(events=tuple(events), next_state=state)


def parse_simulator_event_batch(value: Mapping[str, Any]) -> dict[str, Any]:
    """Parse an exact simulator-event-batch v1 envelope."""

    if not isinstance(value, Mapping):
        raise GraphRuntimeError("simulator event batch must be a mapping")
    required = {
        "schema_version",
        "batch_id",
        "batch_sequence",
        "sender_id",
        "campaign_id",
        "campaign_revision",
        "run_id",
        "source_commit",
        "campaign_fingerprint",
        "source_event_stream_hash",
        "target_system_fingerprint",
        "graph_emitted_period",
        "source_start_index",
        "source_end_index",
        "source_event_ids",
        "source_events",
    }
    if set(value) != required:
        raise GraphRuntimeError("simulator event batch fields do not match v1 schema")
    if value.get("schema_version") != EVENT_BATCH_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported simulator event batch schema")
    for key in ("batch_id", "sender_id", "campaign_id", "campaign_revision", "run_id"):
        _nonempty_string(value[key], f"simulator batch {key}")
    _git_commit(value["source_commit"], "simulator batch source_commit")
    for key in (
        "campaign_fingerprint",
        "source_event_stream_hash",
        "target_system_fingerprint",
    ):
        _sha256(value[key], f"simulator batch {key}")
    _positive_int(value["batch_sequence"], "simulator batch sequence")
    _nonnegative_int(value["graph_emitted_period"], "graph emitted period")
    start = _nonnegative_int(value["source_start_index"], "source start index")
    end = _positive_int(value["source_end_index"], "source end index")
    if end <= start:
        raise GraphRuntimeError("simulator source event range must be non-empty")
    raw_events = value["source_events"]
    if not isinstance(raw_events, list) or len(raw_events) != end - start:
        raise GraphRuntimeError("simulator source event count does not match range")
    source_events = [
        _parse_canonical_event(row, expected_sequence=start + offset).to_dict()
        for offset, row in enumerate(raw_events)
    ]
    source_event_ids = value["source_event_ids"]
    expected_ids = [event["event_id"] for event in source_events]
    if source_event_ids != expected_ids:
        raise GraphRuntimeError("simulator source event ids do not match event payloads")
    if len(expected_ids) != len(set(expected_ids)):
        raise GraphRuntimeError("simulator event batch contains duplicate source events")
    result = deepcopy(dict(value))
    result["source_events"] = source_events
    _strict_json(result, "simulator event batch")
    return result


def validate_delivered_event_batch(
    delivered: DeliveredValue,
    *,
    system_fingerprint: str,
    campaign_fingerprint: str,
    event_stream_hash: str,
    source_bridge_id: str,
) -> dict[str, Any]:
    """Cross-check a batch against runner-owned delivery and graph identity."""

    batch = parse_simulator_event_batch(delivered.payload)
    if (
        delivered.channel != ChannelKind.SIGNAL
        or delivered.artifact_type != "simulator-event-batch"
    ):
        raise GraphRuntimeError("simulator event batch delivery type is invalid")
    if batch["target_system_fingerprint"] != system_fingerprint:
        raise GraphRuntimeError("simulator batch belongs to a different target system")
    if batch["campaign_fingerprint"] != campaign_fingerprint:
        raise GraphRuntimeError("simulator batch belongs to a different campaign")
    if batch["source_event_stream_hash"] != event_stream_hash:
        raise GraphRuntimeError("simulator batch source stream does not match consumer")
    if batch["sender_id"] != source_bridge_id:
        raise GraphRuntimeError("simulator batch sender does not match expected bridge")
    if delivered.source_mechanism != batch["sender_id"]:
        raise GraphRuntimeError("simulator batch sender does not match delivery source")
    if delivered.emitted_period != batch["graph_emitted_period"]:
        raise GraphRuntimeError("simulator batch period does not match delivery")
    if delivered.artifact_ids != (batch["batch_id"],):
        raise GraphRuntimeError("simulator batch artifact does not match payload")
    if not delivered.lineage_event_ids:
        raise GraphRuntimeError("simulator batch requires graph-local event lineage")
    return batch


def _build_event_batch(
    context: MechanismContext,
    bundle: SimulatorCampaignBundle,
    source_events: Sequence[EventEnvelope],
    *,
    sequence: int,
    start: int,
    end: int,
) -> dict[str, Any]:
    body = {
        "schema_version": EVENT_BATCH_SCHEMA_VERSION,
        "batch_id": "pending",
        "batch_sequence": sequence,
        "sender_id": context.mechanism.mechanism_id,
        "campaign_id": bundle.campaign_id,
        "campaign_revision": bundle.campaign_revision,
        "run_id": bundle.run_id,
        "source_commit": bundle.source_commit,
        "campaign_fingerprint": bundle.fingerprint,
        "source_event_stream_hash": bundle.event_stream_hash,
        "target_system_fingerprint": context.system_fingerprint,
        "graph_emitted_period": context.period,
        "source_start_index": start,
        "source_end_index": end,
        "source_event_ids": [event.event_id for event in source_events],
        "source_events": [event.to_dict() for event in source_events],
    }
    digest = _fingerprint({key: value for key, value in body.items() if key != "batch_id"})
    body["batch_id"] = (
        f"{context.mechanism.mechanism_id}-b{sequence}-{digest[:12]}"
    )
    return parse_simulator_event_batch(body)


def _verify_bridge_parameters(
    parameters: Mapping[str, Any],
    bundle: SimulatorCampaignBundle,
) -> int:
    required = {"campaign_fingerprint", "event_stream_hash", "batch_size"}
    if set(parameters) != required:
        raise GraphRuntimeError("simulator bridge parameters do not match v1 schema")
    if parameters["campaign_fingerprint"] != bundle.fingerprint:
        raise GraphRuntimeError("simulator bridge campaign fingerprint mismatch")
    if parameters["event_stream_hash"] != bundle.event_stream_hash:
        raise GraphRuntimeError("simulator bridge source event stream mismatch")
    return _positive_int(parameters["batch_size"], "simulator bridge batch_size")


def _receiver_parameters(parameters: Mapping[str, Any]) -> dict[str, str]:
    required = {
        "campaign_fingerprint",
        "event_stream_hash",
        "source_bridge_id",
        "receiver_role",
    }
    if set(parameters) != required:
        raise GraphRuntimeError("simulator receiver parameters do not match v1 schema")
    return {
        "campaign_fingerprint": _sha256(
            parameters["campaign_fingerprint"], "receiver campaign fingerprint"
        ),
        "event_stream_hash": _sha256(
            parameters["event_stream_hash"], "receiver event stream hash"
        ),
        "source_bridge_id": _nonempty_string(
            parameters["source_bridge_id"], "receiver source bridge id"
        ),
        "receiver_role": _nonempty_string(
            parameters["receiver_role"], "receiver role"
        ),
    }


def _restore_bridge_state(
    raw: Mapping[str, Any],
    bundle: SimulatorCampaignBundle,
    batch_size: int,
) -> dict[str, Any]:
    if not raw:
        return {
            "schema_version": BRIDGE_STATE_SCHEMA_VERSION,
            "campaign_fingerprint": bundle.fingerprint,
            "event_stream_hash": bundle.event_stream_hash,
            "batch_size": batch_size,
            "next_source_index": 0,
            "next_batch_sequence": 1,
            "emitted_batch_ids": [],
            "emitted_source_event_ids": [],
            "complete": False,
            "last_batch_fingerprint": None,
        }
    required = {
        "schema_version",
        "campaign_fingerprint",
        "event_stream_hash",
        "batch_size",
        "next_source_index",
        "next_batch_sequence",
        "emitted_batch_ids",
        "emitted_source_event_ids",
        "complete",
        "last_batch_fingerprint",
    }
    if set(raw) != required or raw.get("schema_version") != BRIDGE_STATE_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported simulator bridge state")
    if (
        raw["campaign_fingerprint"] != bundle.fingerprint
        or raw["event_stream_hash"] != bundle.event_stream_hash
        or raw["batch_size"] != batch_size
    ):
        raise GraphRuntimeError("simulator bridge state source binding changed")
    index = _nonnegative_int(raw["next_source_index"], "bridge source index")
    if index > len(bundle.events):
        raise GraphRuntimeError("simulator bridge source index exceeds event stream")
    sequence = _positive_int(raw["next_batch_sequence"], "bridge batch sequence")
    batch_ids = _unique_strings(raw["emitted_batch_ids"], "bridge batch ids")
    event_ids = _unique_strings(
        raw["emitted_source_event_ids"], "bridge source event ids"
    )
    if sequence != len(batch_ids) + 1:
        raise GraphRuntimeError("simulator bridge batch cursor is inconsistent")
    expected_batch_count = (index + batch_size - 1) // batch_size if index else 0
    if len(batch_ids) != expected_batch_count:
        raise GraphRuntimeError("simulator bridge batch count is inconsistent")
    if index < len(bundle.events) and index % batch_size:
        raise GraphRuntimeError("simulator bridge partial cursor is not terminal")
    expected_event_ids = [event.event_id for event in bundle.events[:index]]
    if event_ids != expected_event_ids:
        raise GraphRuntimeError("simulator bridge source cursor is inconsistent")
    if type(raw["complete"]) is not bool or raw["complete"] != (index == len(bundle.events)):
        raise GraphRuntimeError("simulator bridge completion state is inconsistent")
    fingerprint = raw["last_batch_fingerprint"]
    if fingerprint is not None:
        _sha256(fingerprint, "bridge last batch fingerprint")
    if bool(batch_ids) != (fingerprint is not None):
        raise GraphRuntimeError("simulator bridge batch fingerprint is inconsistent")
    return deepcopy(dict(raw))


def _restore_receiver_state(
    raw: Mapping[str, Any],
    expected: Mapping[str, str],
) -> dict[str, Any]:
    if not raw:
        return {
            "schema_version": RECEIVER_STATE_SCHEMA_VERSION,
            "campaign_fingerprint": expected["campaign_fingerprint"],
            "event_stream_hash": expected["event_stream_hash"],
            "source_bridge_id": expected["source_bridge_id"],
            "next_source_index": 0,
            "next_batch_sequence": 1,
            "received_batch_ids": [],
            "received_source_event_ids": [],
            "event_type_counts": {},
        }
    required = {
        "schema_version",
        "campaign_fingerprint",
        "event_stream_hash",
        "source_bridge_id",
        "next_source_index",
        "next_batch_sequence",
        "received_batch_ids",
        "received_source_event_ids",
        "event_type_counts",
    }
    if set(raw) != required or raw.get("schema_version") != RECEIVER_STATE_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported simulator receiver state")
    for key in ("campaign_fingerprint", "event_stream_hash", "source_bridge_id"):
        if raw[key] != expected[key]:
            raise GraphRuntimeError("simulator receiver state source binding changed")
    index = _nonnegative_int(raw["next_source_index"], "receiver source index")
    sequence = _positive_int(raw["next_batch_sequence"], "receiver batch sequence")
    batch_ids = _unique_strings(raw["received_batch_ids"], "received batch ids")
    event_ids = _unique_strings(
        raw["received_source_event_ids"], "received source event ids"
    )
    if sequence != len(batch_ids) + 1 or index != len(event_ids):
        raise GraphRuntimeError("simulator receiver cursors are inconsistent")
    counts = raw["event_type_counts"]
    if not isinstance(counts, Mapping) or any(
        not isinstance(key, str)
        or not key
        or isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        for key, value in counts.items()
    ):
        raise GraphRuntimeError("simulator receiver event counts are invalid")
    if sum(counts.values()) != len(event_ids):
        raise GraphRuntimeError("simulator receiver event counts are inconsistent")
    return deepcopy(dict(raw))


def _parse_canonical_event(value: Any, *, expected_sequence: int) -> EventEnvelope:
    if not isinstance(value, Mapping):
        raise GraphRuntimeError("canonical source event must be a mapping")
    required = {
        "schema_version",
        "event_id",
        "sequence",
        "year",
        "phase",
        "event_type",
        "actor_ids",
        "artifact_ids",
        "payload",
        "provenance",
    }
    if set(value) != required or value.get("schema_version") != EVENT_SCHEMA_VERSION:
        raise GraphRuntimeError("canonical source event fields do not match v1 schema")
    sequence = _nonnegative_int(value.get("sequence"), "canonical event sequence")
    if sequence != expected_sequence:
        raise GraphRuntimeError("canonical source event sequence is not contiguous")
    year = _nonnegative_int(value.get("year"), "canonical event year")
    phase = _nonnegative_int(value.get("phase"), "canonical event phase")
    event_type = _nonempty_string(value.get("event_type"), "canonical event type")
    actor_ids = _string_ids(value.get("actor_ids"), "canonical event actor ids")
    artifact_ids = _string_ids(
        value.get("artifact_ids"), "canonical event artifact ids"
    )
    payload = _mapping(value.get("payload"), "canonical event payload")
    provenance = _mapping(value.get("provenance"), "canonical event provenance")
    try:
        recreated = EventEnvelope.create(
            sequence=sequence,
            year=year,
            phase=phase,
            event_type=event_type,
            actor_ids=actor_ids,
            artifact_ids=artifact_ids,
            payload=payload,
            provenance=provenance,
        )
    except (TypeError, ValueError) as error:
        raise GraphRuntimeError(f"canonical source event is invalid: {error}") from error
    if recreated.event_id != value.get("event_id"):
        raise GraphRuntimeError("canonical source event identity mismatch")
    _strict_json(recreated.to_dict(), "canonical source event")
    return recreated


def _read_json_object(path: Path, label: str) -> Mapping[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        raise GraphRuntimeError(f"cannot read {label}: {error}") from error
    return _mapping(value, label)


def _checked_file(root: Path, spec: Any, label: str) -> Path:
    row = _mapping(spec, label)
    if set(row) != {"path", "sha256"}:
        raise GraphRuntimeError(f"{label} fields do not match file schema")
    relative = Path(_nonempty_string(row.get("path"), f"{label}.path"))
    expected = _sha256(row.get("sha256"), f"{label}.sha256")
    if relative.is_absolute() or ".." in relative.parts:
        raise GraphRuntimeError(f"{label}.path must stay below the declared root")
    resolved_root = root.resolve()
    path = (resolved_root / relative).resolve()
    try:
        path.relative_to(resolved_root)
    except ValueError as error:
        raise GraphRuntimeError(f"{label}.path escapes the declared root") from error
    if not path.is_file():
        raise GraphRuntimeError(f"{label} is missing: {relative}")
    actual = _file_sha256(path)
    if actual != expected:
        raise GraphRuntimeError(
            f"{label} hash mismatch: expected {expected}, got {actual}"
        )
    return path


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GraphRuntimeError(f"{label} must be a mapping")
    return value


def _file_sha256(path: Path) -> str:
    try:
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as error:
        raise GraphRuntimeError(f"cannot hash campaign source manifest: {error}") from error


def _unique_strings(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item for item in value)
        or len(value) != len(set(value))
    ):
        raise GraphRuntimeError(f"simulator {label} must be unique strings")
    return list(value)


def _string_ids(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item for item in value)
        or len(value) != len(set(value))
    ):
        raise GraphRuntimeError(f"{label} must be a list of unique strings")
    return list(value)


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise GraphRuntimeError(f"{label} must be a non-empty string")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise GraphRuntimeError(f"{label} must be a lowercase SHA-256")
    return value


def _git_commit(value: Any, label: str) -> str:
    if not isinstance(value, str) or _GIT_COMMIT.fullmatch(value) is None:
        raise GraphRuntimeError(f"{label} must be a full lowercase Git commit")
    return value


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise GraphRuntimeError(f"{label} must be a positive integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GraphRuntimeError(f"{label} must be a non-negative integer")
    return value


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _strict_json(value: Any, label: str) -> None:
    try:
        json.dumps(value, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as error:
        raise GraphRuntimeError(f"{label} is not strict JSON: {error}") from error
