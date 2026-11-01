"""Explicit, data-only institution migration at completed native-year boundaries.

This changes institutions, never researchers, papers, resources or RNG. Historical
events retain their original design identity. Pending messages are either carried
with their original provenance or explicitly archived, never silently discarded.
"""
from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import re

from jsonschema import Draft202012Validator

from .model import SystemSpec
from .runtime import (GraphCheckpoint, GraphRuntimeError, _initial_mechanism_states,
                      _validate_checkpoint)
from .validation import validate_system_spec
from utopia.replay.events import canonical_event_stream_hash

SCHEMA = "scienceutopia.native-design-migration.v1"


def _digest(value):
    from .native_kernel import _hash
    return _hash(value)


def _validate_programs(spec):
    """Validate untrusted contracts BEFORE evaluating even their JSON schemas."""
    from .code_mechanisms import validate_code_artifact
    from .tensor_program import IMPLEMENTATION, validate_tensor_program
    images = set()
    for node in spec.mechanisms:
        if node.implementation == "code.python.v1":
            artifact = node.parameters.get("code_artifact")
            validate_code_artifact(artifact)
            if (set(artifact["inputs"]) != {p.port_id for p in node.inputs}
                    or set(artifact["outputs"]) != {p.port_id for p in node.outputs}):
                raise GraphRuntimeError("migration code ports and artifact schemas differ")
            image = node.parameters.get("runtime_image_id")
            if not isinstance(image, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
                raise GraphRuntimeError("migration requires an exact pinned container image digest")
            images.add(image)
        elif node.implementation == IMPLEMENTATION:
            validate_tensor_program(node.parameters["program"])
            if (set(node.parameters["program"]["inputs"]) != set(node.parameters["input_bindings"])
                    or set(node.parameters["program"]["outputs"]) != {p.port_id for p in node.outputs}):
                raise GraphRuntimeError("migration tensor bindings and ports differ")
    if len(images) > 1:
        raise GraphRuntimeError("native code nodes require one pinned container image")
    return next(iter(images), None)


def _reconcile(old_spec, new_spec, graph, state_actions, discard_deliveries):
    """Pure deterministic reconciliation; also used when reopening a receipt."""
    _validate_programs(old_spec)
    _validate_programs(new_spec)
    before = GraphCheckpoint.from_dict(graph)
    _validate_checkpoint(before, old_spec, "annual")
    old = {n.mechanism_id: n for n in old_spec.mechanisms}
    new = {n.mechanism_id: n for n in new_spec.mechanisms}
    if set(state_actions) - new.keys():
        raise GraphRuntimeError("state action refers to an absent new mechanism")
    states = _initial_mechanism_states(new_spec)
    for name, node in new.items():
        action = state_actions.get(name)
        previous = before.mechanism_states.get(name)
        if action is None:
            if name in old and old[name] != node and previous is not None:
                raise GraphRuntimeError(f"changed mechanism {name} needs an explicit state action")
            if previous is not None:
                states[name] = deepcopy(previous)
        elif action == "preserve":
            if previous is None:
                raise GraphRuntimeError(f"cannot preserve absent state: {name}")
            states[name] = deepcopy(previous)
        elif action == "reset":
            states[name] = deepcopy(new_spec.initial_state.get("mechanism_states", {}).get(name, {}))
        elif isinstance(action, dict) and set(action) == {"replace"} and isinstance(action["replace"], dict):
            states[name] = deepcopy(action["replace"])
        else:
            raise GraphRuntimeError("state action must be preserve, reset or {replace: JSON object}")
        if node.implementation == "code.python.v1":
            Draft202012Validator(node.parameters["code_artifact"]["state_schema"]).validate(states.get(name, {}))
    queue = graph["queued_deliveries"]
    known_orders = {str(q["order"]) for q in queue}
    if (set(discard_deliveries) - known_orders
            or any(not isinstance(v, str) or not v.strip() for v in discard_deliveries.values())):
        raise GraphRuntimeError("discard requires an existing delivery order and a nonempty reason")
    retained = []
    for item in queue:
        if str(item["order"]) in discard_deliveries:
            continue
        target = new.get(item["target_mechanism"])
        port = next((p for p in target.inputs if p.port_id == item["target_port"]), None) if target else None
        value = item["value"]
        if port is None or port.channel.value != value["channel"] or port.artifact_type != value["artifact_type"]:
            raise GraphRuntimeError("pending delivery incompatible with new target; explicitly discard or retain its port")
        if target.implementation == "code.python.v1":
            Draft202012Validator(target.parameters["code_artifact"]["inputs"][port.port_id]).validate(value["payload"])
        retained.append(deepcopy(item))
    migrated = {**deepcopy(graph), "system_fingerprint": new_spec.fingerprint,
                "mechanism_states": states, "queued_deliveries": retained}
    _validate_checkpoint(GraphCheckpoint.from_dict(migrated), new_spec, "annual")
    return migrated


def migrate_native_design(kernel, candidate: SystemSpec, *, expected_checkpoint_sha256,
                          state_actions=None, discard_deliveries=None, origin=None):
    """Prepare and install one atomic institution change; no simulation/model calls.

    The caller supplies the hash of the exact completed kernel it inspected.
    Changed stateful nodes require explicit preserve/reset/replacement decisions.
    Removed-node state and dropped-message bytes survive in the migration receipt.
    Saving the enclosing portable checkpoint remains the simulation's responsibility.
    """
    from .native_kernel import NativeScienceKernel
    from .runtime import DeterministicGraphRunner
    if kernel._frame is not None or kernel.last_year < 1:
        raise GraphRuntimeError("migration requires a completed native year")
    before = kernel.to_dict()
    if _digest(before) != expected_checkpoint_sha256:
        raise GraphRuntimeError("stale native checkpoint; migration not installed")
    if kernel.design_history and kernel.design_history[-1]["after_year"] >= kernel.last_year:
        raise GraphRuntimeError("combine edits into one transaction per completed-year boundary")
    validate_system_spec(candidate).require_valid()
    image = _validate_programs(candidate)
    if candidate.system_id != kernel.spec.system_id:
        raise GraphRuntimeError("same-society migration must preserve system_id")
    def founding(spec):
        return {k: v for k, v in spec.initial_state.items() if k != "mechanism_states"}
    if founding(candidate) != founding(kernel.spec):
        raise GraphRuntimeError("migration cannot rewrite founding world/seed attributes")
    actions, discarded = deepcopy(state_actions or {}), deepcopy(discard_deliveries or {})
    graph = _reconcile(kernel.spec, candidate, kernel.graph_checkpoint, actions, discarded)
    # Resolve implementations and validate code/schema without invoking any node.
    executor = kernel.code_executor
    if image is not None and executor is not None and executor.image_id != image:
        from .code_mechanisms import DockerCodeExecutor
        executor = DockerCodeExecutor(image)
        if executor.image_id != image:
            raise GraphRuntimeError("migration executor does not match the pinned candidate image")
    preview = NativeScienceKernel(candidate, registry_extension=kernel.registry_extension,
                                  code_executor=executor)
    DeterministicGraphRunner(candidate, preview._registry())
    record = {"schema": SCHEMA, "after_year": kernel.last_year,
              "event_count": len(kernel.events), "event_prefix_sha256": before["event_stream_hash"],
              "source_spec": kernel.spec.to_dict(), "target_spec": candidate.to_dict(),
              "source_graph": deepcopy(kernel.graph_checkpoint), "target_graph": graph,
              "state_actions": actions, "discard_deliveries": discarded,
              "origin": deepcopy(origin or {"kind": "explicit-external-design"}),
              "parent_kernel_sha256": expected_checkpoint_sha256,
              "previous_migration_sha256": kernel.design_history[-1]["receipt_sha256"] if kernel.design_history else None}
    record["receipt_sha256"] = _digest(record)
    proposed = {**before, "spec": candidate.to_dict(), "system_fingerprint": candidate.fingerprint,
                "graph_checkpoint": graph, "design_history": [*deepcopy(kernel.design_history), record]}
    # All schema, queue, causal-history and epoch checks complete BEFORE install.
    preview.restore(proposed)
    kernel.spec, kernel.graph_checkpoint = preview.spec, preview.graph_checkpoint
    kernel.design_history = preview.design_history
    kernel.code_executor = preview.code_executor
    return deepcopy(record)


def install_recorded_native_proposal(kernel, proposal_event_id, *, expected_checkpoint_sha256,
                                     state_actions=None, discard_deliveries=None):
    """Explicitly install a real world-originated proposal in that SAME society.

    Selection of a proposal is a caller decision, not an implicit improvement
    claim. The function never scores, edits or substitutes the proposed patch.
    """
    from .design_patch import apply_design_patch
    event = next((e for e in kernel.events if e.event_id == proposal_event_id
                  and e.event_type == "native.system.design_proposed"), None)
    if event is None:
        raise GraphRuntimeError("proposal must reference an actual native proposal event")
    proposal = dict(event.payload)
    if proposal.get("status") != "structurally_valid-not-evaluated":
        raise GraphRuntimeError("proposal is not structurally valid")
    if _digest({k: v for k, v in proposal.items() if k != "proposal_sha256"}) != proposal.get("proposal_sha256"):
        raise GraphRuntimeError("recorded proposal hash differs")
    candidate = apply_design_patch(kernel.spec, proposal["patch"])
    if candidate.fingerprint != proposal["candidate_fingerprint"]:
        raise GraphRuntimeError("recorded proposal and compiled design differ")
    return migrate_native_design(kernel, candidate, expected_checkpoint_sha256=expected_checkpoint_sha256,
        state_actions=state_actions, discard_deliveries=discard_deliveries,
        origin={"kind": "recorded-world-proposal", "event_id": event.event_id,
                "proposal_sha256": proposal["proposal_sha256"]})


def commit_native_design(simulation, candidate=None, *, expected_checkpoint_sha256,
                         state_actions=None, discard_deliveries=None, proposal_event_id=None,
                         origin=None):
    """Durably adopt institutions at a just-saved portable society boundary.

    Preserve the prior checkpoint byte-for-byte under a content-addressed archive;
    atomically commit the complete updated society BEFORE swapping the live kernel.
    This does not invoke checkpoint callbacks or change any scientific/RNG field.
    """
    from .native_kernel import NativeScienceKernel
    from utopia.runtime.checkpointing import capture_rng, pack_state, read_portable_checkpoint, write_portable_checkpoint
    from utopia.utils.data_utils import file_sha256
    kernel = simulation.native_system
    if (kernel is None or kernel._frame is not None or kernel.last_year < 1
            or getattr(simulation, "_portable_last_year", None) != kernel.last_year):
        raise GraphRuntimeError("durable migration requires a saved portable native year boundary")
    path = Path(simulation.output_dir) / f"portable_checkpoint_year_{kernel.last_year}.json.gz"
    if getattr(simulation, "_portable_active_checkpoint", None) != str(path.resolve()):
        raise GraphRuntimeError("durable migration must run inside the synchronous completed-checkpoint callback")
    state = read_portable_checkpoint(path)
    if (state.get("year") != kernel.last_year or state.get("phase") != 5
            or state.get("native_system") != kernel.to_dict()
            or state["portable"]["contract"] != simulation.portable_contract()):
        raise GraphRuntimeError("saved society boundary differs from current kernel/contract")
    if (capture_rng() != state["portable"]["rng"]
            or simulation.llm.response_cache.committed_count() != state["portable"]["response_cache_count"]):
        raise GraphRuntimeError("RNG or inference advanced after the saved society boundary")
    if _digest(pack_state(simulation.capture_checkpoint_state(kernel.last_year, phase=5))) != _digest(pack_state(state)):
        raise GraphRuntimeError("unsaved complete society differs from the saved boundary")
    preview = NativeScienceKernel(kernel.spec, registry_extension=kernel.registry_extension,
                                  code_executor=kernel.code_executor, checkpoint=kernel.to_dict())
    kwargs = {"expected_checkpoint_sha256": expected_checkpoint_sha256,
              "state_actions": state_actions, "discard_deliveries": discard_deliveries}
    if proposal_event_id is None:
        if not isinstance(candidate, SystemSpec):
            raise GraphRuntimeError("explicit candidate required")
        receipt = migrate_native_design(preview, candidate, origin=origin, **kwargs)
    else:
        if candidate is not None or origin is not None:
            raise GraphRuntimeError("choose an explicit candidate OR a recorded proposal")
        receipt = install_recorded_native_proposal(preview, proposal_event_id, **kwargs)
    # Archive the old complete society, not only its institution state.
    archive = path.parent / "design-migration-archives" / (file_sha256(path) + ".json.gz")
    archive.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Persist the newly created archive-directory entry before committing state.
    directory = os.open(archive.parent.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    data = path.read_bytes()
    try:
        from utopia.utils.data_utils import write_bytes_atomic
        write_bytes_atomic(archive, data, exclusive=True, private=True, readonly=True)
    except FileExistsError:
        if archive.read_bytes() != data:
            raise GraphRuntimeError("immutable pre-migration society archive differs")
    state["native_system"] = preview.to_dict()
    state["portable"]["contract"]["native_system"] = {"system_fingerprint": preview.spec.fingerprint}
    write_portable_checkpoint(path, state)  # Existing writer uses atomic rename.
    simulation.native_system = preview
    return {"migration": receipt, "checkpoint": str(path), "previous_society_archive": str(archive)}


def checkpoint_native_bootstrap(configured_kernel, saved_state):
    """Validate a migrated checkpoint from the ORIGINAL invocation's design.

    Used before portable contract comparison. Only a valid lineage rooted in the
    exact configured founding design may change the native fingerprint contract.
    """
    from .native_kernel import NativeScienceKernel
    if not isinstance(saved_state, dict) or not saved_state.get("design_history"):
        raise GraphRuntimeError("a changed native design requires validated migration lineage")
    history = saved_state["design_history"]
    if history[0].get("source_spec") != configured_kernel.spec.to_dict():
        raise GraphRuntimeError("migration lineage does not start at the configured native design")
    current = SystemSpec.from_dict(saved_state["spec"])
    image = _validate_programs(current)
    executor = configured_kernel.code_executor
    if executor is not None and image is not None and executor.image_id != image:
        executor = None  # Actual execution resolves the target pinned image, not the old executor.
    return NativeScienceKernel(current, registry_extension=configured_kernel.registry_extension,
                               code_executor=executor, checkpoint=saved_state)


def validate_design_history(state, current_spec):
    """Return the historical design for each event, verifying chained receipts."""
    history = state.get("design_history", [])
    if not isinstance(history, list) or ("design_history" in state and not history):
        raise GraphRuntimeError("migration history must be a nonempty list when present")
    if not history:
        return [current_spec.fingerprint] * len(state["events"])
    expected = []
    previous_hash, previous_spec, previous_year, previous_count = None, None, 0, 0
    from utopia.replay.events import EventEnvelope
    for receipt_index, record in enumerate(history):
        required = {"schema", "after_year", "event_count", "event_prefix_sha256", "source_spec", "target_spec",
                    "source_graph", "target_graph", "state_actions", "discard_deliveries", "parent_kernel_sha256",
                    "previous_migration_sha256", "receipt_sha256", "origin"}
        if not isinstance(record, dict) or set(record) != required:
            raise GraphRuntimeError("migration receipt fields differ")
        body = {k: v for k, v in record.items() if k != "receipt_sha256"}
        if record["schema"] != SCHEMA or _digest(body) != record["receipt_sha256"] or record["previous_migration_sha256"] != previous_hash:
            raise GraphRuntimeError("migration receipt hash chain differs")
        year, count = record["after_year"], record["event_count"]
        if (type(year) is not int or not previous_year < year <= state["last_year"]
                or type(count) is not int or not previous_count <= count <= len(state["events"])):
            raise GraphRuntimeError("migration boundary is inconsistent")
        source, target = SystemSpec.from_dict(record["source_spec"]), SystemSpec.from_dict(record["target_spec"])
        validate_system_spec(source).require_valid()
        validate_system_spec(target).require_valid()
        if source.system_id != target.system_id or (previous_spec is not None and source != previous_spec):
            raise GraphRuntimeError("migration design chain differs")
        prefix = state["events"][:count]
        events = [EventEnvelope.create(**{k: e[k] for k in ("sequence", "year", "phase", "event_type", "actor_ids", "artifact_ids", "payload", "provenance")}) for e in prefix]
        if canonical_event_stream_hash(events) != record["event_prefix_sha256"]:
            raise GraphRuntimeError("migration event prefix differs")
        origin = record["origin"]
        if not isinstance(origin, dict) or origin.get("kind") not in {"explicit-external-design", "recorded-world-proposal"}:
            raise GraphRuntimeError("unsupported migration origin")
        if origin["kind"] == "recorded-world-proposal":
            proposed = next((e for e in events if e.event_id == origin.get("event_id")
                             and e.event_type == "native.system.design_proposed"), None)
            if (proposed is None or proposed.payload.get("proposal_sha256") != origin.get("proposal_sha256")
                    or proposed.payload.get("status") != "structurally_valid-not-evaluated"):
                raise GraphRuntimeError("migration origin does not bind a recorded world proposal")
            from .design_patch import apply_design_patch
            if (apply_design_patch(source, proposed.payload["patch"]) != target
                    or _digest({k: v for k, v in proposed.payload.items() if k != "proposal_sha256"}) != origin["proposal_sha256"]):
                raise GraphRuntimeError("migration differs from original world proposal")
        if any(e["year"] > year for e in prefix) or any(e["year"] <= year for e in state["events"][count:]):
            raise GraphRuntimeError("events cross their migration boundary")
        if (record["source_graph"]["next_period"] != year + 1
                or record["source_graph"]["next_event_sequence"] != count
                or _reconcile(source, target, record["source_graph"], record["state_actions"], record["discard_deliveries"]) != record["target_graph"]):
            raise GraphRuntimeError("migration reconciliation differs")
        parent = {"schema": state["schema"], "spec": source.to_dict(), "system_fingerprint": source.fingerprint,
                  "last_year": year, "graph_checkpoint": record["source_graph"], "events": prefix,
                  "event_stream_hash": record["event_prefix_sha256"]}
        if previous_hash is not None:
            parent["design_history"] = history[:receipt_index]
        if _digest(parent) != record["parent_kernel_sha256"]:
            raise GraphRuntimeError("migration parent checkpoint hash differs")
        expected.extend([source.fingerprint] * (count - previous_count))
        previous_hash, previous_spec, previous_year, previous_count = record["receipt_sha256"], target, year, count
    if previous_spec != current_spec:
        raise GraphRuntimeError("current design differs from migration lineage")
    expected.extend([current_spec.fingerprint] * (len(state["events"]) - previous_count))
    if state["last_year"] == previous_year and state["graph_checkpoint"] != history[-1]["target_graph"]:
        raise GraphRuntimeError("migrated boundary checkpoint differs")
    return expected
