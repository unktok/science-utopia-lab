"""Same real society survives institution changes; no model inference in QA."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from tests.system.test_native_science_kernel import make_sim
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from utopia.runtime.checkpointing import capture_rng, read_portable_checkpoint
from utopia.system import ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from utopia.system.native_kernel import NativeScienceKernel, WORLD_ARTIFACT, legacy_world_system, add_context_receiver, _hash
from utopia.system.native_migration import migrate_native_design
from utopia.system.runtime import (DeterministicGraphRunner, GraphRuntimeError, MechanismEvent,
                                   MechanismResult, MechanismValue)


def notice_spec(parent, label="notice", *, latency=0):
    node = MechanismSpec(label, MechanismFamily.CUSTOM, "test.migration-notice.v1",
        inputs=(PortSpec("world", ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec("message", ChannelKind.ARTIFACT, "migration-notice"),))
    from utopia.system import ArtifactTypeSpec
    spec = replace(parent, mechanisms=(*parent.mechanisms, node),
        artifact_types=(*parent.artifact_types, ArtifactTypeSpec("migration-notice")),
        schedules=(*parent.schedules, ScheduleSpec(label, 230)),
        connections=(*parent.connections, ConnectionSpec("world.funding", "world", label, "world", ChannelKind.ARTIFACT)))
    return add_context_receiver(spec, source=label, source_port="message", latency=latency)


def register_notice(kernel, registry):
    def send(ctx):
        cycles = ctx.state.get("cycles", 0) + 1
        observed = ctx.inputs["world"][0].payload
        authors = tuple(a["id"] for a in observed["ecosystem"]["agents"] if a["can_author"])
        return MechanismResult(next_state={"cycles": cycles},
            outputs={"message": (MechanismValue({"research_advisory": "Migration notice: share your failed ideas", "cycle": cycles}, actor_ids=authors),)},
            events=(MechanismEvent("test.migration_notice"),))
    registry.register("test.migration-notice.v1", 1, send)


def domain(sim):
    """Actual persistent domain data, not a substitute forward world."""
    return json.dumps({"agents": sim.ecosystem.to_dict(), "papers": sim.paper_tracker.to_dict(),
        "funding": sim.funding_tracker.to_dict(), "submitted": sorted(sim.submitted_paper_ids),
        "history": sim.yearly_results}, sort_keys=True, default=str)


def test_actual_society_continues_and_restores_across_new_protocol(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr("time.time", lambda: 1234567890.0)
    kernel = NativeScienceKernel(legacy_world_system(), registry_extension=register_notice)
    sim, calls = make_sim(tmp_path / "society", native=kernel)
    receipts, snapshots = [], []
    original_callback = sim.args.checkpoint_callback
    def boundary(path):
        original_callback(path)
        if kernel.last_year not in (1, 3):
            return
        before_domain, rng = domain(sim), capture_rng()
        before_events = [e.to_dict() for e in kernel.events]
        if kernel.last_year == 1:
            candidate = notice_spec(kernel.spec)
            actions = {}
        else:
            candidate = replace(kernel.spec, mechanisms=tuple(replace(n, parameters={"revision": 2})
                if n.mechanism_id == "notice" else n for n in kernel.spec.mechanisms))
            actions = {"notice": "preserve"}
        receipt = migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(kernel.to_dict()), state_actions=actions)
        assert domain(sim) == before_domain and capture_rng() == rng
        assert [e.to_dict() for e in kernel.events] == before_events
        assert kernel.spec.fingerprint == candidate.fingerprint
        assert NativeScienceKernel(candidate, checkpoint=kernel.to_dict()).to_dict() == kernel.to_dict()
        receipts.append(receipt)
        snapshots.append(kernel.to_dict())
    sim.checkpoint_callback = boundary
    try:
        sim.run()
        assert kernel.last_year == 6 and len(receipts) == 2
        assert kernel.graph_checkpoint["mechanism_states"]["notice"]["cycles"] == 5
        assert any("Migration notice" in json.dumps(payload) for (ctx, _, _), payload in calls if ctx[:2] == ("phase1_directions", 3))
        assert not any("Migration notice" in json.dumps(payload) for (ctx, _, _), payload in calls if ctx[:2] == ("phase1_directions", 2))
        saved = read_portable_checkpoint(tmp_path / "society/checkpoints/portable_checkpoint_year_6.json.gz")
        reopened = NativeScienceKernel(kernel.spec, checkpoint=saved["native_system"])
        assert reopened.to_dict() == kernel.to_dict()
        assert {e.provenance["system_fingerprint"] for e in reopened.events} == {legacy_world_system().fingerprint, snapshots[0]["system_fingerprint"], kernel.spec.fingerprint}
        # Real enclosing Simulation resume uses the current design contract and
        # historical response journal binding; it does not refound the society.
        sim.llm.response_cache.close()
        seed()
        resumed, resumed_calls = make_sim(tmp_path / "society", native=NativeScienceKernel(kernel.spec, registry_extension=register_notice))
        try:
            resumed.run()
            assert not resumed_calls
            assert resumed.native_system.to_dict() == saved["native_system"]
            assert resumed.ecosystem.to_dict() == sim.ecosystem.to_dict()
        finally:
            resumed.llm.response_cache.close()
    finally:
        sim.llm.response_cache.close()


def completed_kernel():
    """Graph-only fixtures test queue reconciliation, not native research effects."""
    spec = notice_spec(legacy_world_system(), latency=2)
    kernel = NativeScienceKernel(spec, registry_extension=register_notice)
    # Real runner with harmless stage replacements only for queue-unit semantics.
    from utopia.system.runtime import MechanismRegistry
    registry = MechanismRegistry()
    for node in spec.mechanisms:
        def handler(ctx, node=node):
            return MechanismResult(next_state={"cycles": 1}, outputs={p.port_id: (MechanismValue({}),) for p in node.outputs},
                events=(MechanismEvent("test.executed"),))
        registry.register(node.implementation, node.version, handler)
    result = DeterministicGraphRunner(spec, registry).run(periods=1, start_period=1)
    kernel.graph_checkpoint, kernel.events, kernel.last_year = result.checkpoint.to_dict(), list(result.events), 1
    return kernel


def test_stale_or_unresolved_candidate_is_atomic():
    kernel = completed_kernel()
    before = kernel.to_dict()
    with pytest.raises(GraphRuntimeError, match="stale"):
        migrate_native_design(kernel, kernel.spec, expected_checkpoint_sha256="0" * 64)
    assert kernel.to_dict() == before
    changed = replace(kernel.spec, mechanisms=tuple(replace(n, implementation="unknown.no-handler") if n.mechanism_id == "notice" else n for n in kernel.spec.mechanisms))
    with pytest.raises(GraphRuntimeError):
        migrate_native_design(kernel, changed, expected_checkpoint_sha256=_hash(before), state_actions={"notice": "preserve"})
    assert kernel.to_dict() == before


def test_stateful_source_changes_require_explicit_memory_decision():
    kernel = completed_kernel()
    before = kernel.to_dict()
    candidate = replace(kernel.spec, mechanisms=tuple(replace(n, parameters={"rule_revision": 2})
        if n.mechanism_id == "notice" else n for n in kernel.spec.mechanisms))
    with pytest.raises(GraphRuntimeError, match="explicit state action"):
        migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before))
    assert kernel.to_dict() == before
    migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before), state_actions={"notice": {"replace": {"cycles": 41}}})
    assert kernel.graph_checkpoint["mechanism_states"]["notice"] == {"cycles": 41}
    assert kernel.graph_checkpoint["queued_deliveries"] == before["graph_checkpoint"]["queued_deliveries"]
    assert NativeScienceKernel(candidate, checkpoint=kernel.to_dict()).to_dict() == kernel.to_dict()


def test_actual_world_proposal_installs_in_same_society(tmp_path, fixed_corpus, monkeypatch):
    from utopia.system.native_kernel import DESIGN_PROPOSALS
    from utopia.system.native_migration import install_recorded_native_proposal
    from utopia.system.design_patch import make_patch
    from utopia.system import ArtifactTypeSpec
    monkeypatch.setattr("time.time", lambda: 1234567890.0)
    base = legacy_world_system()
    actor = MechanismSpec("designer", MechanismFamily.CUSTOM, "test.endogenous-designer.v1",
        outputs=(PortSpec("patch", ChannelKind.ARTIFACT, "system-design-patch"),))
    collector = MechanismSpec("proposal-register", MechanismFamily.CUSTOM, DESIGN_PROPOSALS,
        inputs=(PortSpec("patch", ChannelKind.ARTIFACT, "system-design-patch", required=False),))
    spec = replace(base, mechanisms=(*base.mechanisms, actor, collector),
        artifact_types=(*base.artifact_types, ArtifactTypeSpec("system-design-patch")),
        schedules=(*base.schedules, ScheduleSpec("designer", 245), ScheduleSpec("proposal-register", 246)),
        connections=(*base.connections, ConnectionSpec("designer", "patch", "proposal-register", "patch", ChannelKind.ARTIFACT)))
    def register(kernel, registry):
        def design(ctx):
            patch = make_patch(kernel.spec, [{"op": "add", "path": "/metadata/endogenous_revision", "value": ctx.period}],
                               rationale="Scripted integration test, not LLM invention or benefit")
            return MechanismResult(outputs={"patch": (MechanismValue(patch),)})
        registry.register("test.endogenous-designer.v1", 1, design)
    kernel = NativeScienceKernel(spec, registry_extension=register)
    sim, _ = make_sim(tmp_path / "endogenous", native=kernel)
    original_callback = sim.checkpoint_callback
    installed = []
    def boundary(path):
        original_callback(path)
        if kernel.last_year not in (1, 3):
            return
        proposal = next(e for e in reversed(kernel.events) if e.event_type == "native.system.design_proposed")
        before = domain(sim)
        installed.append(install_recorded_native_proposal(kernel, proposal.event_id,
            expected_checkpoint_sha256=_hash(kernel.to_dict())))
        assert domain(sim) == before
        assert NativeScienceKernel(kernel.spec, checkpoint=kernel.to_dict()).to_dict() == kernel.to_dict()
    sim.checkpoint_callback = boundary
    try:
        sim.run()
        assert len(installed) == 2
        assert all(r["origin"]["kind"] == "recorded-world-proposal" for r in installed)
        assert kernel.last_year == 6 and kernel.spec.metadata["endogenous_revision"] == 3
        assert NativeScienceKernel(kernel.spec, checkpoint=kernel.to_dict()).to_dict() == kernel.to_dict()
    finally:
        sim.llm.response_cache.close()


@pytest.mark.parametrize("inject_write_failure", [False, True])
def test_durable_migration_cold_resume_from_original_design(tmp_path, fixed_corpus, monkeypatch, inject_write_failure):
    from utopia.system.native_migration import commit_native_design
    from utopia.runtime.checkpointing import PortableStop
    monkeypatch.setattr("time.time", lambda: 1234567890.0)
    founding = legacy_world_system()
    kernel = NativeScienceKernel(founding, registry_extension=register_notice)
    root = tmp_path / "durable"
    sim, _ = make_sim(root, native=kernel)
    original_callback = sim.checkpoint_callback
    adopted = []
    def boundary(path):
        original_callback(path)
        if sim.native_system.last_year != 1:
            return
        original_bytes = path.read_bytes()
        before = domain(sim)
        candidate = notice_spec(kernel.spec)
        if inject_write_failure:
            def fail(*args, **kwargs):
                raise OSError("injected persistence failure")
            with monkeypatch.context() as m:
                m.setattr("utopia.runtime.checkpointing.write_portable_checkpoint", fail)
                with pytest.raises(OSError, match="persistence"):
                    commit_native_design(sim, candidate, expected_checkpoint_sha256=_hash(kernel.to_dict()))
            assert path.read_bytes() == original_bytes and sim.native_system is kernel
        else:
            result = commit_native_design(sim, candidate, expected_checkpoint_sha256=_hash(kernel.to_dict()))
            assert Path(result["previous_society_archive"]).read_bytes() == original_bytes
            assert domain(sim) == before
            adopted.append(sim.native_system.to_dict())
        raise PortableStop("simulated cold shutdown immediately after migration transaction")
    sim.checkpoint_callback = boundary
    try:
        with pytest.raises(PortableStop, match="cold shutdown"):
            sim.run()
        assert sim._portable_last_year == 1
    finally:
        sim.llm.response_cache.close()
    seed()
    # No migrated spec retained or supplied at startup: use the ORIGINAL input.
    resumed, calls = make_sim(root, native=NativeScienceKernel(founding, registry_extension=register_notice))
    try:
        assert resumed.load_checkpoint(1)
        if inject_write_failure:
            assert resumed.native_system.spec == founding
            assert not resumed.native_system.design_history
        else:
            assert resumed.native_system.to_dict() == adopted[0]
        assert not calls
        resumed.run()
        assert resumed.native_system.last_year == 6
        if not inject_write_failure:
            assert any("Migration notice" in json.dumps(payload) for (ctx, _, _), payload in calls if ctx[:2] == ("phase1_directions", 3))
    finally:
        resumed.llm.response_cache.close()


def test_cold_bootstrap_refuses_unrelated_configured_world():
    from utopia.system.native_migration import checkpoint_native_bootstrap
    kernel = completed_kernel()
    old = kernel.spec
    candidate = replace(old, metadata={"revision": 2})
    migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(kernel.to_dict()))
    unrelated = NativeScienceKernel(replace(old, metadata={"unrelated": True}))
    with pytest.raises(GraphRuntimeError, match="configured"):
        checkpoint_native_bootstrap(unrelated, kernel.to_dict())


def test_pending_delivery_not_silently_lost_and_removed_state_archived():
    kernel = completed_kernel()
    before = kernel.to_dict()
    remove = {"notice", "researcher-context"}
    candidate = replace(kernel.spec, mechanisms=tuple(n for n in kernel.spec.mechanisms if n.mechanism_id not in remove),
        schedules=tuple(s for s in kernel.spec.schedules if s.mechanism_id not in remove),
        connections=tuple(c for c in kernel.spec.connections if c.source_mechanism not in remove and c.target_mechanism not in remove))
    with pytest.raises(GraphRuntimeError, match="pending delivery"):
        migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before))
    assert kernel.to_dict() == before
    discarded = {str(q["order"]): "Explicitly retire removed receiver" for q in kernel.graph_checkpoint["queued_deliveries"]}
    receipt = migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before), discard_deliveries=discarded)
    assert receipt["source_graph"]["mechanism_states"]["notice"] == {"cycles": 1}
    assert receipt["source_graph"]["queued_deliveries"]
    assert not kernel.graph_checkpoint["queued_deliveries"]
    assert NativeScienceKernel(candidate, checkpoint=kernel.to_dict()).to_dict() == kernel.to_dict()


@pytest.mark.parametrize("field", ["after_year", "event_count", "parent_kernel_sha256", "target_graph"])
def test_tampered_migration_receipt_rejected(field):
    kernel = completed_kernel()
    candidate = replace(kernel.spec, metadata={**kernel.spec.metadata, "design_revision": 2})
    migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(kernel.to_dict()))
    state = deepcopy(kernel.to_dict())
    state["design_history"][0][field] = None
    with pytest.raises((GraphRuntimeError, ValueError, TypeError)):
        NativeScienceKernel(candidate, checkpoint=state)
