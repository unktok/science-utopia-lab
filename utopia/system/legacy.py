"""Adapter between the fixed legacy topology and whole-system ``SystemSpec``."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

from utopia.optimization.design_space import validate_candidate

from .model import (
    AgentTypeSpec,
    ArtifactTypeSpec,
    ChannelKind,
    ConnectionSpec,
    MechanismFamily,
    MechanismSpec,
    PortSpec,
    ScheduleSpec,
    SystemSpec,
)
from .validation import validate_system_spec


LEGACY_ADAPTER = "science-utopia.legacy-fixed-v1"


@dataclass(frozen=True)
class LegacyExecutionPlan:
    system_id: str
    system_fingerprint: str
    years: int
    cli_args: tuple[str, ...]


class LegacyCompilationError(ValueError):
    pass


def legacy_candidate_to_system_spec(
    space: Mapping[str, Any], candidate: Mapping[str, Any]
) -> SystemSpec:
    """Lift the current eight-variable candidate into a restricted SystemSpec.

    This does not claim the legacy topology is the desired scientific system.
    It gives the optimizer and run records a whole-system design object while
    preserving the current simulator's exact execution surface.
    """

    validate_candidate(space, candidate)
    fixed = space["fixed_arguments"]

    artifacts = tuple(
        ArtifactTypeSpec(artifact_type_id, description)
        for artifact_type_id, description in (
            ("researcher-state", "Agent identity, capability, and resources"),
            ("research-output", "A submitted research artifact"),
            ("evaluation-decision", "An evaluation outcome and provenance"),
            ("published-output", "An output exposed to the public record"),
            ("citation-signal", "A citation or use signal"),
            ("funding-application", "A request for research resources"),
            ("resource-allocation", "A resource transfer or allocation"),
        )
    )

    mechanisms = (
        MechanismSpec(
            "legacy.population",
            MechanismFamily.POPULATION,
            "legacy.population.university-only-v1",
            outputs=(
                PortSpec("researchers", ChannelKind.SIGNAL, "researcher-state"),
            ),
            parameters={
                "mode": fixed["population_mode"],
                "researchers_per_institution": fixed["researchers_per_institution"],
                "resource_profile": fixed.get("population_resource_profile"),
            },
        ),
        MechanismSpec(
            "legacy.research",
            MechanismFamily.RESEARCH,
            "legacy.research.llm-project-cycle-v1",
            inputs=(
                PortSpec("researchers", ChannelKind.SIGNAL, "researcher-state"),
                PortSpec("resources", ChannelKind.RESOURCE, "resource-allocation", required=False),
            ),
            outputs=(
                PortSpec("submissions", ChannelKind.ARTIFACT, "research-output"),
                PortSpec("applications", ChannelKind.ARTIFACT, "funding-application"),
            ),
            parameters={
                "funding_application_cost": candidate["funding_application_cost"],
            },
        ),
        MechanismSpec(
            "legacy.evaluation",
            MechanismFamily.EVALUATION,
            "legacy.evaluation.peer-review-v1",
            inputs=(PortSpec("submissions", ChannelKind.ARTIFACT, "research-output"),),
            outputs=(PortSpec("decisions", ChannelKind.DECISION, "evaluation-decision"),),
            parameters={
                "acceptance_rate": candidate["acceptance_rate"],
                "reviews_per_paper": candidate["reviews_per_paper"],
                "reviewer_capacity": candidate["reviewer_capacity"],
                "reviewer_matching": candidate["reviewer_matching"],
                "review_policy": candidate["review_policy"],
                "acceptance_tiebreak": fixed["acceptance_tiebreak"],
                "acceptance_mode": fixed["acceptance_mode"],
            },
        ),
        MechanismSpec(
            "legacy.publication",
            MechanismFamily.PUBLICATION,
            "legacy.publication.conference-v1",
            inputs=(
                PortSpec("submissions", ChannelKind.ARTIFACT, "research-output"),
                PortSpec("decisions", ChannelKind.DECISION, "evaluation-decision"),
            ),
            outputs=(PortSpec("publications", ChannelKind.ARTIFACT, "published-output"),),
            parameters={"resubmission_cost": candidate["resubmission_cost"]},
        ),
        MechanismSpec(
            "legacy.communication",
            MechanismFamily.COMMUNICATION,
            "legacy.communication.citation-v1",
            inputs=(PortSpec("publications", ChannelKind.ARTIFACT, "published-output"),),
            outputs=(PortSpec("citations", ChannelKind.SIGNAL, "citation-signal"),),
        ),
        MechanismSpec(
            "legacy.funding",
            MechanismFamily.FUNDING,
            "legacy.funding.fixed-budget-v1",
            inputs=(PortSpec("applications", ChannelKind.ARTIFACT, "funding-application"),),
            outputs=(PortSpec("allocations", ChannelKind.RESOURCE, "resource-allocation"),),
            parameters={
                "allocation_mode": fixed["funding_allocation_mode"],
                "budget_mode": fixed["funding_budget_mode"],
                "budget_slots_fraction": candidate["funding_budget_slots_frac"],
            },
        ),
    )

    spec = SystemSpec(
        system_id="legacy-fixed-topology",
        version=1,
        agent_types=(
            AgentTypeSpec(
                "researcher",
                ("produce-research", "evaluate-research", "apply-for-funding"),
                "Legacy university researcher agent",
            ),
        ),
        artifact_types=artifacts,
        mechanisms=mechanisms,
        connections=(
            ConnectionSpec(
                "legacy.population",
                "researchers",
                "legacy.research",
                "researchers",
                ChannelKind.SIGNAL,
            ),
            ConnectionSpec(
                "legacy.research",
                "submissions",
                "legacy.evaluation",
                "submissions",
                ChannelKind.ARTIFACT,
            ),
            ConnectionSpec(
                "legacy.research",
                "submissions",
                "legacy.publication",
                "submissions",
                ChannelKind.ARTIFACT,
            ),
            ConnectionSpec(
                "legacy.evaluation",
                "decisions",
                "legacy.publication",
                "decisions",
                ChannelKind.DECISION,
            ),
            ConnectionSpec(
                "legacy.publication",
                "publications",
                "legacy.communication",
                "publications",
                ChannelKind.ARTIFACT,
            ),
            ConnectionSpec(
                "legacy.research",
                "applications",
                "legacy.funding",
                "applications",
                ChannelKind.ARTIFACT,
            ),
            ConnectionSpec(
                "legacy.funding",
                "allocations",
                "legacy.research",
                "resources",
                ChannelKind.RESOURCE,
                latency=1,
            ),
        ),
        schedules=tuple(
            ScheduleSpec(mechanism.mechanism_id, phase)
            for phase, mechanism in enumerate(mechanisms)
        ),
        initial_state={"resource_ledger": "legacy-runtime-managed"},
        global_invariants=(
            "resource-ledger-reconciles",
            "decision-inputs-are-traceable",
            "no-future-information",
        ),
        metadata={
            "compiler": LEGACY_ADAPTER,
            "runtime": {
                "experiment_name": fixed["experiment_name"],
                "rag_device": fixed["rag_device"],
                "log_funding_applications": bool(fixed.get("log_funding_applications")),
                "log_resource_ledger": bool(fixed.get("log_resource_ledger")),
            },
            "source_design_space": space["id"],
            "restricted_topology": True,
        },
    )
    validate_system_spec(spec).require_valid()
    return spec


def compile_legacy_system(spec: SystemSpec, *, years: int) -> LegacyExecutionPlan:
    """Compile the restricted legacy topology to the existing CLI contract."""

    validate_system_spec(spec).require_valid()
    if isinstance(years, bool) or not isinstance(years, int) or years < 1:
        raise LegacyCompilationError("years must be a positive integer")
    if spec.metadata.get("compiler") != LEGACY_ADAPTER:
        raise LegacyCompilationError(f"SystemSpec is not bound to {LEGACY_ADAPTER}")

    expected = {
        "legacy.population": (
            MechanismFamily.POPULATION,
            "legacy.population.university-only-v1",
        ),
        "legacy.research": (
            MechanismFamily.RESEARCH,
            "legacy.research.llm-project-cycle-v1",
        ),
        "legacy.evaluation": (
            MechanismFamily.EVALUATION,
            "legacy.evaluation.peer-review-v1",
        ),
        "legacy.publication": (
            MechanismFamily.PUBLICATION,
            "legacy.publication.conference-v1",
        ),
        "legacy.communication": (
            MechanismFamily.COMMUNICATION,
            "legacy.communication.citation-v1",
        ),
        "legacy.funding": (
            MechanismFamily.FUNDING,
            "legacy.funding.fixed-budget-v1",
        ),
    }
    mechanisms = {item.mechanism_id: item for item in spec.mechanisms}
    if set(mechanisms) != set(expected):
        raise LegacyCompilationError("legacy compiler requires the exact fixed-v1 topology")
    for mechanism_id, (family, implementation) in expected.items():
        mechanism = mechanisms[mechanism_id]
        if mechanism.family != family or mechanism.implementation != implementation:
            raise LegacyCompilationError(
                f"{mechanism_id} requires family {family.value!r} and "
                f"implementation {implementation!r}"
            )
    expected_connections = {
        (
            "legacy.population",
            "researchers",
            "legacy.research",
            "researchers",
            ChannelKind.SIGNAL,
            0,
        ),
        (
            "legacy.research",
            "submissions",
            "legacy.evaluation",
            "submissions",
            ChannelKind.ARTIFACT,
            0,
        ),
        (
            "legacy.research",
            "submissions",
            "legacy.publication",
            "submissions",
            ChannelKind.ARTIFACT,
            0,
        ),
        (
            "legacy.evaluation",
            "decisions",
            "legacy.publication",
            "decisions",
            ChannelKind.DECISION,
            0,
        ),
        (
            "legacy.publication",
            "publications",
            "legacy.communication",
            "publications",
            ChannelKind.ARTIFACT,
            0,
        ),
        (
            "legacy.research",
            "applications",
            "legacy.funding",
            "applications",
            ChannelKind.ARTIFACT,
            0,
        ),
        (
            "legacy.funding",
            "allocations",
            "legacy.research",
            "resources",
            ChannelKind.RESOURCE,
            1,
        ),
    }
    actual_connections = {
        (
            item.source_mechanism,
            item.source_port,
            item.target_mechanism,
            item.target_port,
            item.channel,
            item.latency,
        )
        for item in spec.connections
    }
    expected_schedules = {
        (mechanism_id, phase, "annual")
        for phase, mechanism_id in enumerate(expected)
    }
    actual_schedules = {
        (item.mechanism_id, item.phase, item.trigger) for item in spec.schedules
    }
    if (
        actual_connections != expected_connections
        or actual_schedules != expected_schedules
    ):
        raise LegacyCompilationError("legacy compiler requires the exact fixed-v1 graph")

    population = mechanisms["legacy.population"].parameters
    research = mechanisms["legacy.research"].parameters
    evaluation = mechanisms["legacy.evaluation"].parameters
    publication = mechanisms["legacy.publication"].parameters
    funding = mechanisms["legacy.funding"].parameters
    runtime = spec.metadata.get("runtime")
    if not isinstance(runtime, Mapping):
        raise LegacyCompilationError("metadata.runtime must be an object")

    acceptance_rate = _number(evaluation, "acceptance_rate")
    rate_schedule = ",".join(str(acceptance_rate) for _ in range(years))
    flags = [
        "--experiment_name", str(_required(runtime, "experiment_name")),
        "--population_mode", str(_required(population, "mode")),
        "--researchers_per_institution",
        str(_required(population, "researchers_per_institution")),
        "--funding_allocation_mode", str(_required(funding, "allocation_mode")),
        "--funding_budget_mode", str(_required(funding, "budget_mode")),
        "--acceptance_tiebreak", str(_required(evaluation, "acceptance_tiebreak")),
        "--acceptance_mode", str(_required(evaluation, "acceptance_mode")),
        "--rag_device", str(_required(runtime, "rag_device")),
        "--acceptance_rate_schedule", rate_schedule,
        "--reviews_per_paper", str(_required(evaluation, "reviews_per_paper")),
        "--reviewer_capacity", str(_required(evaluation, "reviewer_capacity")),
        "--reviewer_matching", str(_required(evaluation, "reviewer_matching")),
        "--review_policy", str(_required(evaluation, "review_policy")),
        "--funding_budget_slots_frac",
        str(_number(funding, "budget_slots_fraction")),
        "--funding_application_cost",
        str(_required(research, "funding_application_cost")),
        "--resubmission_cost", str(_number(publication, "resubmission_cost")),
    ]
    if population.get("resource_profile"):
        flags.extend(
            ["--population_resource_profile", str(population["resource_profile"])]
        )
    for name in ("log_funding_applications", "log_resource_ledger"):
        if runtime.get(name):
            flags.append("--" + name)
    return LegacyExecutionPlan(spec.system_id, spec.fingerprint, years, tuple(flags))


def _required(parameters: Mapping[str, Any], name: str) -> Any:
    if name not in parameters:
        raise LegacyCompilationError(f"missing legacy parameter {name!r}")
    return parameters[name]


def _number(parameters: Mapping[str, Any], name: str) -> int | float:
    value = _required(parameters, name)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise LegacyCompilationError(f"legacy parameter {name!r} must be finite")
    return value
