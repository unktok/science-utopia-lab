"""Closed loops for generated rules and a differentiable recurrent world."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import math
from typing import Any

import torch

from utopia.optimization.blackbox import AdaptiveRandomSearch, Observation
from utopia.optimization.generative_system import GenerativeSystemSpace, validate_generative_system
from utopia.optimization.loss import loss_spec_sha256
from utopia.system import SystemSpec
from utopia.system.program_world import (
    RelaxedProgramSystem, aggregate_tensor_loss, evaluate_program_system,
    rollout, tensor_loss,
)
from utopia.system.programs import digest


def differentiable_objective(
    design: RelaxedProgramSystem, worlds: list[Mapping[str, Any]],
    loss_spec: Mapping[str, Any], *, periods: int,
) -> torch.Tensor:
    return aggregate_tensor_loss([
        tensor_loss(rollout(design, world, periods=periods)["metrics"], loss_spec)
        for world in worlds
    ], loss_spec)


def gradient_audit(
    design: RelaxedProgramSystem, worlds: list[Mapping[str, Any]],
    loss_spec: Mapping[str, Any], *, periods: int = 3, epsilon: float = 1e-5,
) -> dict[str, Any]:
    """Central differences of the complete recurrent objective, by variable family."""
    design.zero_grad(set_to_none=True)
    loss = differentiable_objective(design, worlds, loss_spec, periods=periods)
    loss.backward()
    groups: dict[str, tuple[str, torch.nn.Parameter, int, float]] = {}
    for name, parameter in design.named_parameters():
        if parameter.grad is None:
            continue
        group = name.split(".")[0]
        index = int(parameter.grad.abs().flatten().argmax())
        analytic = float(parameter.grad.flatten()[index])
        if group not in groups or abs(analytic) > abs(groups[group][3]):
            groups[group] = name, parameter, index, analytic
    records = []
    for group, (name, parameter, index, analytic) in groups.items():
        with torch.no_grad():
            flat = parameter.flatten()
            original = float(flat[index])
            try:
                flat[index] = original + epsilon
                plus = float(differentiable_objective(design, worlds, loss_spec, periods=periods))
                flat[index] = original - epsilon
                minus = float(differentiable_objective(design, worlds, loss_spec, periods=periods))
            finally:
                flat[index] = original
        numerical = (plus - minus) / (2 * epsilon)
        error = abs(analytic - numerical)
        records.append({"group": group, "parameter": name, "index": index,
                        "analytic": analytic, "central_difference": numerical,
                        "absolute_error": error,
                        "passes": error <= 1e-6 + 1e-4 * abs(numerical)})
    return {"method": "central-difference-whole-rollout", "epsilon": epsilon,
            "records": records, "all_pass": all(item["passes"] for item in records)}


def optimize_program_world(
    system: SystemSpec, worlds: list[Mapping[str, Any]], loss_spec: Mapping[str, Any], *,
    steps: int = 24, learning_rate: float = 0.12, periods: int = 3,
    alternatives: int = 3, seed: int = 0, freedom: str = "process",
) -> dict[str, Any]:
    if isinstance(steps, bool) or not isinstance(steps, int) or not 1 <= steps <= 200:
        raise ValueError("steps must be in [1,200]")
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("learning_rate must be positive and finite")
    design = RelaxedProgramSystem(system, alternatives=alternatives, seed=seed, freedom=freedom)
    initial, _ = design.project()
    initial_outer = evaluate_program_system(initial, worlds, loss_spec, periods=periods)
    audit = gradient_audit(design, worlds, loss_spec, periods=periods)
    if not audit["all_pass"]:
        raise ValueError("whole-world gradient audit failed")
    optimizer = torch.optim.Adam([parameter for parameter in design.parameters()
                                  if parameter.requires_grad], lr=learning_rate)
    best_state = deepcopy(design.state_dict())
    best_relaxed = float("inf")
    trace = []
    for step in range(steps + 1):
        optimizer.zero_grad(set_to_none=True)
        loss = differentiable_objective(design, worlds, loss_spec, periods=periods)
        if not torch.isfinite(loss):
            raise ValueError("non-finite differentiable objective")
        loss.backward()
        squared_norm = sum(float(parameter.grad.square().sum()) for parameter in design.parameters()
                           if parameter.grad is not None)
        scalar = float(loss.detach())
        trace.append({"step": step, "relaxed_loss": scalar,
                      "gradient_norm": math.sqrt(squared_norm)})
        if scalar < best_relaxed:
            best_relaxed = scalar
            best_state = deepcopy(design.state_dict())
        if step != steps:
            torch.nn.utils.clip_grad_norm_(design.parameters(), 5.0)
            optimizer.step()
    design.load_state_dict(best_state)
    projected, decisions = design.project()
    outer = evaluate_program_system(projected, worlds, loss_spec, periods=periods, record=True)
    return {
        "method": "direct-differentiable-program-world", "design_freedom": freedom,
        "loss_spec_sha256": loss_spec_sha256(loss_spec),
        "baseline_system": system.to_dict(), "initial_projected_system": initial.to_dict(),
        "world_sha256": [digest(world) for world in worlds],
        "rule_bank": design.bank,
        "schedule_alternatives": [list(order) for order in design.orders],
        "trace": trace, "gradient_audit": audit,
        "initial_outer": initial_outer, "final_outer": outer,
        "best_relaxed_loss": best_relaxed,
        "relaxation_projection_gap": outer["loss"] - best_relaxed,
        "projection": decisions, "system_spec": projected.to_dict(),
        "parameter_state": {name: value.tolist() for name, value in design.state_dict().items()},
        "interpretation": {
            "autograd_scope": "entire numeric world rollout and mechanism programs",
            "qwen_in_autograd": False,
            "schedule_relaxation": "within-period branch mixture with mixed recurrent boundary state",
            "optimizer_efficiency_claim": False,
        },
    }


def search_program_systems(
    system: SystemSpec, worlds: list[Mapping[str, Any]], loss_spec: Mapping[str, Any], *,
    budget: int = 6, seed: int = 17, periods: int = 3,
) -> dict[str, Any]:
    if isinstance(budget, bool) or not isinstance(budget, int) or not 1 <= budget <= 50:
        raise ValueError("budget must be in [1,50]")
    space = GenerativeSystemSpace(system)
    optimizer = AdaptiveRandomSearch(space, seed=seed, initial_random=min(2, budget))
    records = []
    for _ in range(budget):
        suggestion = optimizer.ask(1)[0]
        candidate = SystemSpec.from_dict(suggestion.candidate)
        try:
            validate_generative_system(candidate)
            outer = evaluate_program_system(candidate, worlds, loss_spec, periods=periods, record=True)
            observation = Observation(
                "o" + digest({"suggestion": suggestion.suggestion_id, "outer": outer})[:20],
                suggestion.suggestion_id, suggestion.candidate, "complete", loss=outer["loss"],
                metadata={"loss_spec_sha256": loss_spec_sha256(loss_spec),
                          "system_fingerprint": candidate.fingerprint},
            )
        except (ValueError, RuntimeError) as error:
            outer = {"status": "failed", "loss": None, "reason": str(error)}
            observation = Observation(
                "o" + digest({"suggestion": suggestion.suggestion_id, "failure": str(error)})[:20],
                suggestion.suggestion_id, suggestion.candidate, "failed", metadata=outer,
            )
        optimizer.tell([observation])
        records.append({"suggestion": suggestion.to_dict(), "observation": observation.to_dict(),
                        "outer": outer, "system_fingerprint": candidate.fingerprint,
                        "program_hashes": {node.mechanism_id: digest(node.parameters["program"])
                                           for node in candidate.mechanisms}})
    valid = [record for record in records if record["observation"]["status"] == "complete"]
    best = min(valid, key=lambda record: record["observation"]["loss"]) if valid else None
    return {
        "method": "generative-black-box", "loss_spec_sha256": loss_spec_sha256(loss_spec),
        "budget": budget, "records": records, "optimizer_state": optimizer.state_dict(),
        "best_suggestion_id": best["suggestion"]["suggestion_id"] if best else None,
        "system_spec": best["suggestion"]["candidate"] if best else None,
        "best_loss": best["observation"]["loss"] if best else None,
    }
