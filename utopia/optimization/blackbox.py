"""Optimizer-neutral ask/tell boundary for opaque science-system designs.

The optimizer sees candidate JSON and scalar losses. It does not inspect the
simulator, require gradients, or assign scientific meaning to evaluation
metrics. A candidate can be today's flat parameter vector or a future nested
whole-system ``SystemSpec`` as long as its search-space adapter implements the
protocol below.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import random
from typing import Any, Callable, Mapping, Protocol, Sequence

from utopia.optimization.design_space import validate_candidate
from utopia.system import (
    SystemSpec,
    compile_legacy_system,
    legacy_candidate_to_system_spec,
    validate_system_spec,
)


JsonObject = dict[str, Any]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _copy_json_object(value: Mapping[str, Any]) -> JsonObject:
    copied = json.loads(canonical_json(value))
    if not isinstance(copied, dict):
        raise ValueError("candidate must be a JSON object")
    return copied


class SearchSpace(Protocol):
    """Adapter between an optimizer and one encoding of a science system."""

    def validate(self, candidate: Mapping[str, Any]) -> None:
        """Raise ``ValueError`` when a candidate is outside this space."""

    def sample(self, *, seed: int, proposal_index: int) -> Mapping[str, Any]:
        """Return a deterministic initial candidate."""

    def mutate(
        self,
        incumbent: Mapping[str, Any],
        *,
        seed: int,
        proposal_index: int,
        scale: float,
    ) -> Mapping[str, Any]:
        """Return a deterministic gradient-free neighbor of ``incumbent``."""


@dataclass(frozen=True)
class Suggestion:
    suggestion_id: str
    candidate: JsonObject
    proposal_index: int
    phase: str
    based_on_observation_id: str | None = None

    def to_dict(self) -> JsonObject:
        return {
            "suggestion_id": self.suggestion_id,
            "candidate": _copy_json_object(self.candidate),
            "proposal_index": self.proposal_index,
            "phase": self.phase,
            "based_on_observation_id": self.based_on_observation_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Suggestion":
        return cls(
            suggestion_id=str(value["suggestion_id"]),
            candidate=_copy_json_object(value["candidate"]),
            proposal_index=int(value["proposal_index"]),
            phase=str(value["phase"]),
            based_on_observation_id=value.get("based_on_observation_id"),
        )


@dataclass(frozen=True)
class Observation:
    """One accepted or rejected simulator observation.

    ``complete`` means the versioned ``LossSpec`` produced a finite scalar loss.
    ``invalid`` and ``failed`` are technical states and never become artificial
    penalty values inside this generic optimizer boundary.
    """

    observation_id: str
    suggestion_id: str
    candidate: JsonObject
    status: str
    loss: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"complete", "invalid", "failed"}:
            raise ValueError(f"unsupported observation status {self.status!r}")
        if self.status == "complete":
            if (
                isinstance(self.loss, bool)
                or not isinstance(self.loss, (int, float))
                or not math.isfinite(self.loss)
            ):
                raise ValueError("complete observation requires a finite scalar loss")
        elif self.loss is not None:
            raise ValueError("invalid or failed observations must not carry a loss")
        _copy_json_object(self.candidate)
        _copy_json_object(self.metadata)

    def to_dict(self) -> JsonObject:
        return {
            "observation_id": self.observation_id,
            "suggestion_id": self.suggestion_id,
            "candidate": _copy_json_object(self.candidate),
            "status": self.status,
            "loss": self.loss,
            "metadata": _copy_json_object(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Observation":
        return cls(
            observation_id=str(value["observation_id"]),
            suggestion_id=str(value["suggestion_id"]),
            candidate=_copy_json_object(value["candidate"]),
            status=str(value["status"]),
            loss=value.get("loss"),
            metadata=_copy_json_object(value.get("metadata", {})),
        )


class AskTellOptimizer(Protocol):
    """Common black-box API for random, Bayesian, evolutionary, or other search."""

    def ask(self, count: int = 1) -> list[Suggestion]:
        ...

    def tell(self, observations: Sequence[Observation]) -> None:
        ...

    def state_dict(self) -> JsonObject:
        ...


class LegacyParameterSpace:
    """Search-space adapter for the current fixed-topology parameter vector."""

    def __init__(self, space: Mapping[str, Any]):
        self.space = _copy_json_object(space)
        variables = self.space.get("variables")
        if not isinstance(variables, dict) or not variables:
            raise ValueError("space.variables must be a non-empty object")

    @staticmethod
    def _rng(seed: int, proposal_index: int, purpose: str) -> random.Random:
        material = f"{seed}:{proposal_index}:{purpose}".encode()
        derived = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
        return random.Random(derived)

    def validate(self, candidate: Mapping[str, Any]) -> None:
        validate_candidate(self.space, candidate)

    def sample(self, *, seed: int, proposal_index: int) -> Mapping[str, Any]:
        rng = self._rng(seed, proposal_index, "sample")
        candidate: JsonObject = {}
        for name, rule in self.space["variables"].items():
            if rule["type"] == "float":
                candidate[name] = round(
                    rng.uniform(rule["minimum"], rule["maximum"]), 8
                )
            elif rule["type"] == "integer":
                candidate[name] = rng.randint(rule["minimum"], rule["maximum"])
            elif rule["type"] == "categorical":
                candidate[name] = rng.choice(rule["choices"])
            else:
                raise ValueError(f"unsupported variable type {rule['type']!r}")
        self.validate(candidate)
        return candidate

    def mutate(
        self,
        incumbent: Mapping[str, Any],
        *,
        seed: int,
        proposal_index: int,
        scale: float,
    ) -> Mapping[str, Any]:
        self.validate(incumbent)
        rng = self._rng(seed, proposal_index, "mutate")
        candidate = _copy_json_object(incumbent)
        for name, rule in self.space["variables"].items():
            if rule["type"] == "float":
                width = rule["maximum"] - rule["minimum"]
                value = rng.gauss(float(incumbent[name]), max(scale * width, 1e-12))
                candidate[name] = round(
                    min(max(value, rule["minimum"]), rule["maximum"]), 8
                )
            elif rule["type"] == "integer":
                width = rule["maximum"] - rule["minimum"]
                value = round(rng.gauss(int(incumbent[name]), max(scale * width, 0.5)))
                candidate[name] = min(max(value, rule["minimum"]), rule["maximum"])
            elif rule["type"] == "categorical":
                choices = list(rule["choices"])
                if len(choices) > 1 and rng.random() < max(0.1, scale):
                    choices.remove(incumbent[name])
                    candidate[name] = rng.choice(choices)
        self.validate(candidate)
        return candidate


class LegacySystemSpecSpace:
    """Whole-system encoding of the current fixed-topology search space.

    This is the adapter intended for the first real closed-loop campaign. It
    proposes nested ``SystemSpec`` JSON while using the existing eight
    parameters as its currently mutable subspace.
    """

    def __init__(self, space: Mapping[str, Any]):
        self.parameters = LegacyParameterSpace(space)
        self.space = self.parameters.space

    def _parse(self, candidate: Mapping[str, Any]) -> tuple[SystemSpec, JsonObject]:
        try:
            spec = SystemSpec.from_dict(candidate)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid SystemSpec encoding: {error}") from error
        validate_system_spec(spec).require_valid()
        compile_legacy_system(spec, years=1)
        source = spec.metadata.get("source_candidate")
        if not isinstance(source, dict):
            raise ValueError("legacy SystemSpec metadata.source_candidate is required")
        self.parameters.validate(source)
        rebuilt = legacy_candidate_to_system_spec(self.space, source)
        if rebuilt.fingerprint != spec.fingerprint:
            raise ValueError("legacy SystemSpec does not match its source candidate")
        return spec, _copy_json_object(source)

    def validate(self, candidate: Mapping[str, Any]) -> None:
        self._parse(candidate)

    def sample(self, *, seed: int, proposal_index: int) -> Mapping[str, Any]:
        parameters = self.parameters.sample(seed=seed, proposal_index=proposal_index)
        return legacy_candidate_to_system_spec(self.space, parameters).to_dict()

    def mutate(
        self,
        incumbent: Mapping[str, Any],
        *,
        seed: int,
        proposal_index: int,
        scale: float,
    ) -> Mapping[str, Any]:
        _, source = self._parse(incumbent)
        parameters = self.parameters.mutate(
            source,
            seed=seed,
            proposal_index=proposal_index,
            scale=scale,
        )
        return legacy_candidate_to_system_spec(self.space, parameters).to_dict()

class AdaptiveRandomSearch:
    """Small deterministic black-box baseline with a serializable ask/tell state.

    Initial proposals are independent samples. Later proposals perturb the
    lowest-loss completed candidate, making the closed loop observably dependent
    on simulator results without assuming differentiability.
    """

    SCHEMA = "scienceutopia.blackbox-optimizer-state.v1"

    def __init__(
        self,
        space: SearchSpace,
        *,
        seed: int,
        initial_random: int = 4,
        mutation_scale: float = 0.2,
    ):
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        if isinstance(initial_random, bool) or not isinstance(initial_random, int):
            raise ValueError("initial_random must be an integer")
        if initial_random < 1:
            raise ValueError("initial_random must be positive")
        if not 0 < mutation_scale <= 1:
            raise ValueError("mutation_scale must be in (0, 1]")
        self.space = space
        self.seed = seed
        self.initial_random = initial_random
        self.mutation_scale = float(mutation_scale)
        self._proposal_index = 0
        self._pending: dict[str, Suggestion] = {}
        self._observations: list[Observation] = []
        self._seen_candidates: set[str] = set()

    def _complete_observations(self) -> list[Observation]:
        return [item for item in self._observations if item.status == "complete"]

    def _incumbent(self) -> Observation | None:
        complete = self._complete_observations()
        if not complete:
            return None
        return min(complete, key=lambda item: (float(item.loss), item.observation_id))

    def ask(self, count: int = 1) -> list[Suggestion]:
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("ask count must be a positive integer")
        suggestions: list[Suggestion] = []
        attempts = 0
        while len(suggestions) < count:
            attempts += 1
            if attempts > count * 1000:
                raise RuntimeError("could not produce enough unique candidates")
            proposal_index = self._proposal_index
            self._proposal_index += 1
            incumbent = self._incumbent()
            if proposal_index < self.initial_random or incumbent is None:
                phase = "initial"
                candidate = self.space.sample(
                    seed=self.seed, proposal_index=proposal_index
                )
                based_on = None
            else:
                phase = "adaptive"
                adaptive_count = max(0, proposal_index - self.initial_random)
                scale = max(
                    0.02,
                    self.mutation_scale / math.sqrt(1 + adaptive_count),
                )
                candidate = self.space.mutate(
                    incumbent.candidate,
                    seed=self.seed,
                    proposal_index=proposal_index,
                    scale=scale,
                )
                based_on = incumbent.observation_id
            self.space.validate(candidate)
            copied = _copy_json_object(candidate)
            identity = canonical_json(copied)
            if identity in self._seen_candidates:
                continue
            suggestion_id = "s" + hashlib.sha256(
                canonical_json({
                    "seed": self.seed,
                    "proposal_index": proposal_index,
                    "candidate": copied,
                }).encode()
            ).hexdigest()[:16]
            suggestion = Suggestion(
                suggestion_id=suggestion_id,
                candidate=copied,
                proposal_index=proposal_index,
                phase=phase,
                based_on_observation_id=based_on,
            )
            self._pending[suggestion_id] = suggestion
            self._seen_candidates.add(identity)
            suggestions.append(suggestion)
        return suggestions

    def tell(self, observations: Sequence[Observation]) -> None:
        observation_ids = {item.observation_id for item in self._observations}
        batch_ids: set[str] = set()
        batch_suggestion_ids: set[str] = set()
        for observation in observations:
            if observation.observation_id in observation_ids or observation.observation_id in batch_ids:
                raise ValueError(f"duplicate observation id {observation.observation_id!r}")
            if observation.suggestion_id in batch_suggestion_ids:
                raise ValueError(
                    f"duplicate suggestion id {observation.suggestion_id!r} in tell batch"
                )
            suggestion = self._pending.get(observation.suggestion_id)
            if suggestion is None:
                raise ValueError(
                    f"observation references unknown or resolved suggestion "
                    f"{observation.suggestion_id!r}"
                )
            if canonical_json(suggestion.candidate) != canonical_json(observation.candidate):
                raise ValueError("observation candidate does not match its suggestion")
            batch_ids.add(observation.observation_id)
            batch_suggestion_ids.add(observation.suggestion_id)
        for observation in observations:
            self._observations.append(observation)
            del self._pending[observation.suggestion_id]

    def state_dict(self) -> JsonObject:
        return {
            "schema": self.SCHEMA,
            "optimizer": "adaptive_random_search",
            "config": {
                "seed": self.seed,
                "initial_random": self.initial_random,
                "mutation_scale": self.mutation_scale,
            },
            "proposal_index": self._proposal_index,
            "pending": [
                item.to_dict()
                for item in sorted(
                    self._pending.values(), key=lambda value: value.proposal_index
                )
            ],
            "observations": [item.to_dict() for item in self._observations],
            "seen_candidates": sorted(self._seen_candidates),
        }

    @classmethod
    def from_state(
        cls, space: SearchSpace, state: Mapping[str, Any]
    ) -> "AdaptiveRandomSearch":
        if state.get("schema") != cls.SCHEMA:
            raise ValueError("unsupported optimizer state schema")
        if state.get("optimizer") != "adaptive_random_search":
            raise ValueError("optimizer state has the wrong implementation")
        config = state["config"]
        optimizer = cls(
            space,
            seed=config["seed"],
            initial_random=config["initial_random"],
            mutation_scale=config["mutation_scale"],
        )
        optimizer._proposal_index = int(state["proposal_index"])
        optimizer._pending = {
            item.suggestion_id: item
            for item in (Suggestion.from_dict(value) for value in state.get("pending", []))
        }
        optimizer._observations = [
            Observation.from_dict(value) for value in state.get("observations", [])
        ]
        optimizer._seen_candidates = set(state.get("seen_candidates", []))
        for suggestion in optimizer._pending.values():
            space.validate(suggestion.candidate)
        for observation in optimizer._observations:
            space.validate(observation.candidate)
        return optimizer


def evaluate_round(
    optimizer: AskTellOptimizer,
    evaluator: Callable[[Suggestion], Observation],
    *,
    count: int,
) -> tuple[list[Suggestion], list[Observation]]:
    """Run one synchronous ask/evaluate/tell round.

    Production simulation will persist suggestions before dispatching jobs. This
    helper exists for deterministic tests and cheap surrogate/smoke loops.
    """

    suggestions = optimizer.ask(count)
    observations = [evaluator(item) for item in suggestions]
    optimizer.tell(observations)
    return suggestions, observations
