"""Execute SystemSpec institutions against the live, original research world.

The baseline graph delegates to native Simulation methods. No numeric world
laws, surrogate researchers or replacement paper corpus are introduced here.
Native stages are registry entries, not mandatory mechanism families.
"""
from __future__ import annotations

from dataclasses import replace
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable

from .model import (AgentTypeSpec, ArtifactTypeSpec, ChannelKind, ConnectionSpec,
                    MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec, SystemSpec)
from .runtime import (DeterministicGraphRunner, GraphCheckpoint, GraphRuntimeError,
                      MechanismEvent, MechanismRegistry, MechanismResult, MechanismValue)
from .validation import validate_system_spec
from utopia.replay.events import EventEnvelope, canonical_event_stream_hash


SCHEMA = "scienceutopia.native-science-kernel.v1"
WORLD_ARTIFACT = "native-world-observation"
CONTROL_ARTIFACT = "native-phase-completion"
CONTEXT_RECEIVER = "native.world.researcher-context.v1"
ARTIFACT_STORE = "native.world.artifact-store.v1"
LLM_INSTITUTION = "native.world.llm-institution.v1"
DESIGN_PROPOSALS = "native.world.design-proposals.v1"
RESOURCE_TRANSFERS = "native.world.resource-transfers.v1"
STAGES = (
    ("open", MechanismFamily.POPULATION),
    ("resubmissions", MechanismFamily.RESEARCH),
    ("research", MechanismFamily.RESEARCH),
    ("collaboration", MechanismFamily.COLLABORATION),
    ("submission", MechanismFamily.RESEARCH),
    ("costs", MechanismFamily.RESEARCH),
    ("review", MechanismFamily.EVALUATION),
    ("selection", MechanismFamily.EVALUATION),
    ("publication", MechanismFamily.PUBLICATION),
    ("citation-potential", MechanismFamily.COMMUNICATION),
    ("funding", MechanismFamily.FUNDING),
    ("communication", MechanismFamily.COMMUNICATION),
    ("close", MechanismFamily.CUSTOM),
)


def _json(value):
    """Observation projection only: exclude clocks/paths, retain domain content."""
    if isinstance(value, dict):
        return {str(k): (_clone(v) if k in {"institutional_context", "extension_state", "open_domain"} else _json(v))
                for k, v in value.items() if k not in {
            "timestamp", "submission_time", "review_time", "decision_time", "output_dir"}}
    if isinstance(value, (tuple, list)):
        return [_json(v) for v in value]
    if isinstance(value, set):
        return sorted((_json(v) for v in value), key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict"):
        return _json(value.to_dict())
    if hasattr(value, "item"):
        return _json(value.item())
    if value is None or type(value) in (str, int, bool):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise GraphRuntimeError(f"native observation is not finite JSON: {type(value).__name__}")


def _clone(value):
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def legacy_world_system(*, seed: int = 42) -> SystemSpec:
    """One exact legacy-instance graph. It is not the grammar of all worlds."""
    nodes, schedules, edges = [], [], []
    for index, (stage, family) in enumerate(STAGES):
        inputs = () if index == 0 else (PortSpec("after", ChannelKind.SIGNAL, CONTROL_ARTIFACT),)
        if stage == "publication":
            inputs += (PortSpec("decisions", ChannelKind.DECISION, "native-paper-decision"),)
        outputs = (PortSpec("next", ChannelKind.SIGNAL, CONTROL_ARTIFACT),
                   PortSpec("world", ChannelKind.ARTIFACT, WORLD_ARTIFACT))
        if stage == "selection":
            outputs += (PortSpec("decisions", ChannelKind.DECISION, "native-paper-decision"),)
        node = MechanismSpec("world." + stage, family, "native.phase." + stage + ".v1",
                             inputs=inputs, outputs=outputs)
        nodes.append(node)
        schedules.append(ScheduleSpec(node.mechanism_id, index * 20))
        if index:
            edges.append(ConnectionSpec(nodes[-2].mechanism_id, "next", node.mechanism_id,
                                        "after", ChannelKind.SIGNAL))
    edges.append(ConnectionSpec("world.selection", "decisions", "world.publication", "decisions", ChannelKind.DECISION))
    return SystemSpec(
        "native-research-world", 1,
        agent_types=(AgentTypeSpec("researcher", ("research", "review", "apply-for-funding")),),
        artifact_types=(ArtifactTypeSpec(WORLD_ARTIFACT), ArtifactTypeSpec(CONTROL_ARTIFACT),
                        ArtifactTypeSpec("native-paper-decision")),
        mechanisms=tuple(nodes), connections=tuple(edges), schedules=tuple(schedules),
        initial_state={"seed": seed}, metadata={"world_adapter": SCHEMA,
            "instance": "original-research-world-not-the-expression-ceiling"},
    )


def add_context_receiver(spec: SystemSpec, *, source: str, source_port: str,
                         receiver: str = "researcher-context", phase: int = 235,
                         latency: int = 0) -> SystemSpec:
    """Connect any new artifact protocol to real researcher prompt input."""
    node = next(n for n in spec.mechanisms if n.mechanism_id == source)
    port = next(p for p in node.outputs if p.port_id == source_port)
    sink = MechanismSpec(receiver, MechanismFamily.COMMUNICATION, CONTEXT_RECEIVER,
                         inputs=(replace(port, port_id="messages", required=False),))
    return replace(spec, mechanisms=(*spec.mechanisms, sink),
                   schedules=(*spec.schedules, ScheduleSpec(receiver, phase)),
                   connections=(*spec.connections, ConnectionSpec(source, source_port, receiver,
                       "messages", port.channel, latency=latency)))


def institutional_context_prompt(agent) -> str:
    messages = getattr(agent, "institutional_context", ())
    if not messages:
        return ""
    # Preserve every raw delivered record in actors/checkpoints/events. Audit
    # hash labels must not make a late inert edit change earlier model inputs.
    from .model_provenance_view import render_provenance_view
    return "\n## Information received from scientific institutions\n" + render_provenance_view(messages) + "\n"


class NativeScienceKernel:
    def __init__(self, spec: SystemSpec, *, registry_extension: Callable | None = None,
                 code_executor=None, checkpoint: dict | None = None):
        validate_system_spec(spec).require_valid()
        self.spec = spec
        self.registry_extension = registry_extension
        self.code_executor = code_executor
        self.graph_checkpoint = None
        self.events = []
        self.last_year = 0
        self.execution_receipts = []
        self.design_history = []
        self.open_domain_state = {}
        from .native_open_domain import default_actions
        self.domain_actions = default_actions()
        self._frame = None
        self._simulation = None
        if checkpoint is not None:
            self.restore(checkpoint)

    @classmethod
    def from_path(cls, path, *, seed=42):
        if str(path) == "legacy":
            return cls(legacy_world_system(seed=seed))
        return cls(SystemSpec.from_dict(json.loads(Path(path).read_text())))

    def observation(self):
        sim = self._simulation
        conferences = sim.conference_system.to_dict()
        # Legacy serializer omits the in-flight submissions; a live observation
        # must not accidentally hide the actual artifacts being evaluated.
        for saved, conference in zip(conferences["conferences"], sim.conference_system.conferences):
            saved["submitted_papers"] = conference.submitted_papers
        observation = {"schema": "scienceutopia.native-world-observation.v1",
            "year": self._frame["year"], "ecosystem": sim.ecosystem.to_dict(),
            "papers": sim.paper_tracker.to_dict(),
            "conferences": conferences,
            "year_results": self._frame["results"],
            "extension_state": dict((self.graph_checkpoint or {}).get("mechanism_states", {}))}
        # Explicit opt-in self-description for endogenous system-design roles.
        # No private evaluator/loss/cache/credentials are added to observations.
        if self.spec.metadata.get('expose_system_spec', False):
            observation['system_spec'] = self.spec.to_dict()
            observation['system_fingerprint'] = self.spec.fingerprint
        if self.open_domain_state:
            observation['open_domain'] = _clone(self.open_domain_state)
        return _json(observation)

    def _registry(self):
        registry = MechanismRegistry()
        # Trusted plugins register typed actions through registry_extension on
        # every construction, including migration previews and cold workers.
        from .native_open_domain import default_actions
        self.domain_actions = default_actions()
        for stage, _ in STAGES:
            registry.register("native.phase." + stage + ".v1", 1,
                              lambda context, stage=stage: self._stage(stage, context))
        registry.register(CONTEXT_RECEIVER, 1, self._receive_context)
        registry.register(ARTIFACT_STORE, 1, self._store)
        registry.register(LLM_INSTITUTION, 1, self._llm_institution)
        registry.register(DESIGN_PROPOSALS, 1, self._record_design_proposals)
        from .native_resource_transfers import apply_native_resource_transfers
        registry.register(RESOURCE_TRANSFERS, 1, lambda context: apply_native_resource_transfers(self, context))
        from .native_activity_contracts import register_activity_contracts
        register_activity_contracts(self, registry)
        from .native_open_domain import register_native_domain
        register_native_domain(self, registry)
        from .native_researcher_work import register_researcher_work
        register_researcher_work(self, registry)
        from .tensor_program import IMPLEMENTATION as TENSOR_IMPLEMENTATION, tensor_handler
        registry.register(TENSOR_IMPLEMENTATION, 1, tensor_handler)
        from .code_mechanisms import _schema
        for node in self.spec.mechanisms:
            if node.implementation == LLM_INSTITUTION:
                schemas = node.parameters.get("output_schemas", {})
                if set(schemas) != {p.port_id for p in node.outputs}:
                    raise GraphRuntimeError("LLM institution ports and output schemas differ")
                for schema in (*schemas.values(), node.parameters.get("state_schema", {"type": "object"})):
                    _schema(schema)
        from .code_mechanisms import CODE_IMPLEMENTATION, DockerCodeExecutor, register_code_mechanisms
        code_nodes = [n for n in self.spec.mechanisms if n.implementation == CODE_IMPLEMENTATION]
        if code_nodes:
            images = {n.parameters.get("runtime_image_id") for n in code_nodes}
            if len(images) != 1 or None in images:
                raise GraphRuntimeError("native code nodes require one explicitly pinned runtime image")
            if self.code_executor is None:
                self.code_executor = DockerCodeExecutor(next(iter(images)))
            register_code_mechanisms(registry, self.code_executor, self.execution_receipts)
        from .native_process import register_native_process
        register_native_process(self, registry)
        # Trusted opt-in capability only; legacy review implementations and
        # default prompt bytes are unchanged unless selected in SystemSpec.
        from .native_review_context import register_review_context
        register_review_context(self, registry)
        from .native_review_routing import register_review_routing
        register_review_routing(self, registry)
        if self.registry_extension:
            self.registry_extension(self, registry)
        return registry

    def run_year(self, simulation, year):
        if self._frame is not None:
            raise GraphRuntimeError("native world is already executing")
        if type(year) is not int or year != self.last_year + 1:
            raise GraphRuntimeError("native years must advance exactly once from the last checkpoint")
        self._simulation = simulation
        self._frame = {"year": year, "results": {"year": year}}
        try:
            runner = DeterministicGraphRunner(self.spec, self._registry())
            result = runner.run(periods=1, start_period=year, checkpoint=self.graph_checkpoint)
            blocked = [r.mechanism_id for r in result.trace if r.status != "executed"]
            if blocked:
                raise GraphRuntimeError("native lifecycle blocked; restore preceding year before retry: " + str(blocked))
            results = self._frame["results"]
            self.graph_checkpoint = result.checkpoint.to_dict()
            self.events.extend(result.events)
            self.last_year = year
            return results
        finally:
            self._frame = None
            self._simulation = None

    def _require(self, *names):
        missing = [name for name in names if name not in self._frame]
        if missing:
            raise GraphRuntimeError("native phase prerequisites missing: " + str(missing))

    def _stage(self, stage, context, *, review_assignment=None, force_review_identity=False):
        sim, frame = self._simulation, self._frame
        year, results = frame["year"], frame["results"]
        sim.portable_safe_point()
        extra = {}
        extra_events = ()
        if stage == "open":
            frame["results"] = results = sim._setup_year(year)
            sim._start_native_government_year(year, results)
        elif stage == "resubmissions":
            frame["resubmissions"] = sim._run_phase_0_resubmissions(year, results)
            sim.wandb_logger.log_phase(year, 0, results, sim, num_resubmissions=len(frame["resubmissions"]))
        elif stage == "research":
            directions, authors, average = sim._run_phase_1_research_directions(year, results)
            frame.update(directions=directions, authors=authors)
            sim.wandb_logger.log_phase(year, 1, results, sim, num_active_authors=len(authors), avg_funding=average)
        elif stage == "collaboration":
            self._require("directions", "authors")
            sim._run_phase_1_5_collaboration_formation(year, frame["directions"], frame["authors"], results)
        elif stage == "submission":
            self._require("directions", "authors", "resubmissions")
            frame["submissions"] = sim._run_phase_2_submit_papers(year, frame["directions"], frame["authors"], frame["resubmissions"], results)
            sim._record_paper_metadata_batch(year)
            sim.wandb_logger.log_phase(year, 2, results, sim)
        elif stage == "costs":
            sim._charge_annual_costs(year)
        elif stage == "review":
            if force_review_identity or getattr(sim, '_record_native_review_identities', False):
                from .native_review_identity import capture_native_review_tasks, EVENT
                with capture_native_review_tasks(sim, year) as review_identity:
                    if review_assignment is None:
                        sim._run_phase_3_peer_review(year, results)
                    else:
                        sim._run_phase_3_peer_review(year, results, native_assignment=review_assignment)
                extra_events = (MechanismEvent(EVENT, payload=review_identity),)
            else:
                sim._run_phase_3_peer_review(year, results)
            sim.wandb_logger.log_phase(year, 3, results, sim)
            sim._apply_strategy_quality_adjustment(year)
        elif stage == "selection":
            sim._select_conference_decisions(year, results)
            extra["decisions"] = tuple(MechanismValue(_json({
                "paper_id": paper["id"], "conference_id": conf.conference_id,
                "decision": status, "final_score": paper.get("final_score"),
            })) for conf in sim.conference_system.conferences
                for status in ("accept", "reject") for paper in conf.decisions[status])
            # An empty batch is still a completed decision cycle, not a blocked publication.
            if not extra["decisions"]:
                extra["decisions"] = (MechanismValue({"empty_cycle": True}),)
        elif stage == "publication":
            self._apply_decisions(context)
            sim._commit_conference_decisions(year, results)
            sim.wandb_logger.log_phase(year, 4, results, sim)
        elif stage == "citation-potential":
            sim._assign_citation_potential(year)
        elif stage == "funding":
            self._require("submissions")
            sim._run_phase_5_update_funding(year, frame["submissions"], results)
        elif stage == "communication":
            sim._run_native_communication(year, results)
            sim._finish_native_government_year(year, results)
        elif stage == "close":
            sim._collect_exploration_metrics(year)
            if sim.is_exploration_experiment:
                sim._run_integrity_checks(year)
            sim._collect_preferential_attachment_metrics(year)
            results["conference_statistics"] = sim.conference_system.get_all_statistics()
            if getattr(sim, "resource_ledger", None) is not None:
                results["resource_balances"] = sim.resource_ledger.close_year(year, sim.ecosystem.agent_population)
            sim.wandb_logger.log_phase(year, 5, results, sim)
        world = self.observation()
        return MechanismResult(outputs={"next": (MechanismValue({"year": year}),),
            "world": (MechanismValue(world),), **extra}, events=(MechanismEvent(
                "native.system.phase_executed", payload={"stage": stage, "observation_sha256": _hash(world)}), *extra_events))

    def _apply_decisions(self, context):
        """Commit only actual native paper identities, regardless of selection algorithm."""
        sim = self._simulation
        decisions = [value.payload for value in context.inputs["decisions"]]
        conferences = sim.conference_system.conferences
        known = {paper["id"]: (conf, paper) for conf in conferences
                 for paper in (*conf.submitted_papers, *conf.decisions["accept"], *conf.decisions["reject"])}
        if not known:
            if decisions != [{"empty_cycle": True}]:
                raise GraphRuntimeError("empty native cycle requires an explicit empty decision batch")
            return
        # The native baseline has already selected these exact paper objects.
        # Do not rebuild maps or timestamps; preserving that path is the test.
        native = {n.mechanism_id for n in self.spec.mechanisms
                  if n.implementation == "native.phase.selection.v1"}
        if all(value.source_mechanism in native for value in context.inputs["decisions"]):
            return
        ids = [d.get("paper_id") for d in decisions]
        if len(ids) != len(set(ids)) or set(ids) != set(known):
            raise GraphRuntimeError("native decisions must cover exactly the real submitted paper identities")
        for decision in decisions:
            conf, _ = known[decision["paper_id"]]
            score = decision.get("final_score")
            if (decision.get("conference_id") != conf.conference_id
                    or decision.get("decision") not in {"accept", "reject"}
                    or isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score)):
                raise GraphRuntimeError("invalid native decision/score/conference reference")
        from utopia.agents.conference import ConferenceStatus
        from collections import defaultdict
        sim.conference_system.authors_to_accepted_papers = defaultdict(list)
        sim.conference_system.authors_to_rejected_papers = defaultdict(list)
        for conf in conferences:
            conf.decisions = {"accept": [], "reject": []}
            conf.authors_to_accepted_papers = defaultdict(list)
            conf.authors_to_rejected_papers = defaultdict(list)
        for decision in decisions:
            conf, paper = known[decision["paper_id"]]
            paper["status"] = status = decision["decision"]
            paper["final_score"] = decision["final_score"]
            paper["reviews"] = conf.reviews.get(paper["id"], [])
            conf.decisions[status].append(paper)
            author_map = conf.authors_to_accepted_papers if status == "accept" else conf.authors_to_rejected_papers
            for aid in sim._get_all_author_ids(paper):
                author_map[aid].append(paper)
                global_map = (sim.conference_system.authors_to_accepted_papers if status == "accept"
                              else sim.conference_system.authors_to_rejected_papers)
                global_map[aid].append(paper)
        for conf in conferences:
            conf.submitted_papers.clear()
            conf.status = ConferenceStatus.DECISIONS_MADE

    def _receive_context(self, context):
        population = self._simulation.ecosystem.agent_population
        planned = []
        for port, values in context.inputs.items():
            for index, value in enumerate(values):
                ids = value.actor_ids
                if not ids:
                    raise GraphRuntimeError("researcher context records need explicit actor_ids")
                if any(aid not in population or not getattr(population[aid], "can_author", False) for aid in ids):
                    raise GraphRuntimeError("context recipient must be an existing author-capable actor")
                message = {"message_id": _hash({"source": value.source_mechanism, "port": port,
                    "index": index, "year": context.period, "payload": value.payload,
                    "lineage": value.lineage_event_ids}),
                    "source": value.source_mechanism, "received_year": context.period,
                    "emitted_year": value.emitted_period, "payload": dict(value.payload),
                    "input_event_ids": list(value.lineage_event_ids)}
                for aid in ids:
                    planned.append((aid, message))
        events = []
        for aid, message in planned:
            agent = population[aid]
            messages = list(getattr(agent, "institutional_context", ()))
            if any(m["message_id"] == message["message_id"] for m in messages):
                raise GraphRuntimeError("context message was already delivered")
            agent.institutional_context = [*messages, _clone(message)]
            events.append(MechanismEvent("native.system.context_delivered", actor_ids=(aid,),
                                         payload={"message": message}))
        return MechanismResult(events=tuple(events))

    def _store(self, context):
        records = list(context.state.get("records", []))
        declared = dict(context.state.get("declared_artifacts", {}))
        events = []
        declarations = context.mechanism.parameters.get("declare_artifacts", False)
        reserved = set(self._simulation.paper_tracker.papers_by_id) | set(self.open_domain_state.get('artifacts', {}))
        owners = dict(self._frame.get('artifact_owners', {}))
        # Merge the completed checkpoint with already executed current-year stores.
        for node, state in (self.graph_checkpoint or {}).get("mechanism_states", {}).items():
            for identity in state.get("declared_artifacts", {}):
                owners.setdefault(identity, node)
        for port, values in context.inputs.items():
            artifact_type = next(p.artifact_type for p in context.mechanism.inputs if p.port_id == port)
            if declarations:
                for value in values:
                    if len(value.artifact_ids) != 1:
                        raise GraphRuntimeError("artifact declaration requires exactly one identity per record")
                    identity = value.artifact_ids[0]
                    if (identity in reserved or owners.get(identity, context.mechanism.mechanism_id) != context.mechanism.mechanism_id
                            or (identity in declared and declared[identity] != artifact_type)):
                        raise GraphRuntimeError("generic artifact identity/type collides with another owner")
                    events.append(MechanismEvent('artifact.updated' if identity in declared else 'artifact.created',
                        actor_ids=value.actor_ids, artifact_ids=(identity,),
                        payload={'artifact_type': artifact_type, 'content': dict(value.payload)}))
                    declared[identity] = artifact_type
                    owners[identity] = context.mechanism.mechanism_id
            records.extend({"port": port, "payload": dict(value.payload), "actor_ids": list(value.actor_ids),
                            "artifact_ids": list(value.artifact_ids), "year": context.period,
                            "input_event_ids": list(value.lineage_event_ids)} for value in values)
        state = {"records": records}
        if declarations:
            state['declared_artifacts'] = declared
            self._frame['artifact_owners'] = owners
        return MechanismResult(next_state=state, events=(*events, MechanismEvent(
            "native.system.artifacts_stored", payload={"record_count": len(records)})))

    def _llm_institution(self, context):
        """An open role with actual native LLM transport, not an enum of institutions."""
        prompt = context.mechanism.parameters["instruction"] + "\nReturn JSON with exactly outputs and state. "
        prompt += "outputs maps EVERY declared port to a list of {payload:object, actor_ids:[string], artifact_ids:[string]}. "
        prompt += "state is your persistent JSON object. Payload schemas:\n" + json.dumps(context.mechanism.parameters["output_schemas"])
        prompt += "\nObserved input records and your prior state:\n" + json.dumps({
            "inputs": {port: [{"payload": dict(v.payload), "actor_ids": list(v.actor_ids),
                              "artifact_ids": list(v.artifact_ids),
                              "input_event_ids": list(v.lineage_event_ids)} for v in values]
                       for port, values in context.inputs.items()},
            "state": dict(context.state)}, ensure_ascii=False, allow_nan=False)
        result, _ = self._simulation.llm.generate(prompt=prompt,
            response_format=context.mechanism.parameters.get("response_format"),
            seed_ctx=("native_institution", context.period, context.mechanism.mechanism_id))
        # Same output contract as generated code; this broker never gives code network access.
        from .code_mechanisms import validate_code_result
        contract = {"outputs": context.mechanism.parameters["output_schemas"],
                    "state_schema": context.mechanism.parameters.get("state_schema", {"type": "object"})}
        validate_code_result(contract, result)
        return MechanismResult(outputs={port: tuple(MechanismValue(v["payload"],
            actor_ids=tuple(v.get("actor_ids", ())), artifact_ids=tuple(v.get("artifact_ids", ())))
            for v in values) for port, values in result["outputs"].items()}, next_state=result["state"],
            events=(MechanismEvent("native.system.llm_institution_executed",
                                   payload={"prompt_sha256": _hash(prompt), "response_sha256": _hash(result)}),))

    def _record_design_proposals(self, context):
        """Record world-originated design proposals; never hot-install or score them."""
        from .design_patch import apply_design_patch, digest
        records = list(context.state.get('proposals', []))
        events = []
        for values in context.inputs.values():
            for value in values:
                proposal = {'year': context.period, 'origin_mechanism': value.source_mechanism,
                            'patch': dict(value.payload), 'loss': None}
                try:
                    candidate = apply_design_patch(self.spec, proposal['patch'])
                    proposal.update(status='structurally_valid-not-evaluated', candidate_fingerprint=candidate.fingerprint)
                except Exception as error:
                    proposal.update(status='technically_invalid', error=str(error)[:2000])
                proposal['proposal_sha256'] = digest(proposal)
                records.append(proposal)
                events.append(MechanismEvent('native.system.design_proposed', actor_ids=value.actor_ids,
                                             payload=proposal))
        return MechanismResult(next_state={'proposals': records}, events=tuple(events))

    def gradient_contract(self):
        from .tensor_program import IMPLEMENTATION as TENSOR_IMPLEMENTATION
        return {"world": "native-research-world", "end_to_end_autograd": False,
                "opaque_nodes": [{"id": node.mechanism_id, "implementation": node.implementation}
                                 for node in self.spec.mechanisms if node.implementation != TENSOR_IMPLEMENTATION],
                "represented_tensor_nodes": [node.mechanism_id for node in self.spec.mechanisms
                                             if node.implementation == TENSOR_IMPLEMENTATION],
                "tensor_trace_autograd": "represented operations, memory and tensor edges; opaque native observations conditioned/frozen",
                "reason": "JSON/domain transitions and native LLM/discrete operations do not carry autograd tensors",
                "numeric_miniature_is_not_a_substitute": True}

    def to_dict(self):
        if self._frame is not None:
            raise GraphRuntimeError("only completed-year kernel checkpoints are supported")
        result = {"schema": SCHEMA, "spec": self.spec.to_dict(), "system_fingerprint": self.spec.fingerprint,
                "last_year": self.last_year, "graph_checkpoint": _clone(self.graph_checkpoint),
                "events": [e.to_dict() for e in self.events],
                "event_stream_hash": canonical_event_stream_hash(self.events)}
        if self.design_history:
            result["design_history"] = _clone(self.design_history)
        if self.open_domain_state:
            result['open_domain'] = _clone(self.open_domain_state)
        return result

    def restore(self, state):
        required = {"schema", "spec", "system_fingerprint", "last_year", "graph_checkpoint", "events", "event_stream_hash"}
        if (not isinstance(state, dict) or not required <= set(state) <= required | {'design_history', 'open_domain'} or state["schema"] != SCHEMA
                or state["spec"] != self.spec.to_dict() or state["system_fingerprint"] != self.spec.fingerprint
                or type(state["last_year"]) is not int or state["last_year"] < 0):
            raise GraphRuntimeError("native kernel checkpoint identity/schema mismatch")
        events = []
        seen = set()
        from .native_migration import validate_design_history
        fingerprints = validate_design_history(state, self.spec)
        for index, value in enumerate(state["events"]):
            event = EventEnvelope.create(**{k: value[k] for k in (
                "sequence", "year", "phase", "event_type", "actor_ids", "artifact_ids", "payload", "provenance")})
            if (event.to_dict() != value or event.sequence != index
                    or not 1 <= event.year <= state["last_year"]
                    or event.provenance.get("system_fingerprint") != fingerprints[index]):
                raise GraphRuntimeError("native kernel event history is inconsistent")
            if any(ref not in seen for ref in event.provenance.get("input_event_ids", ())):
                raise GraphRuntimeError("native kernel causal reference is missing or future")
            events.append(event)
            seen.add(event.event_id)
        if canonical_event_stream_hash(events) != state["event_stream_hash"]:
            raise GraphRuntimeError("native kernel event hash mismatch")
        checkpoint = state["graph_checkpoint"]
        if state["last_year"] == 0:
            if checkpoint is not None or events:
                raise GraphRuntimeError("unstarted kernel cannot contain execution state")
        else:
            restored = GraphCheckpoint.from_dict(checkpoint)
            from .runtime import _validate_checkpoint
            _validate_checkpoint(restored, self.spec, "annual")
            if any(n.implementation == 'native.process.activity.v1' for n in self.spec.mechanisms):
                from .native_migration import validate_native_execution_checkpoint
                validate_native_execution_checkpoint(self.spec, checkpoint)
            if (restored.system_fingerprint != self.spec.fingerprint
                    or restored.next_period != state["last_year"] + 1
                    or restored.next_event_sequence != len(events)):
                raise GraphRuntimeError("native kernel graph cursor mismatch")
        from .native_open_domain import validate_domain_state
        validate_domain_state(state.get('open_domain', {}), events=events)
        from .native_researcher_work import validate_work_checkpoint
        validate_work_checkpoint(self.spec, checkpoint, events)
        from .native_activity_contracts import EFFECT, reconstruct_applied_plan
        for event in events:
            if event.event_type == EFFECT and 'base_plan' in event.payload:
                reconstruct_applied_plan(event.payload)
        from .native_review_routing import REVIEW, validate_routing_state, validate_routing_receipt
        for event in events:
            if event.event_type == 'native.system.review_routing_applied':
                validate_routing_receipt(event.payload)
        if checkpoint:
            for node in self.spec.mechanisms:
                if node.implementation == REVIEW:
                    validate_routing_state(checkpoint['mechanism_states'].get(node.mechanism_id, {}),
                        events, node.mechanism_id)
        self.graph_checkpoint = _clone(checkpoint)
        self.events = events
        self.last_year = state["last_year"]
        self.design_history = _clone(state.get("design_history", []))
        self.open_domain_state = _clone(state.get('open_domain', {}))
