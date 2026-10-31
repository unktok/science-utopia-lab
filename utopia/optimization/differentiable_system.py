"""Prospective differentiable surrogate design for whole-system graphs.

Discrete mechanism presence, implementation choices, and edges are relaxed to
sigmoid/softmax features. Continuous parameters use normalized coordinates.
Gradient descent occurs only on a surrogate; every proposed design is projected
back to a valid ``SystemSpec`` and evaluated through a separate black-box
boundary. The included model is synthetic and analytic by construction.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from jsonschema import Draft202012Validator

from utopia.optimization.loss import loss_spec_sha256, validate_loss_spec
from utopia.optimization.objective_compiler import canonical_sha256
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


DESIGN_SCHEMA = "scienceutopia.differentiable-system-design.v0"
REPORT_SCHEMA = "scienceutopia.differentiable-system-design-report.v0"


def load_differentiable_design(
    path: str | Path, schema_path: str | Path
) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validate_differentiable_design(value, schema)
    return value


def validate_differentiable_design(
    spec: Mapping[str, Any], schema: Mapping[str, Any]
) -> None:
    errors = [
        f"schema: {error.message}"
        for error in Draft202012Validator(schema).iter_errors(spec)
    ]
    if errors:
        raise ValueError("Invalid differentiable design: " + "; ".join(sorted(errors)))
    if spec["schema"] != DESIGN_SCHEMA:
        errors.append(f"schema must be {DESIGN_SCHEMA!r}")
    if spec["active_campaign_effect"] != "none":
        errors.append("active_campaign_effect must be none")

    template = spec["system_template"]
    mechanisms = _unique(template["mechanisms"], "slot_id", "mechanism slot", errors)
    mechanism_ids = _unique(template["mechanisms"], "mechanism_id", "mechanism", errors)
    _unique(template["edges"], "edge_id", "edge", errors)
    families = {item["family"] for item in template["mechanisms"]}
    if len(families) < 4 or not {"research", "funding", "publication", "governance"} <= families:
        errors.append(
            "system template must span research, funding, publication, governance, "
            "and at least four families"
        )

    ports: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for mechanism in template["mechanisms"]:
        _unique(
            mechanism["implementations"],
            "option_id",
            f"implementation in {mechanism['slot_id']}",
            errors,
        )
        _unique(
            mechanism["parameters"],
            "parameter_id",
            f"parameter in {mechanism['slot_id']}",
            errors,
        )
        if (
            mechanism["presence"]["mode"] == "fixed-present"
            and "initial_logit" in mechanism["presence"]
        ):
            errors.append(
                f"fixed mechanism {mechanism['slot_id']!r} must not declare a "
                "presence logit"
            )
        for direction in ("inputs", "outputs"):
            _unique(
                mechanism[direction],
                "port_id",
                f"{direction} port in {mechanism['slot_id']}",
                errors,
            )
            for port in mechanism[direction]:
                ports[(mechanism["mechanism_id"], direction, port["port_id"])] = port
        for parameter in mechanism["parameters"]:
            if parameter["maximum"] <= parameter["minimum"]:
                errors.append(
                    f"parameter {mechanism['slot_id']}.{parameter['parameter_id']} "
                    "has non-positive range"
                )

    for edge in template["edges"]:
        source = ports.get((edge["source_mechanism"], "outputs", edge["source_port"]))
        target = ports.get((edge["target_mechanism"], "inputs", edge["target_port"]))
        if edge["source_mechanism"] not in mechanism_ids or source is None:
            errors.append(f"edge {edge['edge_id']!r} has an unresolved source")
        if edge["target_mechanism"] not in mechanism_ids or target is None:
            errors.append(f"edge {edge['edge_id']!r} has an unresolved target")
        if source and source["channel"] != edge["channel"]:
            errors.append(f"edge {edge['edge_id']!r} source channel mismatch")
        if target and target["channel"] != edge["channel"]:
            errors.append(f"edge {edge['edge_id']!r} target channel mismatch")

    space = DifferentiableSystemSpace(spec)
    feature_ids = set(space.feature_ids)
    surrogate = spec["surrogate"]
    for field in ("targets", "weights"):
        declared = set(surrogate[field])
        if declared != feature_ids:
            errors.append(f"surrogate {field} must cover exactly all relaxed features")
    if set(surrogate["uncertainty"]["anchor"]) != feature_ids:
        errors.append("surrogate uncertainty anchor must cover exactly all relaxed features")
    for interaction in surrogate["interactions"]:
        if interaction["left"] not in feature_ids or interaction["right"] not in feature_ids:
            errors.append("surrogate interaction has an unresolved feature")
    if surrogate["conditioned_loss_sha256"] != spec["objective_binding"]["loss_spec"]["sha256"]:
        errors.append("surrogate is conditioned on a different LossSpec")
    required_reports = {
        "gradient-trace",
        "projection-decisions",
        "surrogate-gap",
        "uncertainty",
        "projection-instability",
        "outer-validation",
        "objective-provenance",
    }
    missing_reports = required_reports - set(spec["audit"]["required_reports"])
    if missing_reports:
        errors.append(f"audit is missing reports {sorted(missing_reports)!r}")
    generated_flags = {
        "surrogate-gap-exceeds-bound",
        "surrogate-uncertainty-exceeds-bound",
        "projection-boundary-sensitive",
        "surrogate-improvement-blackbox-regression",
        "relaxation-projection-gap",
    }
    missing_flags = generated_flags - set(spec["audit"]["goodhart_flags"])
    if missing_flags:
        errors.append(f"audit is missing generated Goodhart flags {sorted(missing_flags)!r}")
    if errors:
        raise ValueError("Invalid differentiable design: " + "; ".join(sorted(errors)))


def _unique(
    items: Sequence[Mapping[str, Any]], key: str, label: str, errors: list[str]
) -> set[str]:
    seen: set[str] = set()
    for item in items:
        value = item[key]
        if value in seen:
            errors.append(f"duplicate {label} {value!r}")
        seen.add(value)
    return seen


def _sigmoid(value: float, temperature: float) -> float:
    scaled = max(min(value / temperature, 60.0), -60.0)
    return 1.0 / (1.0 + math.exp(-scaled))


def _softmax(values: Sequence[float], temperature: float) -> list[float]:
    scaled = [value / temperature for value in values]
    maximum = max(scaled)
    exps = [math.exp(value - maximum) for value in scaled]
    total = sum(exps)
    return [value / total for value in exps]


@dataclass(frozen=True)
class SurrogatePrediction:
    mean: float
    uncertainty: float
    feature_gradient: Mapping[str, float]


class DifferentiableSurrogate(Protocol):
    def predict_and_gradient(
        self, features: Mapping[str, float]
    ) -> SurrogatePrediction:
        ...


class BlackBoxSystemEvaluator(Protocol):
    def evaluate(
        self, system: SystemSpec, loss_spec: Mapping[str, Any], scenarios: Sequence[str]
    ) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class ProjectionResult:
    system_spec: SystemSpec
    features: Mapping[str, float]
    decisions: tuple[Mapping[str, Any], ...]


class DifferentiableSystemSpace:
    """Relax and project a mixed whole-system graph design space."""

    def __init__(self, spec: Mapping[str, Any]) -> None:
        self.spec = spec
        self._mechanisms = list(spec["system_template"]["mechanisms"])
        self._edges = list(spec["system_template"]["edges"])
        self._binary_temperature = float(spec["relaxation"]["binary"]["temperature"])
        self._categorical_temperature = float(spec["relaxation"]["categorical"]["temperature"])
        self._threshold = float(spec["relaxation"]["projection"]["binary_threshold"])
        self._raw_kinds: dict[str, str] = {}
        self._feature_ids: list[str] = []
        self._categorical_groups: dict[str, list[tuple[str, str]]] = {}
        self._build_layout()

    def _build_layout(self) -> None:
        for mechanism in self._mechanisms:
            slot = mechanism["slot_id"]
            if mechanism["presence"]["mode"] == "relaxed-binary":
                raw = f"presence-logit:{slot}"
                feature = f"presence:{slot}"
                self._raw_kinds[raw] = "logit"
                self._feature_ids.append(feature)
            else:
                self._feature_ids.append(f"presence:{slot}")
            group = []
            for option in mechanism["implementations"]:
                feature = f"implementation:{slot}:{option['option_id']}"
                self._feature_ids.append(feature)
                if len(mechanism["implementations"]) > 1:
                    raw = f"implementation-logit:{slot}:{option['option_id']}"
                    self._raw_kinds[raw] = "logit"
                    group.append((raw, feature))
            if group:
                self._categorical_groups[slot] = group
            for parameter in mechanism["parameters"]:
                raw = f"parameter:{slot}:{parameter['parameter_id']}"
                self._raw_kinds[raw] = "continuous"
                self._feature_ids.append(raw)
        for edge in self._edges:
            feature = f"edge:{edge['edge_id']}"
            self._feature_ids.append(feature)
            if edge["presence"]["mode"] == "relaxed-binary":
                self._raw_kinds[f"edge-logit:{edge['edge_id']}"] = "logit"

    @property
    def feature_ids(self) -> tuple[str, ...]:
        return tuple(self._feature_ids)

    @property
    def raw_ids(self) -> tuple[str, ...]:
        return tuple(self._raw_kinds)

    def initial_raw(self) -> dict[str, float]:
        raw: dict[str, float] = {}
        for mechanism in self._mechanisms:
            slot = mechanism["slot_id"]
            if mechanism["presence"]["mode"] == "relaxed-binary":
                raw[f"presence-logit:{slot}"] = float(mechanism["presence"]["initial_logit"])
            if len(mechanism["implementations"]) > 1:
                for option in mechanism["implementations"]:
                    raw[
                        f"implementation-logit:{slot}:{option['option_id']}"
                    ] = float(option["initial_logit"])
            for parameter in mechanism["parameters"]:
                raw[f"parameter:{slot}:{parameter['parameter_id']}"] = float(
                    parameter["initial_normalized"]
                )
        for edge in self._edges:
            if edge["presence"]["mode"] == "relaxed-binary":
                raw[f"edge-logit:{edge['edge_id']}"] = float(edge["presence"]["initial_logit"])
        return raw

    def features(self, raw: Mapping[str, float]) -> dict[str, float]:
        self._validate_raw(raw)
        features: dict[str, float] = {}
        for mechanism in self._mechanisms:
            slot = mechanism["slot_id"]
            if mechanism["presence"]["mode"] == "relaxed-binary":
                features[f"presence:{slot}"] = _sigmoid(
                    raw[f"presence-logit:{slot}"], self._binary_temperature
                )
            else:
                features[f"presence:{slot}"] = 1.0
            options = mechanism["implementations"]
            if len(options) == 1:
                features[f"implementation:{slot}:{options[0]['option_id']}"] = 1.0
            else:
                group = self._categorical_groups[slot]
                probabilities = _softmax(
                    [raw[raw_id] for raw_id, _ in group],
                    self._categorical_temperature,
                )
                for (_, feature_id), probability in zip(group, probabilities, strict=True):
                    features[feature_id] = probability
            for parameter in mechanism["parameters"]:
                raw_id = f"parameter:{slot}:{parameter['parameter_id']}"
                features[raw_id] = min(max(float(raw[raw_id]), 0.0), 1.0)
        for edge in self._edges:
            feature = f"edge:{edge['edge_id']}"
            if edge["presence"]["mode"] == "relaxed-binary":
                features[feature] = _sigmoid(
                    raw[f"edge-logit:{edge['edge_id']}"], self._binary_temperature
                )
            else:
                features[feature] = 1.0
        return features

    def pullback(
        self, raw: Mapping[str, float], feature_gradient: Mapping[str, float]
    ) -> dict[str, float]:
        features = self.features(raw)
        missing = set(self.feature_ids) - set(feature_gradient)
        if missing:
            raise ValueError(f"surrogate gradient is missing features {sorted(missing)!r}")
        gradient: dict[str, float] = {}
        for raw_id, kind in self._raw_kinds.items():
            if kind == "continuous":
                gradient[raw_id] = float(feature_gradient[raw_id])
            elif raw_id.startswith("presence-logit:"):
                slot = raw_id.split(":", 1)[1]
                feature_id = f"presence:{slot}"
                probability = features[feature_id]
                gradient[raw_id] = (
                    float(feature_gradient[feature_id])
                    * probability
                    * (1.0 - probability)
                    / self._binary_temperature
                )
            elif raw_id.startswith("edge-logit:"):
                edge_id = raw_id.split(":", 1)[1]
                feature_id = f"edge:{edge_id}"
                probability = features[feature_id]
                gradient[raw_id] = (
                    float(feature_gradient[feature_id])
                    * probability
                    * (1.0 - probability)
                    / self._binary_temperature
                )
        for group in self._categorical_groups.values():
            weighted = sum(
                features[feature_id] * float(feature_gradient[feature_id])
                for _, feature_id in group
            )
            for raw_id, feature_id in group:
                probability = features[feature_id]
                gradient[raw_id] = (
                    probability
                    * (float(feature_gradient[feature_id]) - weighted)
                    / self._categorical_temperature
                )
        return gradient

    def project(self, raw: Mapping[str, float]) -> ProjectionResult:
        features = self.features(raw)
        template = self.spec["system_template"]
        mechanisms = []
        schedules = []
        decisions: list[Mapping[str, Any]] = []
        active: set[str] = set()
        for mechanism in self._mechanisms:
            slot = mechanism["slot_id"]
            probability = features[f"presence:{slot}"]
            present = (
                mechanism["presence"]["mode"] == "fixed-present"
                or probability >= self._threshold
            )
            if not present:
                decisions.append(
                    {
                        "kind": "mechanism-presence",
                        "id": slot,
                        "probability": probability,
                        "selected": False,
                    }
                )
                continue
            active.add(mechanism["mechanism_id"])
            option = max(
                mechanism["implementations"],
                key=lambda item: features[f"implementation:{slot}:{item['option_id']}"],
            )
            parameters = {}
            for parameter in mechanism["parameters"]:
                normalized = features[f"parameter:{slot}:{parameter['parameter_id']}"]
                value = parameter["minimum"] + normalized * (
                    parameter["maximum"] - parameter["minimum"]
                )
                parameters[parameter["parameter_id"]] = round(value, parameter["round_digits"])
            mechanisms.append(
                MechanismSpec(
                    mechanism_id=mechanism["mechanism_id"],
                    family=MechanismFamily(mechanism["family"]),
                    implementation=option["implementation"],
                    inputs=tuple(_port(item) for item in mechanism["inputs"]),
                    outputs=tuple(_port(item) for item in mechanism["outputs"]),
                    parameters=parameters,
                )
            )
            schedules.append(
                ScheduleSpec(
                    mechanism_id=mechanism["mechanism_id"], **mechanism["schedule"]
                )
            )
            decisions.append({
                "kind": "mechanism-projection",
                "id": slot,
                "probability": probability,
                "selected": True,
                "implementation": option["option_id"],
                "parameters": parameters,
            })
        connections = []
        for edge in self._edges:
            probability = features[f"edge:{edge['edge_id']}"]
            threshold_selected = (
                edge["presence"]["mode"] == "fixed-present"
                or probability >= self._threshold
            )
            endpoints_present = (
                edge["source_mechanism"] in active
                and edge["target_mechanism"] in active
            )
            selected = threshold_selected and endpoints_present
            reason = (
                "selected"
                if selected
                else (
                    "dangling-endpoint-force-absent"
                    if threshold_selected
                    else "below-threshold"
                )
            )
            if selected:
                connections.append(
                    ConnectionSpec(
                        source_mechanism=edge["source_mechanism"],
                        source_port=edge["source_port"],
                        target_mechanism=edge["target_mechanism"],
                        target_port=edge["target_port"],
                        channel=ChannelKind(edge["channel"]),
                        latency=edge["latency"],
                    )
                )
            decisions.append(
                {
                    "kind": "edge-projection",
                    "id": edge["edge_id"],
                    "probability": probability,
                    "selected": selected,
                    "reason": reason,
                }
            )
        system = SystemSpec(
            system_id=template["system_id"],
            version=template["version"],
            agent_types=tuple(AgentTypeSpec(**item) for item in template["agent_types"]),
            artifact_types=tuple(ArtifactTypeSpec(**item) for item in template["artifact_types"]),
            mechanisms=tuple(mechanisms),
            connections=tuple(connections),
            schedules=tuple(schedules),
            global_invariants=tuple(template["global_invariants"]),
            metadata={
                "differentiable_projection": {
                    "schema": DESIGN_SCHEMA,
                    "design_id": self.spec["id"],
                }
            },
        )
        validate_system_spec(system).require_valid()
        return ProjectionResult(system, self.encode_projected(system), tuple(decisions))

    def encode_projected(self, system: SystemSpec) -> dict[str, float]:
        mechanisms = {item.mechanism_id: item for item in system.mechanisms}
        features: dict[str, float] = {}
        for template in self._mechanisms:
            slot = template["slot_id"]
            mechanism = mechanisms.get(template["mechanism_id"])
            features[f"presence:{slot}"] = 1.0 if mechanism else 0.0
            for option in template["implementations"]:
                features[f"implementation:{slot}:{option['option_id']}"] = (
                    1.0
                    if mechanism
                    and mechanism.implementation == option["implementation"]
                    else 0.0
                )
            for parameter in template["parameters"]:
                raw_id = f"parameter:{slot}:{parameter['parameter_id']}"
                if mechanism:
                    value = float(mechanism.parameters[parameter["parameter_id"]])
                    features[raw_id] = (value - parameter["minimum"]) / (
                        parameter["maximum"] - parameter["minimum"]
                    )
                else:
                    features[raw_id] = 0.0
        connection_keys = {
            (item.source_mechanism, item.source_port, item.target_mechanism, item.target_port)
            for item in system.connections
        }
        for edge in self._edges:
            key = (
                edge["source_mechanism"],
                edge["source_port"],
                edge["target_mechanism"],
                edge["target_port"],
            )
            features[f"edge:{edge['edge_id']}"] = 1.0 if key in connection_keys else 0.0
        return features

    def _validate_raw(self, raw: Mapping[str, float]) -> None:
        if set(raw) != set(self.raw_ids):
            raise ValueError("raw relaxation vector does not match design layout")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in raw.values()
        ):
            raise ValueError("raw relaxation vector must contain finite numbers")


def _port(item: Mapping[str, Any]) -> PortSpec:
    return PortSpec(
        port_id=item["port_id"],
        channel=ChannelKind(item["channel"]),
        artifact_type=item.get("artifact_type"),
        required=item["required"],
    )


class QuadraticAnalyticSurrogate:
    """Synthetic differentiable loss surface with analytic feature gradients."""

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = config

    def predict_and_gradient(self, features: Mapping[str, float]) -> SurrogatePrediction:
        mean = float(self.config["bias"])
        gradient = {key: 0.0 for key in features}
        for key, value in features.items():
            difference = float(value) - float(self.config["targets"][key])
            weight = float(self.config["weights"][key])
            mean += weight * difference * difference
            gradient[key] += 2.0 * weight * difference
        for interaction in self.config["interactions"]:
            left = interaction["left"]
            right = interaction["right"]
            coefficient = float(interaction["coefficient"])
            mean += coefficient * float(features[left]) * float(features[right])
            gradient[left] += coefficient * float(features[right])
            gradient[right] += coefficient * float(features[left])
        uncertainty_config = self.config["uncertainty"]
        squared_distance = sum(
            (float(features[key]) - float(uncertainty_config["anchor"][key])) ** 2
            for key in features
        )
        uncertainty = float(uncertainty_config["base"]) + float(
            uncertainty_config["distance_scale"]
        ) * math.sqrt(squared_distance)
        return SurrogatePrediction(mean, uncertainty, gradient)


def optimize_relaxed(
    space: DifferentiableSystemSpace,
    surrogate: DifferentiableSurrogate,
    config: Mapping[str, Any],
    *,
    mutable_raw_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Optimize a relaxed system, optionally freezing part of the design.

    ``mutable_raw_ids`` turns the same whole-system relaxation into nested
    design spaces.  For example, a caller can expose only continuous
    parameters, then implementation choices, then node/edge topology without
    changing the surrogate, projection rule, or outer evaluator.
    """

    raw = space.initial_raw()
    mutable = set(space.raw_ids if mutable_raw_ids is None else mutable_raw_ids)
    unknown = mutable - set(space.raw_ids)
    if unknown:
        raise ValueError(f"mutable_raw_ids contains unknown ids {sorted(unknown)!r}")
    if not mutable:
        raise ValueError("mutable_raw_ids must expose at least one design variable")
    trace = []
    for step in range(int(config["iterations"]) + 1):
        features = space.features(raw)
        prediction = surrogate.predict_and_gradient(features)
        raw_gradient = space.pullback(raw, prediction.feature_gradient)
        raw_gradient = {
            key: value if key in mutable else 0.0
            for key, value in raw_gradient.items()
        }
        norm = math.sqrt(sum(value * value for value in raw_gradient.values()))
        trace.append({
            "step": step,
            "surrogate_mean": prediction.mean,
            "surrogate_uncertainty": prediction.uncertainty,
            "raw_gradient_norm": norm,
            "raw": dict(raw),
            "features": features,
        })
        if step == int(config["iterations"]):
            break
        clip = float(config["gradient_clip"])
        scale = min(1.0, clip / norm) if norm > 0 else 1.0
        learning_rate = float(config["learning_rate"])
        for key, gradient in raw_gradient.items():
            if key not in mutable:
                continue
            raw[key] -= learning_rate * scale * gradient
            if key.startswith("parameter:"):
                raw[key] = min(max(raw[key], 0.0), 1.0)
            else:
                bound = float(config["logit_clip"])
                raw[key] = min(max(raw[key], -bound), bound)
    return {"initial_raw": trace[0]["raw"], "optimized_raw": dict(raw), "trace": trace}


class SyntheticBlackBoxEvaluator:
    """Nondifferentiable projected-system evaluator used only by tests."""

    def __init__(self, space: DifferentiableSystemSpace, conditioned_loss_sha256: str) -> None:
        self.space = space
        self.conditioned_loss_sha256 = conditioned_loss_sha256

    def evaluate(
        self, system: SystemSpec, loss_spec: Mapping[str, Any], scenarios: Sequence[str]
    ) -> Mapping[str, Any]:
        validate_loss_spec(loss_spec)
        if loss_spec_sha256(loss_spec) != self.conditioned_loss_sha256:
            raise ValueError("black-box evaluator received a different LossSpec")
        features = self.space.encode_projected(system)
        base = (
            0.7 * (features["parameter:research:exploration-rate"] - 0.72) ** 2
            + 0.5 * (features["parameter:funding:allocation-share"] - 0.64) ** 2
            + 0.4 * (features["parameter:governance:mission-concentration"] - 0.35) ** 2
            + 0.25 * (1.0 - features["presence:evaluation"])
            + 0.18 * (1.0 - features["presence:funding"])
            + 0.15 * (1.0 - features["presence:governance"])
            + 0.10 * (1.0 - features["presence:communication"])
            + 0.10 * (1.0 - features["edge:governance-funding"])
            + 0.08 * (1.0 - features["edge:publication-communication"])
        )
        if features["implementation:evaluation:open"] > 0.5:
            base -= 0.06
        if features["implementation:governance:polycentric"] > 0.5:
            base -= 0.04
        scenario_losses = {}
        for scenario in scenarios:
            if scenario == "synthetic-base":
                scenario_losses[scenario] = base
            elif scenario == "synthetic-congestion":
                communication_penalty = (
                    0.16
                    if features["implementation:communication:broadcast"] > 0.5
                    else 0.04
                )
                scenario_losses[scenario] = base + communication_penalty
            else:
                raise ValueError(f"unknown synthetic scenario {scenario!r}")
        return {
            "status": "complete",
            "loss": sum(scenario_losses.values()) / len(scenario_losses),
            "scenario_losses": scenario_losses,
            "system_fingerprint": system.fingerprint,
            "loss_spec_sha256": self.conditioned_loss_sha256,
        }


def projection_instability(
    space: DifferentiableSystemSpace, raw: Mapping[str, float], epsilon: float
) -> dict[str, Any]:
    baseline = space.project(raw).system_spec.fingerprint
    sensitive = []
    for key in space.raw_ids:
        if space._raw_kinds[key] == "continuous":
            continue
        changed = False
        for delta in (-epsilon, epsilon):
            perturbed = dict(raw)
            perturbed[key] += delta
            if space.project(perturbed).system_spec.fingerprint != baseline:
                changed = True
        if changed:
            sensitive.append(key)
    return {
        "epsilon": epsilon,
        "sensitive_raw_ids": sensitive,
        "sensitive_fraction": len(sensitive) / max(
            sum(kind == "logit" for kind in space._raw_kinds.values()), 1
        ),
    }


def outer_validate(
    space: DifferentiableSystemSpace,
    surrogate: DifferentiableSurrogate,
    evaluator: BlackBoxSystemEvaluator,
    loss_spec: Mapping[str, Any],
    initial_raw: Mapping[str, float],
    optimized_raw: Mapping[str, float],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    records = {}
    for label, raw in (("initial", initial_raw), ("optimized", optimized_raw)):
        projection = space.project(raw)
        prediction = surrogate.predict_and_gradient(projection.features)
        black_box = evaluator.evaluate(projection.system_spec, loss_spec, config["scenarios"])
        records[label] = {
            "system_spec": projection.system_spec.to_dict(),
            "system_fingerprint": projection.system_spec.fingerprint,
            "projection_decisions": list(projection.decisions),
            "projected_features": dict(projection.features),
            "surrogate_mean": prediction.mean,
            "surrogate_uncertainty": prediction.uncertainty,
            "black_box": dict(black_box),
            "absolute_surrogate_gap": abs(float(black_box["loss"]) - prediction.mean),
        }
    instability = projection_instability(space, optimized_raw, float(config["projection_epsilon"]))
    flags = []
    final = records["optimized"]
    initial = records["initial"]
    if final["absolute_surrogate_gap"] > float(config["maximum_absolute_gap"]):
        flags.append("surrogate-gap-exceeds-bound")
    if final["surrogate_uncertainty"] > float(config["maximum_uncertainty"]):
        flags.append("surrogate-uncertainty-exceeds-bound")
    if instability["sensitive_raw_ids"]:
        flags.append("projection-boundary-sensitive")
    if (
        final["surrogate_mean"] < initial["surrogate_mean"]
        and final["black_box"]["loss"] > initial["black_box"]["loss"]
    ):
        flags.append("surrogate-improvement-blackbox-regression")
    return {
        "protocol": {
            "evaluator": config["evaluator"],
            "data_role": config["data_role"],
            "scenarios": list(config["scenarios"]),
            "thresholds": {
                "maximum_absolute_gap": config["maximum_absolute_gap"],
                "maximum_relaxation_projection_gap": config[
                    "maximum_relaxation_projection_gap"
                ],
                "maximum_uncertainty": config["maximum_uncertainty"],
                "projection_epsilon": config["projection_epsilon"],
            },
        },
        "records": records,
        "projection_instability": instability,
        "goodhart_flags": flags,
    }


def run_synthetic_proof(
    spec: Mapping[str, Any],
    schema: Mapping[str, Any],
    objective_compilation: Mapping[str, Any],
    loss_spec: Mapping[str, Any],
) -> dict[str, Any]:
    """Run a deterministic synthetic inner/outer differentiable design proof."""

    validate_differentiable_design(spec, schema)
    binding = spec["objective_binding"]
    if canonical_sha256(objective_compilation) != binding["compilation_sha256"]:
        raise ValueError("objective compilation hash mismatch")
    if objective_compilation["objective_spec"] != binding["objective_spec"]:
        raise ValueError("ObjectiveSpec binding mismatch")
    if loss_spec_sha256(loss_spec) != binding["loss_spec"]["sha256"]:
        raise ValueError("LossSpec binding hash mismatch")
    if (
        loss_spec["id"] != binding["loss_spec"]["id"]
        or loss_spec["version"] != binding["loss_spec"]["version"]
    ):
        raise ValueError("LossSpec binding identity mismatch")

    space = DifferentiableSystemSpace(spec)
    surrogate = QuadraticAnalyticSurrogate(spec["surrogate"])
    inner = optimize_relaxed(space, surrogate, spec["inner_optimizer"])
    evaluator = SyntheticBlackBoxEvaluator(space, binding["loss_spec"]["sha256"])
    outer = outer_validate(
        space,
        surrogate,
        evaluator,
        loss_spec,
        inner["initial_raw"],
        inner["optimized_raw"],
        spec["outer_validation"],
    )
    relaxed_final = surrogate.predict_and_gradient(space.features(inner["optimized_raw"]))
    projected_final = outer["records"]["optimized"]["surrogate_mean"]
    relaxation_projection_gap = abs(relaxed_final.mean - projected_final)
    outer["relaxation_projection_gap"] = relaxation_projection_gap
    if relaxation_projection_gap > float(
        spec["outer_validation"]["maximum_relaxation_projection_gap"]
    ):
        outer["goodhart_flags"].append("relaxation-projection-gap")
    return {
        "schema": REPORT_SCHEMA,
        "status": "synthetic-proof-only",
        "design": {"id": spec["id"], "version": spec["version"], "sha256": canonical_sha256(spec)},
        "objective_binding": binding,
        "gradient_trace": inner["trace"],
        "optimized_raw": inner["optimized_raw"],
        "relaxed_final": {
            "surrogate_mean": relaxed_final.mean,
            "surrogate_uncertainty": relaxed_final.uncertainty,
        },
        "outer_validation": outer,
        "audit": {
            "potential_goodhart_flags": spec["audit"]["goodhart_flags"],
            "observed_goodhart_flags": outer["goodhart_flags"],
            "prohibited_claims": spec["audit"]["prohibited_claims"],
        },
    }
