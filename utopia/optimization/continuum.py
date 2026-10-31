"""One optimization boundary across progressively freer science systems.

There are two independent questions:

* design freedom: which parts of a science system may change; and
* search method: how a candidate is proposed.

This module makes that distinction executable.  A black-box optimizer and a
differentiable surrogate can explore nested views of the same relaxed
whole-system template, project through the same deterministic ``SystemSpec``
boundary, and call the same opaque outer evaluator.

The implementation is intentionally a compact development slice.  It does not
turn synthetic losses into policy claims and it does not make the real
simulator differentiable.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import math
import random
from typing import Any, Mapping, Sequence

from utopia.optimization.blackbox import (
    AdaptiveRandomSearch,
    Observation,
    Suggestion,
    canonical_json,
)
from utopia.optimization.differentiable_system import (
    BlackBoxSystemEvaluator,
    DifferentiableSurrogate,
    DifferentiableSystemSpace,
    ProjectionResult,
    optimize_relaxed,
)


RAW_CANDIDATE_SCHEMA = "scienceutopia.relaxed-system-candidate.v1"
CONTINUUM_REPORT_SCHEMA = "scienceutopia.optimization-continuum-report.v1"


class DesignFreedom(str, Enum):
    """Nested design spaces, ordered from local tuning to open invention."""

    PARAMETERS = "parameters"
    MECHANISM_CONFIGURATION = "mechanism-configuration"
    GRAPH_STRUCTURE = "graph-structure"
    OPEN_ENDED_SYSTEM = "open-ended-system"


class SearchMethod(str, Enum):
    """Candidate-generation method, independent of design freedom."""

    BLACK_BOX = "black-box"
    DIFFERENTIABLE_SURROGATE = "differentiable-surrogate"
    HYBRID = "hybrid-gradient-black-box"


@dataclass(frozen=True)
class OptimizationCoordinate:
    design_freedom: DesignFreedom
    search_method: SearchMethod

    def __post_init__(self) -> None:
        if self.design_freedom is DesignFreedom.OPEN_ENDED_SYSTEM:
            raise ValueError(
                "open-ended system synthesis is a declared frontier, not an "
                "executable design space"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "design_freedom": self.design_freedom.value,
            "search_method": self.search_method.value,
        }


def mutable_raw_ids(
    space: DifferentiableSystemSpace, freedom: DesignFreedom
) -> tuple[str, ...]:
    """Return the relaxed variables exposed at one nested freedom level."""

    if freedom is DesignFreedom.OPEN_ENDED_SYSTEM:
        raise ValueError("open-ended system synthesis has no frozen executable grammar")
    allowed: list[str] = []
    for raw_id in space.raw_ids:
        if raw_id.startswith("parameter:"):
            allowed.append(raw_id)
        elif (
            freedom
            in {DesignFreedom.MECHANISM_CONFIGURATION, DesignFreedom.GRAPH_STRUCTURE}
            and raw_id.startswith("implementation-logit:")
        ):
            allowed.append(raw_id)
        elif freedom is DesignFreedom.GRAPH_STRUCTURE and raw_id.startswith(
            ("presence-logit:", "edge-logit:")
        ):
            allowed.append(raw_id)
    if not allowed:
        raise ValueError(f"design freedom {freedom.value!r} exposes no variables")
    return tuple(allowed)


class RelaxedVectorSearchSpace:
    """Gradient-free search over a differentiable template's raw coordinates.

    Black-box search never reads gradients or surrogate predictions.  It sees
    only bounded numeric coordinates.  Projection is deliberately outside the
    optimizer so every search method crosses the same discrete boundary.
    """

    def __init__(
        self,
        space: DifferentiableSystemSpace,
        freedom: DesignFreedom,
        *,
        center_raw: Mapping[str, float] | None = None,
        sample_radius: float | None = None,
        logit_bound: float = 6.0,
    ) -> None:
        if logit_bound <= 0:
            raise ValueError("logit_bound must be positive")
        if sample_radius is not None and not 0 < sample_radius <= 1:
            raise ValueError("sample_radius must be in (0, 1]")
        self.space = space
        self.freedom = freedom
        self.mutable_ids = mutable_raw_ids(space, freedom)
        self._mutable = set(self.mutable_ids)
        self._frozen_anchor = space.initial_raw()
        self._center = dict(self._frozen_anchor if center_raw is None else center_raw)
        space.features(self._center)
        for raw_id in set(space.raw_ids) - self._mutable:
            if self._center[raw_id] != self._frozen_anchor[raw_id]:
                raise ValueError(
                    f"center_raw changes frozen variable {raw_id!r} at "
                    f"freedom level {freedom.value!r}"
                )
        self.sample_radius = sample_radius
        self.logit_bound = float(logit_bound)

    @staticmethod
    def _rng(seed: int, proposal_index: int, purpose: str) -> random.Random:
        material = f"{seed}:{proposal_index}:{purpose}".encode()
        derived = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
        return random.Random(derived)

    def _candidate(self, raw: Mapping[str, float]) -> dict[str, Any]:
        candidate = {
            "schema": RAW_CANDIDATE_SCHEMA,
            "design_id": str(self.space.spec["id"]),
            "freedom": self.freedom.value,
            "raw": {key: float(raw[key]) for key in self.space.raw_ids},
        }
        self.validate(candidate)
        return candidate

    def _raw(self, candidate: Mapping[str, Any]) -> dict[str, float]:
        if set(candidate) != {"schema", "design_id", "freedom", "raw"}:
            raise ValueError("relaxed candidate has unknown or missing fields")
        if candidate["schema"] != RAW_CANDIDATE_SCHEMA:
            raise ValueError("unsupported relaxed candidate schema")
        if candidate["design_id"] != self.space.spec["id"]:
            raise ValueError("candidate belongs to a different design template")
        if candidate["freedom"] != self.freedom.value:
            raise ValueError("candidate belongs to a different freedom level")
        raw_value = candidate["raw"]
        if not isinstance(raw_value, Mapping):
            raise ValueError("candidate raw vector must be an object")
        if set(raw_value) != set(self.space.raw_ids):
            raise ValueError("candidate raw vector does not match the design layout")
        raw: dict[str, float] = {}
        for key in self.space.raw_ids:
            value = raw_value[key]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError("candidate raw vector must contain finite numbers")
            numeric = float(value)
            if key.startswith("parameter:") and not 0.0 <= numeric <= 1.0:
                raise ValueError(f"continuous variable {key!r} is outside [0, 1]")
            if not key.startswith("parameter:") and abs(numeric) > self.logit_bound:
                raise ValueError(f"logit {key!r} exceeds the configured bound")
            if key not in self._mutable and numeric != self._frozen_anchor[key]:
                raise ValueError(f"candidate changes frozen variable {key!r}")
            raw[key] = numeric
        self.space.features(raw)
        return raw

    def validate(self, candidate: Mapping[str, Any]) -> None:
        self._raw(candidate)

    def sample(self, *, seed: int, proposal_index: int) -> Mapping[str, Any]:
        rng = self._rng(seed, proposal_index, "sample")
        raw = dict(self._center)
        if self.sample_radius is not None and proposal_index == 0:
            return self._candidate(raw)
        for key in self.mutable_ids:
            center = self._center[key]
            if key.startswith("parameter:"):
                if self.sample_radius is None:
                    raw[key] = rng.random()
                else:
                    raw[key] = min(
                        max(center + rng.uniform(-self.sample_radius, self.sample_radius), 0.0),
                        1.0,
                    )
            elif self.sample_radius is None:
                raw[key] = rng.uniform(-self.logit_bound, self.logit_bound)
            else:
                width = 2.0 * self.logit_bound * self.sample_radius
                raw[key] = min(
                    max(center + rng.uniform(-width, width), -self.logit_bound),
                    self.logit_bound,
                )
        return self._candidate(raw)

    def mutate(
        self,
        incumbent: Mapping[str, Any],
        *,
        seed: int,
        proposal_index: int,
        scale: float,
    ) -> Mapping[str, Any]:
        if not 0 < scale <= 1:
            raise ValueError("mutation scale must be in (0, 1]")
        raw = self._raw(incumbent)
        rng = self._rng(seed, proposal_index, "mutate")
        for key in self.mutable_ids:
            if key.startswith("parameter:"):
                raw[key] = min(max(rng.gauss(raw[key], scale), 0.0), 1.0)
            else:
                raw[key] = min(
                    max(
                        rng.gauss(raw[key], scale * 2.0 * self.logit_bound),
                        -self.logit_bound,
                    ),
                    self.logit_bound,
                )
        return self._candidate(raw)

    def project(self, candidate: Mapping[str, Any]) -> ProjectionResult:
        return self.space.project(self._raw(candidate))


@dataclass(frozen=True)
class ProjectedSystemEvaluation:
    proposal_id: str
    coordinate: OptimizationCoordinate
    source_raw: Mapping[str, float]
    projection: ProjectionResult
    outer_evaluation: Mapping[str, Any]
    lineage: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "coordinate": self.coordinate.to_dict(),
            "source_raw": dict(self.source_raw),
            "system_fingerprint": self.projection.system_spec.fingerprint,
            "system_spec": self.projection.system_spec.to_dict(),
            "projected_features": dict(self.projection.features),
            "projection_decisions": list(self.projection.decisions),
            "outer_evaluation": dict(self.outer_evaluation),
            "lineage": dict(self.lineage),
        }


def evaluate_projected_raw(
    *,
    proposal_id: str,
    coordinate: OptimizationCoordinate,
    space: DifferentiableSystemSpace,
    raw: Mapping[str, float],
    evaluator: BlackBoxSystemEvaluator,
    loss_spec: Mapping[str, Any],
    scenarios: Sequence[str],
    lineage: Mapping[str, Any],
) -> ProjectedSystemEvaluation:
    """Project and evaluate one proposal through the method-neutral boundary."""

    projection = space.project(raw)
    outer = dict(evaluator.evaluate(projection.system_spec, loss_spec, scenarios))
    status = outer.get("status")
    if status not in {"complete", "invalid", "failed"}:
        raise ValueError("outer evaluator returned an unsupported technical status")
    loss = outer.get("loss")
    if status == "complete":
        if (
            isinstance(loss, bool)
            or not isinstance(loss, (int, float))
            or not math.isfinite(loss)
        ):
            raise ValueError("complete outer evaluation requires a finite scalar loss")
    elif loss is not None:
        raise ValueError("invalid or failed outer evaluation must not carry a loss")
    if outer.get("system_fingerprint") != projection.system_spec.fingerprint:
        raise ValueError("outer evaluator returned a mismatched system fingerprint")
    return ProjectedSystemEvaluation(
        proposal_id=proposal_id,
        coordinate=coordinate,
        source_raw={key: float(raw[key]) for key in space.raw_ids},
        projection=projection,
        outer_evaluation=outer,
        lineage=lineage,
    )


def evaluate_black_box_suggestion(
    suggestion: Suggestion,
    *,
    coordinate: OptimizationCoordinate,
    search_space: RelaxedVectorSearchSpace,
    evaluator: BlackBoxSystemEvaluator,
    loss_spec: Mapping[str, Any],
    scenarios: Sequence[str],
) -> tuple[Observation, ProjectedSystemEvaluation]:
    if coordinate.search_method not in {SearchMethod.BLACK_BOX, SearchMethod.HYBRID}:
        raise ValueError("black-box suggestion requires a black-box or hybrid coordinate")
    raw = search_space._raw(suggestion.candidate)
    projected = evaluate_projected_raw(
        proposal_id=suggestion.suggestion_id,
        coordinate=coordinate,
        space=search_space.space,
        raw=raw,
        evaluator=evaluator,
        loss_spec=loss_spec,
        scenarios=scenarios,
        lineage={
            "phase": suggestion.phase,
            "based_on_observation_id": suggestion.based_on_observation_id,
        },
    )
    observation_id = "o" + hashlib.sha256(
        canonical_json(
            {
                "suggestion_id": suggestion.suggestion_id,
                "system_fingerprint": projected.projection.system_spec.fingerprint,
                "loss": projected.outer_evaluation["loss"],
            }
        ).encode()
    ).hexdigest()[:16]
    observation = Observation(
        observation_id=observation_id,
        suggestion_id=suggestion.suggestion_id,
        candidate=suggestion.candidate,
        status=str(projected.outer_evaluation["status"]),
        loss=(
            float(projected.outer_evaluation["loss"])
            if projected.outer_evaluation["status"] == "complete"
            else None
        ),
        metadata={
            "projected_system": projected.to_dict(),
            "measurement_role": "synthetic-optimization-development",
        },
    )
    return observation, projected


def run_black_box_episode(
    *,
    space: DifferentiableSystemSpace,
    freedom: DesignFreedom,
    evaluator: BlackBoxSystemEvaluator,
    loss_spec: Mapping[str, Any],
    scenarios: Sequence[str],
    seed: int,
    budget: int,
    initial_random: int = 2,
    center_raw: Mapping[str, float] | None = None,
    method: SearchMethod = SearchMethod.BLACK_BOX,
) -> dict[str, Any]:
    """Run a tiny result-dependent black-box episode on a nested design space."""

    if budget < 1:
        raise ValueError("budget must be positive")
    if method is SearchMethod.DIFFERENTIABLE_SURROGATE:
        raise ValueError("use run_differentiable_episode for gradient search")
    coordinate = OptimizationCoordinate(freedom, method)
    search_space = RelaxedVectorSearchSpace(
        space,
        freedom,
        center_raw=center_raw,
        sample_radius=0.15 if center_raw is not None else None,
    )
    optimizer = AdaptiveRandomSearch(
        search_space,
        seed=seed,
        initial_random=min(initial_random, budget),
        mutation_scale=0.2,
    )
    records = []
    for _ in range(budget):
        suggestion = optimizer.ask(1)[0]
        observation, projected = evaluate_black_box_suggestion(
            suggestion,
            coordinate=coordinate,
            search_space=search_space,
            evaluator=evaluator,
            loss_spec=loss_spec,
            scenarios=scenarios,
        )
        optimizer.tell([observation])
        records.append(
            {
                "suggestion": suggestion.to_dict(),
                "observation": observation.to_dict(),
                "projected": projected.to_dict(),
            }
        )
    complete = [item for item in records if item["observation"]["status"] == "complete"]
    best = (
        min(complete, key=lambda item: item["observation"]["loss"])
        if complete
        else None
    )
    return {
        "schema": CONTINUUM_REPORT_SCHEMA,
        "coordinate": coordinate.to_dict(),
        "design_id": space.spec["id"],
        "mutable_raw_ids": list(search_space.mutable_ids),
        "budget": budget,
        "records": records,
        "best_proposal_id": (
            best["suggestion"]["suggestion_id"] if best is not None else None
        ),
        "best_system_fingerprint": (
            best["projected"]["system_fingerprint"] if best is not None else None
        ),
        "best_loss": best["observation"]["loss"] if best is not None else None,
        "optimizer_state_sha256": hashlib.sha256(
            canonical_json(optimizer.state_dict()).encode()
        ).hexdigest(),
    }


def run_differentiable_episode(
    *,
    space: DifferentiableSystemSpace,
    freedom: DesignFreedom,
    surrogate: DifferentiableSurrogate,
    optimizer_config: Mapping[str, Any],
    evaluator: BlackBoxSystemEvaluator,
    loss_spec: Mapping[str, Any],
    scenarios: Sequence[str],
) -> dict[str, Any]:
    """Run gradient search and pass only its projection to the outer evaluator."""

    coordinate = OptimizationCoordinate(freedom, SearchMethod.DIFFERENTIABLE_SURROGATE)
    mutable = mutable_raw_ids(space, freedom)
    inner = optimize_relaxed(
        space,
        surrogate,
        optimizer_config,
        mutable_raw_ids=mutable,
    )
    optimized_raw = inner["optimized_raw"]
    proposal_id = "g" + hashlib.sha256(
        canonical_json(
            {
                "design_id": space.spec["id"],
                "freedom": freedom.value,
                "raw": optimized_raw,
            }
        ).encode()
    ).hexdigest()[:16]
    projected = evaluate_projected_raw(
        proposal_id=proposal_id,
        coordinate=coordinate,
        space=space,
        raw=optimized_raw,
        evaluator=evaluator,
        loss_spec=loss_spec,
        scenarios=scenarios,
        lineage={
            "phase": "gradient-projection",
            "iterations": optimizer_config["iterations"],
        },
    )
    return {
        "schema": CONTINUUM_REPORT_SCHEMA,
        "coordinate": coordinate.to_dict(),
        "design_id": space.spec["id"],
        "mutable_raw_ids": list(mutable),
        "inner": inner,
        "projected": projected.to_dict(),
        "outer_loss": projected.outer_evaluation["loss"],
    }


def run_hybrid_episode(
    *,
    space: DifferentiableSystemSpace,
    freedom: DesignFreedom,
    surrogate: DifferentiableSurrogate,
    optimizer_config: Mapping[str, Any],
    evaluator: BlackBoxSystemEvaluator,
    loss_spec: Mapping[str, Any],
    scenarios: Sequence[str],
    seed: int,
    black_box_budget: int,
) -> dict[str, Any]:
    """Use a gradient proposal as the center of a result-dependent local search."""

    mutable = mutable_raw_ids(space, freedom)
    inner = optimize_relaxed(
        space,
        surrogate,
        optimizer_config,
        mutable_raw_ids=mutable,
    )
    black_box = run_black_box_episode(
        space=space,
        freedom=freedom,
        evaluator=evaluator,
        loss_spec=loss_spec,
        scenarios=scenarios,
        seed=seed,
        budget=black_box_budget,
        center_raw=inner["optimized_raw"],
        method=SearchMethod.HYBRID,
    )
    return {
        "schema": CONTINUUM_REPORT_SCHEMA,
        "coordinate": OptimizationCoordinate(freedom, SearchMethod.HYBRID).to_dict(),
        "design_id": space.spec["id"],
        "gradient_initializer": {
            "initial_surrogate_loss": inner["trace"][0]["surrogate_mean"],
            "final_surrogate_loss": inner["trace"][-1]["surrogate_mean"],
            "optimized_raw": inner["optimized_raw"],
        },
        "black_box": black_box,
    }


def continuum_capability_map(space: DifferentiableSystemSpace) -> dict[str, Any]:
    """Machine-readable map for documentation and a future game view."""

    rows = []
    for freedom in (
        DesignFreedom.PARAMETERS,
        DesignFreedom.MECHANISM_CONFIGURATION,
        DesignFreedom.GRAPH_STRUCTURE,
    ):
        rows.append(
            {
                "freedom": freedom.value,
                "mutable_raw_ids": list(mutable_raw_ids(space, freedom)),
                "search_methods": [item.value for item in SearchMethod],
                "projects_to_system_spec": True,
                "common_outer_evaluator": True,
            }
        )
    rows.append(
        {
            "freedom": DesignFreedom.OPEN_ENDED_SYSTEM.value,
            "mutable_raw_ids": [],
            "search_methods": [],
            "projects_to_system_spec": False,
            "common_outer_evaluator": False,
            "status": "declared-frontier-not-implemented",
        }
    )
    return {
        "schema": "scienceutopia.optimization-capability-map.v1",
        "design_id": space.spec["id"],
        "axes": {
            "design_freedom": "what the optimizer may change",
            "search_method": "how proposals are generated",
        },
        "rows": rows,
        "known_gap": "schedule and open-ended program synthesis are not relaxed in v1",
    }

