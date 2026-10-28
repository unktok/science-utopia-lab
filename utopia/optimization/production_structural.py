"""Structural black-box execution over production mechanism adapters.

The finite workload source is deterministic experiment infrastructure.  Every
candidate mechanism selected by the grammar is a production adapter: conference
evaluation, paper-tracker publication, or compact ranked funding.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable, Mapping

from utopia.optimization.blackbox import Observation, Suggestion
from utopia.optimization.structural_space import (
    EdgeOption,
    EdgeSlot,
    NodeOption,
    NodeSlot,
    StructuralGrammar,
    StructuralSystemSpace,
)
from utopia.system import (
    ArtifactTypeSpec,
    ChannelKind,
    ConnectionSpec,
    DeterministicGraphRunner,
    GraphRunResult,
    MechanismFamily,
    MechanismRegistry,
    MechanismResult,
    MechanismSpec,
    MechanismValue,
    PortSpec,
    ScheduleSpec,
    SystemSpec,
)
from utopia.system.production import (
    COMPACT_RANKED_ALLOCATION,
    CONFERENCE_ACCEPTANCE,
    PAPER_TRACKER_PUBLICATION,
    register_production_mechanisms,
)


STRUCTURAL_WORKLOAD_SOURCE = "experiment.structural-production-workload-v1"


@dataclass(frozen=True)
class ProductionStructuralSummary:
    accepted: int
    rejected: int
    publication_records: int
    funding_awards: int
    total_awarded: float
    government_policies: int
    blocked_invocations: int
    mechanism_count: int
    connection_count: int

    def to_dict(self) -> dict[str, int | float]:
        return {
            "accepted": self.accepted,
            "rejected": self.rejected,
            "publication_records": self.publication_records,
            "funding_awards": self.funding_awards,
            "total_awarded": self.total_awarded,
            "government_policies": self.government_policies,
            "blocked_invocations": self.blocked_invocations,
            "mechanism_count": self.mechanism_count,
            "connection_count": self.connection_count,
        }


@dataclass(frozen=True)
class ProductionStructuralRun:
    spec: SystemSpec
    result: GraphRunResult
    summary: ProductionStructuralSummary


LossFunction = Callable[[ProductionStructuralRun], float]


def production_structural_grammar() -> StructuralGrammar:
    """Finite structural grammar whose candidate nodes are production adapters."""

    artifact_types = tuple(
        ArtifactTypeSpec(name)
        for name in (
            "review-batch",
            "paper-decision",
            "publication-record",
            "funding-panel",
            "resource-allocation",
        )
    )
    workload = NodeSlot(
        "workload",
        (
            NodeOption(
                "deterministic-v1",
                MechanismSpec(
                    "workload",
                    MechanismFamily.CUSTOM,
                    STRUCTURAL_WORKLOAD_SOURCE,
                    outputs=(
                        PortSpec(
                            "review_batches", ChannelKind.ARTIFACT, "review-batch"
                        ),
                        PortSpec(
                            "funding_panels", ChannelKind.ARTIFACT, "funding-panel"
                        ),
                    ),
                ),
                ScheduleSpec("workload", 0),
            ),
        ),
    )
    evaluation = NodeSlot(
        "evaluation-policy",
        (
            NodeOption(
                "evaluation-rate",
                MechanismSpec(
                    "evaluation",
                    MechanismFamily.EVALUATION,
                    CONFERENCE_ACCEPTANCE,
                    inputs=(
                        PortSpec(
                            "review_batches", ChannelKind.ARTIFACT, "review-batch"
                        ),
                    ),
                    outputs=(
                        PortSpec(
                            "decisions", ChannelKind.DECISION, "paper-decision"
                        ),
                    ),
                    parameters={
                        "acceptance_rate": 0.5,
                        "acceptance_mode": "rate",
                        "tiebreak_seed": 2718,
                    },
                ),
                ScheduleSpec("evaluation", 1),
            ),
            NodeOption(
                "governed-fixed-slots",
                MechanismSpec(
                    "evaluation",
                    MechanismFamily.GOVERNANCE,
                    CONFERENCE_ACCEPTANCE,
                    inputs=(
                        PortSpec(
                            "review_batches", ChannelKind.ARTIFACT, "review-batch"
                        ),
                    ),
                    outputs=(
                        PortSpec(
                            "decisions", ChannelKind.DECISION, "paper-decision"
                        ),
                    ),
                    parameters={
                        "acceptance_rate": 0.5,
                        "acceptance_mode": "fixed_slots",
                        "tiebreak_seed": 2718,
                    },
                ),
                ScheduleSpec("evaluation", 1),
            ),
        ),
    )
    funding = NodeSlot(
        "funding",
        (
            NodeOption(
                "compact-funding",
                MechanismSpec(
                    "funding",
                    MechanismFamily.FUNDING,
                    COMPACT_RANKED_ALLOCATION,
                    inputs=(
                        PortSpec(
                            "panels",
                            ChannelKind.ARTIFACT,
                            "funding-panel",
                            required=False,
                        ),
                    ),
                    outputs=(
                        PortSpec(
                            "allocations",
                            ChannelKind.RESOURCE,
                            "resource-allocation",
                            required=False,
                        ),
                    ),
                    parameters={"award_slots": 1, "award_amount": 25},
                ),
                ScheduleSpec("funding", 1),
            ),
        ),
        optional=True,
    )
    publication = NodeSlot(
        "publication",
        (
            NodeOption(
                "paper-tracker",
                MechanismSpec(
                    "publication",
                    MechanismFamily.PUBLICATION,
                    PAPER_TRACKER_PUBLICATION,
                    inputs=(
                        PortSpec(
                            "decisions",
                            ChannelKind.DECISION,
                            "paper-decision",
                            required=False,
                        ),
                    ),
                    outputs=(
                        PortSpec(
                            "records",
                            ChannelKind.ARTIFACT,
                            "publication-record",
                            required=False,
                        ),
                    ),
                ),
                ScheduleSpec("publication", 2),
            ),
        ),
        optional=True,
    )

    review_input = EdgeSlot(
        "review-input",
        tuple(
            EdgeOption(
                name,
                ConnectionSpec(
                    "workload",
                    "review_batches",
                    "evaluation",
                    "review_batches",
                    ChannelKind.ARTIFACT,
                    latency=latency,
                ),
            )
            for name, latency in (("instant", 0), ("delayed", 1))
        ),
        optional=False,
    )
    funding_input = EdgeSlot(
        "funding-input",
        tuple(
            EdgeOption(
                name,
                ConnectionSpec(
                    "workload",
                    "funding_panels",
                    "funding",
                    "panels",
                    ChannelKind.ARTIFACT,
                    latency=latency,
                ),
            )
            for name, latency in (("instant", 0), ("delayed", 1))
        ),
    )
    publication_flow = EdgeSlot(
        "publication-flow",
        tuple(
            EdgeOption(
                name,
                ConnectionSpec(
                    "evaluation",
                    "decisions",
                    "publication",
                    "decisions",
                    ChannelKind.DECISION,
                    latency=latency,
                ),
            )
            for name, latency in (("instant", 0), ("delayed", 1))
        ),
    )
    return StructuralGrammar(
        space_id="production-structural-science-system-v1",
        system_id="production-structural-science-system",
        version=1,
        node_slots=(workload, evaluation, funding, publication),
        edge_slots=(review_input, funding_input, publication_flow),
        artifact_types=artifact_types,
        global_invariants=(
            "strict-json-events",
            "production-adapter-state",
            "fingerprint-bound-checkpoints",
        ),
        metadata={
            "purpose": "production-structural-black-box-vertical-slice",
            "workload": "deterministic-experiment-fixture-v1",
            "mechanism_boundary": "production-adapters",
        },
    )


def production_structural_space() -> StructuralSystemSpace:
    return StructuralSystemSpace(production_structural_grammar())


def production_structural_registry() -> MechanismRegistry:
    registry = MechanismRegistry()
    registry.register(STRUCTURAL_WORKLOAD_SOURCE, 1, _structural_workload)
    register_production_mechanisms(registry)
    return registry


def execute_production_structural_candidate(
    space: StructuralSystemSpace,
    candidate: Mapping[str, Any],
    *,
    periods: int = 4,
) -> ProductionStructuralRun:
    spec = space.decode(candidate)
    result = DeterministicGraphRunner(
        spec, production_structural_registry()
    ).run(periods=periods)
    decisions = [
        event
        for event in result.events
        if event.event_type == "evaluation.paper_decided"
    ]
    awards = [
        event for event in result.events if event.event_type == "funding.awarded"
    ]
    summary = ProductionStructuralSummary(
        accepted=sum(event.payload["decision"] == "accept" for event in decisions),
        rejected=sum(event.payload["decision"] == "reject" for event in decisions),
        publication_records=sum(
            event.event_type == "publication.recorded" for event in result.events
        ),
        funding_awards=len(awards),
        total_awarded=sum(float(event.payload["amount"]) for event in awards),
        government_policies=sum(
            event.event_type == "government.policy_decided"
            for event in result.events
        ),
        blocked_invocations=sum(record.status == "blocked" for record in result.trace),
        mechanism_count=len(spec.mechanisms),
        connection_count=len(spec.connections),
    )
    return ProductionStructuralRun(spec, result, summary)


def engineering_demonstration_loss(run: ProductionStructuralRun) -> float:
    """Finite integration-test loss, not a scientific or held-out metric."""

    summary = run.summary
    value = (
        0.2 * summary.blocked_invocations
        + 0.05 * summary.mechanism_count
        + 0.02 * summary.connection_count
        - 1.0 * summary.accepted
        - 0.5 * summary.publication_records
        - 0.01 * summary.total_awarded
    )
    if not math.isfinite(value):
        raise ValueError("production structural loss must be finite")
    return value


def observe_production_structural_suggestion(
    space: StructuralSystemSpace,
    suggestion: Suggestion,
    *,
    periods: int = 4,
    loss_function: LossFunction = engineering_demonstration_loss,
) -> Observation:
    """Execute one suggested production graph and create an ask/tell observation."""

    run = execute_production_structural_candidate(
        space, suggestion.candidate, periods=periods
    )
    loss = loss_function(run)
    if isinstance(loss, bool) or not isinstance(loss, (int, float)) or not math.isfinite(loss):
        raise ValueError("loss_function must return a finite scalar")
    return Observation(
        observation_id="observation-" + suggestion.suggestion_id,
        suggestion_id=suggestion.suggestion_id,
        candidate=suggestion.candidate,
        status="complete",
        loss=float(loss),
        metadata={
            "system_fingerprint": run.spec.fingerprint,
            "event_stream_hash": run.result.event_stream_hash,
            "checkpoint_fingerprint": run.result.checkpoint.fingerprint,
            "summary": run.summary.to_dict(),
        },
    )


def _structural_workload(context) -> MechanismResult:
    period = context.period
    paper_count = 2 if period % 2 == 0 else 3
    papers = [_paper(period, index) for index in range(paper_count)]
    review_batch = {
        "batch_id": f"reviews-{period}",
        "conference_id": "science-conf",
        "conference_name": "Science Conference",
        "topics": ["science-of-science"],
        "papers": papers,
        "reviews": {
            paper["id"]: [
                {
                    "reviewer_id": f"reviewer-{index}",
                    "overall_score": 5 - index,
                    "justification": "deterministic structural workload",
                }
            ]
            for index, paper in enumerate(papers)
        },
    }
    funding_panel = {
        "panel_id": f"funding-{period}",
        "applications": [
            {"applicant_id": f"researcher-{period}-0"},
            {"applicant_id": f"researcher-{period}-1"},
        ],
        "compact_result": {"ranked_application_ids": [1, 0]},
    }
    return MechanismResult(
        outputs={
            "review_batches": (
                MechanismValue(
                    review_batch, artifact_ids=(review_batch["batch_id"],)
                ),
            ),
            "funding_panels": (
                MechanismValue(
                    funding_panel, artifact_ids=(funding_panel["panel_id"],)
                ),
            ),
        }
    )


def _paper(period: int, index: int) -> dict[str, Any]:
    return {
        "id": f"paper-{period}-{index}",
        "title": f"Paper {period}-{index}",
        "abstract": f"Deterministic abstract {period}-{index}",
        "author_id": f"researcher-{period}-{index}",
        "author_type": "researcher",
        "year": period + 1,
        "conference": "science-conf",
        "topics": ["science-of-science"],
        "tags": ["cs.CY"],
        "project_start_year": period,
        "project_end_year": period + 1,
        "maturity": 1,
        "type": "submission",
        "status": "pending",
    }
