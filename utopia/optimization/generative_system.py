"""Compositional rule and graph synthesis, with opaque ask/tell support.

Candidates contain actual program ASTs. Mutation can create previously absent
rules/nodes rather than selecting from a pre-enumerated catalogue of systems.
The numeric language and resource limits still bound what can be invented.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import random
from typing import Any, Mapping

from utopia.system import (
    ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec,
    ScheduleSpec, SystemSpec, validate_system_spec,
)
from utopia.system.programs import (
    PROGRAM_IMPLEMENTATION, PROGRAM_SCHEMA, digest, validate_program,
)

FEATURES = ("quality", "novelty", "resources", "knowledge", "signal")
EFFECTS = ("allocation", "access", "learning", "effort")


def op(name: str, *args: Any) -> dict[str, Any]:
    return {"op": name, "args": list(args)}


def program_from_expression(expression: Mapping[str, Any]) -> dict[str, Any]:
    program = {
        "schema": PROGRAM_SCHEMA,
        "inputs": {name: "vector" for name in FEATURES},
        "parameters": {
            "gain": {"initial": 0.7, "minimum": -2.0, "maximum": 2.0},
            "bias": {"initial": -0.1, "minimum": -2.0, "maximum": 2.0},
        },
        "state": {"memory": 0.0},
        "output": op("add", op("mul", {"param": "gain"}, dict(expression)),
                     {"param": "bias"}),
        "updates": {"memory": op("add", op("mul", {"const": 0.6}, {"state": "memory"}),
                                 op("mul", {"const": 0.4}, dict(expression)))},
    }
    validate_program(program)
    return program


def random_expression(rng: random.Random, depth: int = 3) -> dict[str, Any]:
    """A recursive typed numeric grammar; no list of complete mechanisms."""
    if depth <= 0 or rng.random() < 0.25:
        tag = rng.choice(("input", "input", "param", "state", "const"))
        if tag == "input": return {tag: rng.choice(FEATURES)}
        if tag == "param": return {tag: rng.choice(("gain", "bias"))}
        if tag == "state": return {tag: "memory"}
        return {tag: round(rng.uniform(-1, 1), 5)}
    name = rng.choice(("add", "sub", "mul", "sigmoid", "tanh", "mean", "threshold"))
    arity = 2 if name in {"add", "sub", "mul", "threshold"} else 1
    return op(name, *(random_expression(rng, depth - 1) for _ in range(arity)))


def synthesize_program(*, seed: int, depth: int = 3) -> dict[str, Any]:
    return program_from_expression(random_expression(random.Random(seed), depth))


def mutate_program(program: Mapping[str, Any], *, seed: int) -> dict[str, Any]:
    """Replace an AST subtree or alter a parameter, retaining a legal program."""
    validate_program(program)
    rng = random.Random(seed)
    candidate = deepcopy(program)
    root = candidate["output"]
    locations: list[tuple[Any, Any]] = [(candidate, "output")]

    def visit(expr: Any) -> None:
        if "args" in expr:
            for index, arg in enumerate(expr["args"]):
                locations.append((expr["args"], index))
                visit(arg)

    visit(root)
    container, index = rng.choice(locations)
    container[index] = random_expression(rng, depth=2)
    validate_program(candidate)
    return candidate


def program_node(
    name: str, family: MechanismFamily, program: Mapping[str, Any],
    effects: Mapping[str, float], *, label: str | None = None,
) -> MechanismSpec:
    validate_program(program)
    return MechanismSpec(
        name, family, PROGRAM_IMPLEMENTATION,
        inputs=(PortSpec("in", ChannelKind.SIGNAL, required=False),),
        outputs=(PortSpec("out", ChannelKind.SIGNAL, required=False),),
        parameters={"program": deepcopy(program), "effects": dict(effects),
                    "label": label or name},
    )


def seed_generative_system() -> SystemSpec:
    nodes = (
        program_node("research", MechanismFamily.RESEARCH,
                     program_from_expression(op("add", {"input": "quality"},
                                                {"input": "resources"})),
                     {"effort": 0.5, "learning": 0.2}),
        program_node("evaluation", MechanismFamily.EVALUATION,
                     program_from_expression(op("threshold", {"input": "signal"},
                                                {"const": 0.3})),
                     {"access": 1.0}),
        program_node("publication", MechanismFamily.PUBLICATION,
                     program_from_expression(op("add", {"input": "signal"},
                                                {"input": "novelty"})),
                     {"learning": 0.6, "access": 0.4}),
        program_node("funding", MechanismFamily.FUNDING,
                     program_from_expression(op("sub", {"input": "signal"},
                                                {"input": "resources"})),
                     {"allocation": 1.0}),
    )
    edges = tuple(ConnectionSpec(a, "out", b, "in", ChannelKind.SIGNAL)
                  for a, b in (("research", "evaluation"),
                               ("evaluation", "publication"),
                               ("publication", "funding")))
    spec = SystemSpec(
        "generative-miniature", 1, mechanisms=nodes, connections=edges,
        schedules=tuple(ScheduleSpec(node.mechanism_id, index)
                        for index, node in enumerate(nodes)),
        metadata={"backend": "numeric-program-world-v1", "evidence_role": "development"},
    )
    validate_generative_system(spec)
    return spec


def validate_generative_system(spec: SystemSpec) -> None:
    validate_system_spec(spec).require_valid()
    if len(spec.mechanisms) > 8 or len(spec.connections) > 56:
        raise ValueError("numeric world supports 0..8 mechanisms and at most 56 edges")
    if len(spec.schedules) != len(spec.mechanisms):
        raise ValueError("every generated mechanism needs one schedule")
    for node in spec.mechanisms:
        if node.implementation != PROGRAM_IMPLEMENTATION or node.version != 1:
            raise ValueError("numeric world accepts program.numeric.v1 implementations")
        if (node.inputs != (PortSpec("in", ChannelKind.SIGNAL, required=False),)
                or node.outputs != (PortSpec("out", ChannelKind.SIGNAL, required=False),)):
            raise ValueError("numeric world requires the vector signal port protocol")
        validate_program(node.parameters["program"])
        inputs = node.parameters["program"]["inputs"]
        if any(key not in FEATURES or kind != "vector" for key, kind in inputs.items()):
            raise ValueError("program declares an input unavailable in the numeric world")
        effects = node.parameters["effects"]
        if not isinstance(effects, dict) or set(effects) - set(EFFECTS):
            raise ValueError("unknown numeric world effect")
        for value in effects.values():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not -2 <= value <= 2:
                raise ValueError("effect strength outside [-2,2]")
    if any(edge.latency not in (0, 1) for edge in spec.connections):
        raise ValueError("numeric world supports latency 0 or 1")
    if any(schedule.trigger != "annual" for schedule in spec.schedules):
        raise ValueError("numeric world supports annual schedules")


class GenerativeSystemSpace:
    """Optimizer adapter with program, node, edge, delay and order mutations."""

    def __init__(self, baseline: SystemSpec | None = None):
        self.baseline = baseline or seed_generative_system()
        validate_generative_system(self.baseline)

    def validate(self, candidate: Mapping[str, Any]) -> None:
        validate_generative_system(SystemSpec.from_dict(candidate))

    def sample(self, *, seed: int, proposal_index: int) -> Mapping[str, Any]:
        if proposal_index == 0:
            return self.baseline.to_dict()
        return self.mutate(self.baseline.to_dict(), seed=seed,
                           proposal_index=proposal_index, scale=0.3)

    def mutate(
        self, incumbent: Mapping[str, Any], *, seed: int,
        proposal_index: int, scale: float,
    ) -> Mapping[str, Any]:
        candidate, _ = self.mutate_with_record(
            incumbent, seed=seed, proposal_index=proposal_index,
        )
        return candidate

    def mutate_with_record(
        self, incumbent: Mapping[str, Any], *, seed: int,
        proposal_index: int, operation: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        self.validate(incumbent)
        spec = SystemSpec.from_dict(incumbent)
        rng = random.Random(f"{seed}:{proposal_index}:generative")
        options = ["program"] if spec.mechanisms else []
        if any(node.parameters["program"]["parameters"] for node in spec.mechanisms):
            options.append("parameter")
        if len(spec.mechanisms) < 8:
            options.append("add-node")
        if len(spec.mechanisms) > 1:
            options.append("order")
        if len(spec.connections) < len(spec.mechanisms) * (len(spec.mechanisms) - 1):
            options.append("add-edge")
        if spec.connections:
            options.extend(("remove-edge", "delay"))
        if spec.mechanisms:
            options.append("remove-node")
        operation = operation or rng.choice(options)
        nodes, edges, schedules = list(spec.mechanisms), list(spec.connections), list(spec.schedules)
        record: dict[str, Any] = {"operation": operation, "parent": spec.fingerprint}
        if operation in {"program", "parameter"}:
            available = [index for index, node in enumerate(nodes) if (
                operation == "program" or node.parameters["program"]["parameters"]
            )]
            index = rng.choice(available)
            node = nodes[index]
            parameters = deepcopy(node.parameters)
            old_program = parameters["program"]
            if operation == "program":
                parameters["program"] = mutate_program(old_program, seed=rng.randrange(2**32))
            else:
                if not old_program["parameters"]:
                    raise ValueError("selected mechanism has no mutable parameters")
                name = rng.choice(list(old_program["parameters"]))
                config = old_program["parameters"][name]
                config["initial"] = rng.uniform(config["minimum"], config["maximum"])
            nodes[index] = replace(node, parameters=parameters)
            record["mechanism_id"] = node.mechanism_id
            record["program_sha256"] = digest(parameters["program"])
        elif operation == "add-node":
            if len(nodes) == 8:
                raise ValueError("mechanism budget exhausted")
            suffix = hashlib.sha256(f"{seed}:{proposal_index}".encode()).hexdigest()[:8]
            name = f"commons-{suffix}"
            if name in {node.mechanism_id for node in nodes}:
                raise ValueError("generated duplicate node id")
            node = program_node(
                name, MechanismFamily.CUSTOM,
                synthesize_program(seed=rng.randrange(2**32)),
                {rng.choice(EFFECTS): round(rng.uniform(0.1, 1.2), 5)},
                label="Generated commons mechanism",
            )
            source = rng.choice(nodes).mechanism_id if nodes else None
            nodes.append(node)
            schedules.append(ScheduleSpec(name, max((s.phase for s in schedules), default=-1) + 1))
            if source is not None:
                edges.append(ConnectionSpec(source, "out", name, "in", ChannelKind.SIGNAL))
            record.update({"mechanism_id": name, "program_sha256": digest(node.parameters["program"])})
        elif operation == "remove-node":
            if not nodes:
                raise ValueError("graph has no mechanism to remove")
            name = rng.choice(nodes).mechanism_id
            nodes = [node for node in nodes if node.mechanism_id != name]
            edges = [edge for edge in edges if name not in (edge.source_mechanism, edge.target_mechanism)]
            schedules = [item for item in schedules if item.mechanism_id != name]
            record["mechanism_id"] = name
        elif operation == "add-edge":
            existing = {(edge.source_mechanism, edge.target_mechanism) for edge in edges}
            available = [(a.mechanism_id, b.mechanism_id) for a in nodes for b in nodes
                         if a != b and (a.mechanism_id, b.mechanism_id) not in existing]
            if not available:
                raise ValueError("no new edge possible")
            source, target = rng.choice(available)
            edges.append(ConnectionSpec(source, "out", target, "in", ChannelKind.SIGNAL,
                                        latency=rng.randrange(2)))
            record["edge"] = [source, target]
        elif operation in {"remove-edge", "delay"}:
            if not edges:
                raise ValueError("graph has no edge to mutate")
            index = rng.randrange(len(edges))
            record["edge"] = [edges[index].source_mechanism, edges[index].target_mechanism]
            if operation == "remove-edge": edges.pop(index)
            else: edges[index] = replace(edges[index], latency=1 - edges[index].latency)
        elif operation == "order":
            if len(schedules) < 2:
                raise ValueError("order mutation needs two mechanisms")
            schedules.sort(key=lambda item: (item.phase, item.mechanism_id))
            first, second = rng.sample(range(len(schedules)), 2)
            schedules[first], schedules[second] = schedules[second], schedules[first]
            schedules = [replace(item, phase=index) for index, item in enumerate(schedules)]
            record["order"] = [item.mechanism_id for item in schedules]
        else:
            raise ValueError(f"unknown mutation {operation!r}")
        candidate = replace(spec, mechanisms=tuple(nodes), connections=tuple(edges),
                            schedules=tuple(schedules))
        validate_generative_system(candidate)
        record["child"] = candidate.fingerprint
        return candidate.to_dict(), record
