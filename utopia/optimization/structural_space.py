"""Finite typed structural search spaces for whole science-system graphs.

This module connects graph structure to the optimizer-neutral ``SearchSpace``
protocol.  It does not know how a mechanism behaves and it does not define an
optimization loss.  A grammar declares legal node implementations and edge
variants; the normal ``SystemSpec`` validator establishes graph conformance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import itertools
import json
from types import MappingProxyType
from typing import Any, Mapping

from utopia.system import (
    AgentTypeSpec,
    ArtifactTypeSpec,
    ChannelKind,
    ConnectionSpec,
    MechanismFamily,
    MechanismSpec,
    PortSpec,
    ScheduleSpec,
    SystemSpec,
    validate_system_spec,
)
from utopia.system.examples import (
    AUTONOMOUS_RESEARCH,
    COMMUNITY_PUBLICATION,
    CURATED_PUBLICATION,
    DIRECT_PUBLICATION,
    FIXED_GRANT,
    MATCHING_GRANT,
    RESOURCE_RESEARCH,
)


STRUCTURAL_ENCODING_SCHEMA = "scienceutopia.structural-selection.v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


@dataclass(frozen=True)
class NodeOption:
    option_id: str
    mechanism: MechanismSpec
    schedule: ScheduleSpec


@dataclass(frozen=True)
class NodeSlot:
    slot_id: str
    options: tuple[NodeOption, ...]
    optional: bool = False


@dataclass(frozen=True)
class EdgeOption:
    option_id: str
    connection: ConnectionSpec


@dataclass(frozen=True)
class EdgeSlot:
    slot_id: str
    options: tuple[EdgeOption, ...]
    optional: bool = True


@dataclass(frozen=True)
class StructuralGrammar:
    """Declarative finite grammar for graph structure and implementation choice."""

    space_id: str
    system_id: str
    version: int
    node_slots: tuple[NodeSlot, ...]
    edge_slots: tuple[EdgeSlot, ...] = ()
    agent_types: tuple[AgentTypeSpec, ...] = ()
    artifact_types: tuple[ArtifactTypeSpec, ...] = ()
    initial_state: Mapping[str, Any] = field(default_factory=dict)
    global_invariants: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StructuralSelection:
    nodes: Mapping[str, str | None]
    edges: Mapping[str, str | None]

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", MappingProxyType(dict(self.nodes)))
        object.__setattr__(self, "edges", MappingProxyType(dict(self.edges)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": dict(sorted(self.nodes.items())),
            "edges": dict(sorted(self.edges.items())),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StructuralSelection":
        if set(value) != {"nodes", "edges"}:
            raise ValueError("structural selection requires exactly nodes and edges")
        nodes = value["nodes"]
        edges = value["edges"]
        if not isinstance(nodes, dict) or not isinstance(edges, dict):
            raise ValueError("structural selection nodes and edges must be objects")
        for group_name, group in (("nodes", nodes), ("edges", edges)):
            if any(
                not isinstance(key, str)
                or (choice is not None and not isinstance(choice, str))
                for key, choice in group.items()
            ):
                raise ValueError(
                    f"structural selection {group_name} must map strings to strings or null"
                )
        return cls(dict(nodes), dict(edges))

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            _canonical_json(self.to_dict()).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class StructuralMutation:
    kind: str
    slot_id: str
    before: str | None
    after: str | None


class StructuralSystemSpace:
    """Search-space adapter that emits complete canonical ``SystemSpec`` JSON."""

    def __init__(self, grammar: StructuralGrammar) -> None:
        self.grammar = grammar
        self._validate_grammar()
        self._node_slots = {slot.slot_id: slot for slot in grammar.node_slots}
        self._edge_slots = {slot.slot_id: slot for slot in grammar.edge_slots}
        self._valid_selections = self._enumerate_valid_selections()
        if not self._valid_selections:
            raise ValueError("structural grammar has no valid SystemSpec candidates")
        self._selection_keys = {
            _canonical_json(selection.to_dict()) for selection in self._valid_selections
        }

    @property
    def candidate_count(self) -> int:
        return len(self._valid_selections)

    @property
    def selections(self) -> tuple[StructuralSelection, ...]:
        return self._valid_selections

    def build(self, selection: StructuralSelection) -> SystemSpec:
        self._validate_selection_shape(selection)
        if _canonical_json(selection.to_dict()) not in self._selection_keys:
            raise ValueError("selection does not produce a valid graph in this space")
        spec = self._build_unchecked(selection)
        validate_system_spec(spec).require_valid()
        return spec

    def decode(self, candidate: Mapping[str, Any]) -> SystemSpec:
        """Parse and verify that candidate is the canonical grammar expansion."""

        try:
            spec = SystemSpec.from_dict(candidate)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid SystemSpec encoding: {error}") from error
        validate_system_spec(spec).require_valid()
        encoded = spec.metadata.get("structural_encoding")
        if not isinstance(encoded, dict):
            raise ValueError("SystemSpec metadata.structural_encoding is required")
        if encoded.get("schema") != STRUCTURAL_ENCODING_SCHEMA:
            raise ValueError("unsupported structural encoding schema")
        if encoded.get("space_id") != self.grammar.space_id:
            raise ValueError("candidate belongs to a different structural space")
        selection_value = encoded.get("selection")
        if not isinstance(selection_value, dict):
            raise ValueError("structural encoding selection must be an object")
        selection = StructuralSelection.from_dict(selection_value)
        rebuilt = self.build(selection)
        if rebuilt.canonical_json() != spec.canonical_json():
            raise ValueError("SystemSpec differs from its canonical structural selection")
        return spec

    def selection(self, candidate: Mapping[str, Any]) -> StructuralSelection:
        spec = self.decode(candidate)
        encoded = spec.metadata["structural_encoding"]
        return StructuralSelection.from_dict(encoded["selection"])

    def validate(self, candidate: Mapping[str, Any]) -> None:
        self.decode(candidate)

    def candidate_fingerprint(self, candidate: Mapping[str, Any]) -> str:
        return self.decode(candidate).fingerprint

    def sample(self, *, seed: int, proposal_index: int) -> Mapping[str, Any]:
        index = self._deterministic_index(seed, proposal_index, "sample", self.candidate_count)
        return self.build(self._valid_selections[index]).to_dict()

    def neighbors(
        self, candidate: Mapping[str, Any]
    ) -> tuple[tuple[StructuralMutation, dict[str, Any]], ...]:
        incumbent = self.selection(candidate)
        incumbent_nodes = incumbent.nodes
        incumbent_edges = incumbent.edges
        neighbors: list[tuple[StructuralMutation, dict[str, Any]]] = []
        for selection in self._valid_selections:
            node_diffs = [
                slot_id
                for slot_id in self._node_slots
                if incumbent_nodes[slot_id] != selection.nodes[slot_id]
            ]
            edge_diffs = [
                slot_id
                for slot_id in self._edge_slots
                if incumbent_edges[slot_id] != selection.edges[slot_id]
            ]
            if len(node_diffs) + len(edge_diffs) != 1:
                continue
            if node_diffs:
                slot_id = node_diffs[0]
                before = incumbent_nodes[slot_id]
                after = selection.nodes[slot_id]
                kind = (
                    "node-presence"
                    if before is None or after is None
                    else "implementation"
                )
            else:
                slot_id = edge_diffs[0]
                before = incumbent_edges[slot_id]
                after = selection.edges[slot_id]
                kind = (
                    "edge-presence"
                    if before is None or after is None
                    else "topology"
                )
            mutation = StructuralMutation(kind, slot_id, before, after)
            neighbors.append((mutation, self.build(selection).to_dict()))
        return tuple(
            sorted(
                neighbors,
                key=lambda item: (
                    item[0].kind,
                    item[0].slot_id,
                    str(item[0].before),
                    str(item[0].after),
                ),
            )
        )

    def mutate_with_record(
        self,
        incumbent: Mapping[str, Any],
        *,
        seed: int,
        proposal_index: int,
        scale: float,
    ) -> tuple[Mapping[str, Any], StructuralMutation]:
        if not 0 < scale <= 1:
            raise ValueError("mutation scale must be in (0, 1]")
        neighbors = self.neighbors(incumbent)
        if not neighbors:
            raise ValueError("candidate has no legal one-step structural mutation")
        index = self._deterministic_index(
            seed, proposal_index, "mutation", len(neighbors)
        )
        mutation, candidate = neighbors[index]
        return candidate, mutation

    def mutate(
        self,
        incumbent: Mapping[str, Any],
        *,
        seed: int,
        proposal_index: int,
        scale: float,
    ) -> Mapping[str, Any]:
        candidate, _ = self.mutate_with_record(
            incumbent,
            seed=seed,
            proposal_index=proposal_index,
            scale=scale,
        )
        return candidate

    def _validate_grammar(self) -> None:
        if not self.grammar.space_id or not self.grammar.system_id:
            raise ValueError("grammar space_id and system_id must be non-empty")
        node_slot_ids = [slot.slot_id for slot in self.grammar.node_slots]
        edge_slot_ids = [slot.slot_id for slot in self.grammar.edge_slots]
        if len(node_slot_ids) != len(set(node_slot_ids)):
            raise ValueError("node slot ids must be unique")
        if len(edge_slot_ids) != len(set(edge_slot_ids)):
            raise ValueError("edge slot ids must be unique")
        mechanism_ids: set[str] = set()
        for slot in self.grammar.node_slots:
            if not slot.options:
                raise ValueError(f"node slot {slot.slot_id!r} has no options")
            option_ids = [option.option_id for option in slot.options]
            if len(option_ids) != len(set(option_ids)):
                raise ValueError(f"node slot {slot.slot_id!r} has duplicate options")
            slot_mechanism_ids = {
                option.mechanism.mechanism_id for option in slot.options
            }
            if len(slot_mechanism_ids) != 1:
                raise ValueError(
                    f"node slot {slot.slot_id!r} options must share one mechanism id"
                )
            mechanism_id = next(iter(slot_mechanism_ids))
            if mechanism_id in mechanism_ids:
                raise ValueError("mechanism ids must be unique across node slots")
            mechanism_ids.add(mechanism_id)
            if any(
                option.schedule.mechanism_id != mechanism_id
                for option in slot.options
            ):
                raise ValueError(
                    f"node slot {slot.slot_id!r} schedule must target its mechanism"
                )
        for slot in self.grammar.edge_slots:
            if not slot.options:
                raise ValueError(f"edge slot {slot.slot_id!r} has no options")
            option_ids = [option.option_id for option in slot.options]
            if len(option_ids) != len(set(option_ids)):
                raise ValueError(f"edge slot {slot.slot_id!r} has duplicate options")
            identities = {
                (
                    option.connection.source_mechanism,
                    option.connection.source_port,
                    option.connection.target_mechanism,
                    option.connection.target_port,
                    option.connection.channel,
                )
                for option in slot.options
            }
            if len(identities) != 1:
                raise ValueError(
                    f"edge slot {slot.slot_id!r} options may vary topology attributes "
                    "but must connect the same typed ports"
                )

    def _validate_selection_shape(self, selection: StructuralSelection) -> None:
        if set(selection.nodes) != set(self._node_slots):
            raise ValueError("selection node slots do not match grammar")
        if set(selection.edges) != set(self._edge_slots):
            raise ValueError("selection edge slots do not match grammar")
        for slot_id, choice in selection.nodes.items():
            slot = self._node_slots[slot_id]
            allowed = {option.option_id for option in slot.options}
            if choice is None and not slot.optional:
                raise ValueError(f"required node slot {slot_id!r} cannot be absent")
            if choice is not None and choice not in allowed:
                raise ValueError(f"unknown option {choice!r} for node slot {slot_id!r}")
        for slot_id, choice in selection.edges.items():
            slot = self._edge_slots[slot_id]
            allowed = {option.option_id for option in slot.options}
            if choice is None and not slot.optional:
                raise ValueError(f"required edge slot {slot_id!r} cannot be absent")
            if choice is not None and choice not in allowed:
                raise ValueError(f"unknown option {choice!r} for edge slot {slot_id!r}")

    def _enumerate_valid_selections(self) -> tuple[StructuralSelection, ...]:
        node_values = [
            ([None] if slot.optional else [])
            + [option.option_id for option in slot.options]
            for slot in self.grammar.node_slots
        ]
        edge_values = [
            ([None] if slot.optional else [])
            + [option.option_id for option in slot.options]
            for slot in self.grammar.edge_slots
        ]
        valid: list[StructuralSelection] = []
        for values in itertools.product(*node_values, *edge_values):
            node_count = len(self.grammar.node_slots)
            selection = StructuralSelection(
                dict(zip((slot.slot_id for slot in self.grammar.node_slots), values[:node_count])),
                dict(zip((slot.slot_id for slot in self.grammar.edge_slots), values[node_count:])),
            )
            try:
                validate_system_spec(self._build_unchecked(selection)).require_valid()
            except ValueError:
                continue
            valid.append(selection)
        return tuple(
            sorted(valid, key=lambda item: _canonical_json(item.to_dict()))
        )

    def _build_unchecked(self, selection: StructuralSelection) -> SystemSpec:
        mechanisms: list[MechanismSpec] = []
        schedules: list[ScheduleSpec] = []
        for slot in self.grammar.node_slots:
            choice = selection.nodes[slot.slot_id]
            if choice is None:
                continue
            option = next(item for item in slot.options if item.option_id == choice)
            mechanisms.append(option.mechanism)
            schedules.append(option.schedule)
        connections: list[ConnectionSpec] = []
        for slot in self.grammar.edge_slots:
            choice = selection.edges[slot.slot_id]
            if choice is None:
                continue
            option = next(item for item in slot.options if item.option_id == choice)
            connections.append(option.connection)
        metadata = {
            **dict(self.grammar.metadata),
            "structural_encoding": {
                "schema": STRUCTURAL_ENCODING_SCHEMA,
                "space_id": self.grammar.space_id,
                "selection": selection.to_dict(),
            },
        }
        return SystemSpec(
            system_id=self.grammar.system_id,
            version=self.grammar.version,
            agent_types=self.grammar.agent_types,
            artifact_types=self.grammar.artifact_types,
            mechanisms=tuple(mechanisms),
            connections=tuple(connections),
            schedules=tuple(schedules),
            initial_state=self.grammar.initial_state,
            global_invariants=self.grammar.global_invariants,
            metadata=metadata,
        )

    @staticmethod
    def _deterministic_index(
        seed: int, proposal_index: int, purpose: str, length: int
    ) -> int:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        if (
            isinstance(proposal_index, bool)
            or not isinstance(proposal_index, int)
            or proposal_index < 0
        ):
            raise ValueError("proposal_index must be a non-negative integer")
        material = f"{seed}:{proposal_index}:{purpose}".encode("utf-8")
        return int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % length


def toy_structural_grammar() -> StructuralGrammar:
    """Executable finite grammar proving structural black-box optimization."""

    allocation = ArtifactTypeSpec(
        "resource-allocation", "Toy resource transfer between mechanisms"
    )
    publication = NodeSlot(
        "publication",
        (
            NodeOption(
                "direct",
                MechanismSpec(
                    "publication",
                    MechanismFamily.PUBLICATION,
                    DIRECT_PUBLICATION,
                    parameters={
                        "author_id": "researcher-structural",
                        "artifact_id": "paper-structural",
                        "title": "Structural search output",
                    },
                ),
                ScheduleSpec("publication", 2),
            ),
            NodeOption(
                "curated",
                MechanismSpec(
                    "publication",
                    MechanismFamily.PUBLICATION,
                    CURATED_PUBLICATION,
                    parameters={
                        "author_id": "researcher-structural",
                        "artifact_id": "paper-structural",
                        "title": "Structurally curated output",
                    },
                ),
                ScheduleSpec("publication", 2),
            ),
            NodeOption(
                "community-governed",
                MechanismSpec(
                    "publication",
                    MechanismFamily.GOVERNANCE,
                    COMMUNITY_PUBLICATION,
                    parameters={
                        "author_id": "researcher-structural",
                        "artifact_id": "paper-structural",
                        "title": "Community-governed output",
                    },
                ),
                ScheduleSpec("publication", 2),
            ),
        ),
    )
    funding = NodeSlot(
        "funding",
        (
            NodeOption(
                "fixed",
                MechanismSpec(
                    "funding",
                    MechanismFamily.FUNDING,
                    FIXED_GRANT,
                    outputs=(
                        PortSpec(
                            "allocations",
                            ChannelKind.RESOURCE,
                            "resource-allocation",
                        ),
                    ),
                    parameters={
                        "recipient_id": "researcher-funded",
                        "amount": 10,
                        "initial_balance": 0,
                        "start_period": 0,
                    },
                ),
                ScheduleSpec("funding", 0),
            ),
            NodeOption(
                "matching",
                MechanismSpec(
                    "funding",
                    MechanismFamily.FUNDING,
                    MATCHING_GRANT,
                    outputs=(
                        PortSpec(
                            "allocations",
                            ChannelKind.RESOURCE,
                            "resource-allocation",
                        ),
                    ),
                    parameters={
                        "recipient_id": "researcher-funded",
                        "base_amount": 6,
                        "match_ratio": 0.5,
                        "initial_balance": 0,
                        "start_period": 0,
                    },
                ),
                ScheduleSpec("funding", 0),
            ),
        ),
        optional=True,
    )
    research = NodeSlot(
        "research",
        (
            NodeOption(
                "resource-triggered",
                MechanismSpec(
                    "research",
                    MechanismFamily.RESEARCH,
                    RESOURCE_RESEARCH,
                    inputs=(
                        PortSpec(
                            "resources",
                            ChannelKind.RESOURCE,
                            "resource-allocation",
                            required=False,
                        ),
                    ),
                ),
                ScheduleSpec("research", 1),
            ),
            NodeOption(
                "autonomous",
                MechanismSpec(
                    "research",
                    MechanismFamily.RESEARCH,
                    AUTONOMOUS_RESEARCH,
                    parameters={"actor_id": "researcher-autonomous"},
                ),
                ScheduleSpec("research", 1),
            ),
        ),
        optional=True,
    )
    resource_edge = EdgeSlot(
        "resource-flow",
        (
            EdgeOption(
                "instant",
                ConnectionSpec(
                    "funding",
                    "allocations",
                    "research",
                    "resources",
                    ChannelKind.RESOURCE,
                    latency=0,
                ),
            ),
            EdgeOption(
                "delayed",
                ConnectionSpec(
                    "funding",
                    "allocations",
                    "research",
                    "resources",
                    ChannelKind.RESOURCE,
                    latency=1,
                ),
            ),
        ),
        optional=True,
    )
    return StructuralGrammar(
        space_id="toy-structural-science-system-v1",
        system_id="toy-structural-science-system",
        version=1,
        node_slots=(publication, funding, research),
        edge_slots=(resource_edge,),
        artifact_types=(allocation,),
        global_invariants=("strict-json-events", "typed-resource-flow"),
        metadata={
            "purpose": "structural-black-box-vertical-slice",
            "production_adapter": "not-bound",
        },
    )
