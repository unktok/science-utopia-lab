"""Bounded numeric programs for mechanisms invented during system search.

The AST is data, never Python source. Both tensor simulation and the ordinary
graph runner execute this interpreter. New rules need no Python registration.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import math
import re
from typing import Any

import torch

from .runtime import (
    MechanismContext, MechanismEvent, MechanismRegistry,
    MechanismResult, MechanismValue,
)

PROGRAM_SCHEMA = "scienceutopia.mechanism-program.v1"
PROGRAM_IMPLEMENTATION = "program.numeric.v1"
MAX_DEPTH = 10
MAX_NODES = 160
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{0,47}$")
ARITY = {"add": 2, "sub": 2, "mul": 2, "square": 1, "sigmoid": 1,
         "tanh": 1, "mean": 1, "softmax": 1, "threshold": 2}


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()


def _number(value: Any) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and abs(value) <= 100)


def validate_program(program: Mapping[str, Any]) -> None:
    """Check names, tensor shapes, bounds, references and AST resource limits."""
    fields = {"schema", "inputs", "parameters", "state", "output", "updates"}
    if not isinstance(program, Mapping) or set(program) != fields:
        raise ValueError("program fields do not match mechanism-program.v1")
    if program["schema"] != PROGRAM_SCHEMA:
        raise ValueError("unsupported mechanism program schema")
    for group in ("inputs", "parameters", "state", "updates"):
        values = program[group]
        if not isinstance(values, dict) or len(values) > 32:
            raise ValueError(f"program {group} must be an object with at most 32 names")
        if any(not isinstance(k, str) or not IDENTIFIER.fullmatch(k) for k in values):
            raise ValueError(f"invalid {group} identifier")
    if any(not isinstance(kind, str) or kind not in {"scalar", "vector"}
           for kind in program["inputs"].values()):
        raise ValueError("program input type must be scalar or vector")
    for config in program["parameters"].values():
        if not isinstance(config, dict) or set(config) != {"initial", "minimum", "maximum"}:
            raise ValueError("parameter must declare initial, minimum, maximum")
        if not all(_number(value) for value in config.values()):
            raise ValueError("parameter bounds must be finite bounded numbers")
        if not config["minimum"] <= config["initial"] <= config["maximum"]:
            raise ValueError("parameter initial value outside bounds")
        if config["minimum"] >= config["maximum"]:
            raise ValueError("parameter has empty domain")
    if any(not _number(value) for value in program["state"].values()):
        raise ValueError("state initializers must be finite bounded numbers")
    if set(program["updates"]) != set(program["state"]):
        raise ValueError("updates must cover exactly the declared state")
    count = 0

    def check(expr: Any, depth: int) -> str:
        nonlocal count
        count += 1
        if depth > MAX_DEPTH or count > MAX_NODES:
            raise ValueError("program exceeds AST resource limit")
        if not isinstance(expr, dict):
            raise ValueError("expression must be an AST object")
        for tag, group in (("input", "inputs"), ("param", "parameters"), ("state", "state")):
            if set(expr) == {tag}:
                if not isinstance(expr[tag], str) or expr[tag] not in program[group]:
                    raise ValueError(f"unresolved {tag} reference")
                return program[group][expr[tag]] if tag == "input" else (
                    "scalar" if tag == "param" else "vector"
                )
        if set(expr) == {"const"} and _number(expr["const"]):
            return "scalar"
        if set(expr) != {"op", "args"} or not isinstance(expr["op"], str):
            raise ValueError("unknown expression fields")
        op = expr["op"]
        if op not in ARITY or not isinstance(expr["args"], list):
            raise ValueError("unsupported expression operator")
        if len(expr["args"]) != ARITY[op]:
            raise ValueError(f"wrong arity for {op}")
        kinds = [check(arg, depth + 1) for arg in expr["args"]]
        if op == "mean":
            return "scalar"
        if op == "softmax" and kinds != ["vector"]:
            raise ValueError("softmax requires a vector")
        return "vector" if "vector" in kinds else "scalar"

    check(program["output"], 0)
    for expression in program["updates"].values():
        check(expression, 0)


def execute_program(
    program: Mapping[str, Any],
    inputs: Mapping[str, torch.Tensor],
    *,
    size: int,
    state: Mapping[str, torch.Tensor] | None = None,
    parameters: Mapping[str, torch.Tensor] | None = None,
    hard: bool = False,
    temperature: float = 0.25,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Execute a checked AST; threshold has exact and smooth interpretations.

    All state assignments are simultaneous. Scalars broadcast over agents.
    Final outputs/state use tanh as a declared bounded numeric protocol.
    """
    validate_program(program)
    if size < 1 or not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("size and temperature must be positive")
    if not set(program["inputs"]) <= set(inputs):
        raise ValueError("missing declared program input")
    anchor = next(iter(inputs.values()), torch.zeros(size, dtype=torch.float64))

    def tensor(value: Any) -> torch.Tensor:
        return torch.as_tensor(value, dtype=anchor.dtype, device=anchor.device)

    for key, kind in program["inputs"].items():
        value = inputs[key]
        if value.shape != (torch.Size([size]) if kind == "vector" else torch.Size([])):
            raise ValueError(f"input {key!r} violates declared shape")
        if not torch.isfinite(value).all():
            raise ValueError(f"input {key!r} must be finite")
    states = {key: tensor(value).expand(size) for key, value in program["state"].items()}
    if state is not None:
        if set(state) != set(states):
            raise ValueError("state layout mismatch")
        states = dict(state)
    params = {key: tensor(value["initial"]) for key, value in program["parameters"].items()}
    if parameters is not None:
        if set(parameters) != set(params):
            raise ValueError("parameter layout mismatch")
        params = dict(parameters)

    def evaluate(expr: Mapping[str, Any]) -> torch.Tensor:
        if "const" in expr:
            return tensor(expr["const"])
        if "input" in expr:
            return inputs[expr["input"]]
        if "param" in expr:
            return params[expr["param"]]
        if "state" in expr:
            return states[expr["state"]]
        args = [evaluate(arg) for arg in expr["args"]]
        op = expr["op"]
        if op == "add": return args[0] + args[1]
        if op == "sub": return args[0] - args[1]
        if op == "mul": return args[0] * args[1]
        if op == "square": return args[0].square()
        if op == "sigmoid": return args[0].sigmoid()
        if op == "tanh": return args[0].tanh()
        if op == "mean": return args[0].mean()
        if op == "softmax": return args[0].softmax(dim=0)
        if op == "threshold":
            difference = args[0] - args[1]
            return (difference >= 0).to(anchor.dtype) if hard else (
                difference / temperature
            ).sigmoid()
        raise AssertionError(op)

    output = evaluate(program["output"]).expand(size).tanh()
    updated = {key: evaluate(expr).expand(size).tanh()
               for key, expr in program["updates"].items()}
    if not torch.isfinite(output).all() or any(
        not torch.isfinite(value).all() for value in updated.values()
    ):
        raise ValueError("program produced non-finite output/state")
    return output, updated


def register_program_interpreter(registry: MechanismRegistry) -> None:
    """One interpreter registration supports every generated program."""
    registry.register(PROGRAM_IMPLEMENTATION, 1, program_handler)


def program_handler(context: MechanismContext) -> MechanismResult:
    program = context.mechanism.parameters["program"]
    validate_program(program)
    external = context.initial_state.get("program_inputs", {})
    size = context.initial_state.get("population_size", 4)
    if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 100:
        raise ValueError("program population_size must be in [1,100]")
    inputs = {key: torch.as_tensor(value, dtype=torch.float64)
              for key, value in external.items()}
    delivered = [torch.tensor(value.payload["values"], dtype=torch.float64)
                 for value in context.inputs.get("in", ())]
    inputs["signal"] = torch.stack(delivered).sum(0) if delivered else torch.zeros(
        size, dtype=torch.float64
    )
    saved = context.state.get("values")
    state = None if saved is None else {
        key: torch.tensor(value, dtype=torch.float64) for key, value in saved.items()
    }
    output, next_state = execute_program(program, inputs, size=size, state=state, hard=True)
    values = output.tolist()
    return MechanismResult(
        outputs={"out": (MechanismValue({"values": values}),)},
        events=(MechanismEvent(
            event_type="mechanism.program.executed",
            payload={"values": values, "program_sha256": digest(program)},
        ),),
        next_state={"values": {key: value.tolist() for key, value in next_state.items()}},
    )
