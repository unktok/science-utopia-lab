"""Typed contract and immutable records for evaluation mechanisms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from typing import Any, Mapping, Sequence


def canonical_hash(value: Any) -> str:
    text = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, order=True)
class InformationTime:
    """Logical time controlling which information a mechanism may access."""

    year: int
    phase: int

    def __post_init__(self) -> None:
        if self.year < 0 or self.phase < 0:
            raise ValueError("Information time must be non-negative")


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    submission_id: str
    kind: str
    value: Any
    available_at: InformationTime


@dataclass(frozen=True)
class Submission:
    submission_id: str
    author_ids: tuple[str, ...]
    submitted_at: InformationTime
    evidence: tuple[EvidenceItem, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Assessor:
    assessor_id: str
    available_at: InformationTime
    conflicts: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Assessment:
    assessment_id: str
    submission_id: str
    assessor_id: str
    score: float
    observed_at: InformationTime
    evidence_ids: tuple[str, ...]
    justification: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.score, bool) or not math.isfinite(float(self.score)):
            raise ValueError("Assessment score must be a finite number")


@dataclass(frozen=True)
class EvidencePacket:
    submission_id: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class AssessorAssignment:
    submission_id: str
    assessor_ids: tuple[str, ...]


@dataclass(frozen=True)
class ResourceEffect:
    effect_id: str
    decision_id: str
    actor_id: str
    category: str
    delta: float


@dataclass(frozen=True)
class LedgerEntry:
    effect_id: str
    decision_id: str
    actor_id: str
    category: str
    delta: float
    balance_before: float
    balance_after: float


@dataclass(frozen=True)
class DecisionProvenance:
    mechanism_id: str
    mechanism_version: int
    round_id: str
    decision_at: InformationTime
    submission_id: str
    evidence_ids: tuple[str, ...]
    assessor_ids: tuple[str, ...]
    assessment_ids: tuple[str, ...]
    aggregation_rule: str
    aggregate_score: float | None
    rank: int
    slots: int
    seed: int | None
    random_key: str | None
    input_hash: str


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    submission_id: str
    outcome: str
    aggregate_score: float | None
    rank: int
    provenance: DecisionProvenance
    resource_effects: tuple[ResourceEffect, ...]


@dataclass(frozen=True)
class DecisionDraft:
    submission_id: str
    outcome: str
    aggregate_score: float | None
    rank: int
    slots: int
    random_key: str | None = None


@dataclass(frozen=True)
class EvaluationRequest:
    round_id: str
    decision_at: InformationTime
    submissions: tuple[Submission, ...]
    assessors: tuple[Assessor, ...]
    supplied_assessments: tuple[Assessment, ...]
    acceptance_rate: float
    seed: int | None = None
    acceptance_slots: int | None = None
    opening_balances: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationResult:
    mechanism_id: str
    evidence: tuple[EvidencePacket, ...]
    assignments: tuple[AssessorAssignment, ...]
    assessments: tuple[Assessment, ...]
    decisions: tuple[DecisionRecord, ...]
    ledger: tuple[LedgerEntry, ...]
    closing_balances: Mapping[str, float]


class EvaluationInputError(ValueError):
    pass


class FutureInformationError(EvaluationInputError):
    pass


class EvaluationMechanism(ABC):
    """Five-stage contract for an auditable evaluation system.

    Implementations are pure: the request contains all observations and opening
    balances, and the result contains every decision and resulting ledger row.
    """

    mechanism_id: str
    mechanism_version: int = 1
    aggregation_rule: str

    def __init__(self, *, accepted_author_delta: float = 0.0) -> None:
        if isinstance(accepted_author_delta, bool) or not math.isfinite(
            float(accepted_author_delta)
        ):
            raise ValueError("accepted_author_delta must be finite")
        self.accepted_author_delta = float(accepted_author_delta)

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        self._validate_request(request)
        evidence = self.form_evidence(request)
        assignments = self.select_assessors(request, evidence)
        assessments = self.assess(request, evidence, assignments)
        drafts = self.aggregate(request, evidence, assignments, assessments)
        return self.apply_consequences(
            request, evidence, assignments, assessments, drafts
        )

    @abstractmethod
    def form_evidence(
        self, request: EvaluationRequest
    ) -> tuple[EvidencePacket, ...]:
        """Choose the evidence visible for each submission."""

    @abstractmethod
    def select_assessors(
        self,
        request: EvaluationRequest,
        evidence: Sequence[EvidencePacket],
    ) -> tuple[AssessorAssignment, ...]:
        """Select eligible assessors for each evidence packet."""

    @abstractmethod
    def assess(
        self,
        request: EvaluationRequest,
        evidence: Sequence[EvidencePacket],
        assignments: Sequence[AssessorAssignment],
    ) -> tuple[Assessment, ...]:
        """Produce or ingest assessments using only visible evidence."""

    @abstractmethod
    def aggregate(
        self,
        request: EvaluationRequest,
        evidence: Sequence[EvidencePacket],
        assignments: Sequence[AssessorAssignment],
        assessments: Sequence[Assessment],
    ) -> tuple[DecisionDraft, ...]:
        """Aggregate assessments into ranked draft decisions."""

    @abstractmethod
    def apply_consequences(
        self,
        request: EvaluationRequest,
        evidence: Sequence[EvidencePacket],
        assignments: Sequence[AssessorAssignment],
        assessments: Sequence[Assessment],
        drafts: Sequence[DecisionDraft],
    ) -> EvaluationResult:
        """Materialize decisions, provenance, and resource consequences."""

    def _validate_request(self, request: EvaluationRequest) -> None:
        if (
            isinstance(request.acceptance_rate, bool)
            or not math.isfinite(float(request.acceptance_rate))
            or not 0 <= request.acceptance_rate <= 1
        ):
            raise EvaluationInputError("acceptance_rate must be in [0, 1]")
        if request.acceptance_slots is not None and request.acceptance_slots < 0:
            raise EvaluationInputError("acceptance_slots must be non-negative")

        self._require_unique(
            "submission", [item.submission_id for item in request.submissions]
        )
        self._require_unique(
            "assessor", [item.assessor_id for item in request.assessors]
        )
        self._require_unique(
            "assessment",
            [item.assessment_id for item in request.supplied_assessments],
        )

        submissions = {
            item.submission_id: item for item in request.submissions
        }
        assessors = {item.assessor_id: item for item in request.assessors}
        evidence: dict[str, EvidenceItem] = {}

        for submission in request.submissions:
            if submission.submitted_at > request.decision_at:
                raise FutureInformationError(
                    f"Submission {submission.submission_id} is from the future"
                )
            if not submission.author_ids:
                raise EvaluationInputError(
                    f"Submission {submission.submission_id} has no authors"
                )
            for item in submission.evidence:
                if item.submission_id != submission.submission_id:
                    raise EvaluationInputError(
                        f"Evidence {item.evidence_id} points to another submission"
                    )
                if item.evidence_id in evidence:
                    raise EvaluationInputError(
                        f"Duplicate evidence id: {item.evidence_id}"
                    )
                if item.available_at > request.decision_at:
                    raise FutureInformationError(
                        f"Evidence {item.evidence_id} is from the future"
                    )
                evidence[item.evidence_id] = item

        for assessor in request.assessors:
            if assessor.available_at > request.decision_at:
                raise FutureInformationError(
                    f"Assessor {assessor.assessor_id} is not yet available"
                )

        for assessment in request.supplied_assessments:
            submission = submissions.get(assessment.submission_id)
            assessor = assessors.get(assessment.assessor_id)
            if submission is None:
                raise EvaluationInputError(
                    f"Assessment {assessment.assessment_id} has unknown submission"
                )
            if assessor is None:
                raise EvaluationInputError(
                    f"Assessment {assessment.assessment_id} has unknown assessor"
                )
            if assessment.observed_at > request.decision_at:
                raise FutureInformationError(
                    f"Assessment {assessment.assessment_id} is from the future"
                )
            if assessment.assessor_id in submission.author_ids:
                raise EvaluationInputError(
                    f"Assessment {assessment.assessment_id} is a self-assessment"
                )
            conflicts = set(assessor.conflicts)
            if submission.submission_id in conflicts or conflicts.intersection(
                submission.author_ids
            ):
                raise EvaluationInputError(
                    f"Assessment {assessment.assessment_id} has a declared conflict"
                )
            available_ids = {
                item.evidence_id for item in submission.evidence
            }
            unknown = set(assessment.evidence_ids) - available_ids
            if unknown:
                raise EvaluationInputError(
                    f"Assessment {assessment.assessment_id} cites unknown evidence "
                    f"{sorted(unknown)}"
                )

    @staticmethod
    def _require_unique(kind: str, values: Sequence[str]) -> None:
        if len(set(values)) != len(values):
            raise EvaluationInputError(f"Duplicate {kind} id")

    @staticmethod
    def slots(request: EvaluationRequest) -> int:
        count = len(request.submissions)
        if count == 0:
            return 0
        if request.acceptance_slots is not None:
            return min(request.acceptance_slots, count)
        return min(max(1, round(count * request.acceptance_rate)), count)

    def _materialize_result(
        self,
        request: EvaluationRequest,
        evidence: Sequence[EvidencePacket],
        assignments: Sequence[AssessorAssignment],
        assessments: Sequence[Assessment],
        drafts: Sequence[DecisionDraft],
    ) -> EvaluationResult:
        from .ledger import apply_resource_effects, reconcile_resource_effects

        submission_by_id = {
            item.submission_id: item for item in request.submissions
        }
        evidence_by_submission = {
            item.submission_id: item for item in evidence
        }
        assignment_by_submission = {
            item.submission_id: item for item in assignments
        }
        assessments_by_submission: dict[str, list[Assessment]] = {
            item.submission_id: [] for item in request.submissions
        }
        for assessment in assessments:
            assessments_by_submission[assessment.submission_id].append(assessment)

        decisions: list[DecisionRecord] = []
        effects: list[ResourceEffect] = []
        for draft in drafts:
            packet = evidence_by_submission[draft.submission_id]
            assignment = assignment_by_submission[draft.submission_id]
            used_assessments = assessments_by_submission[draft.submission_id]
            input_hash = canonical_hash({
                "submission": asdict(submission_by_id[draft.submission_id]),
                "evidence_ids": packet.evidence_ids,
                "assessor_ids": assignment.assessor_ids,
                "assessments": [asdict(item) for item in used_assessments],
            })
            provenance = DecisionProvenance(
                mechanism_id=self.mechanism_id,
                mechanism_version=self.mechanism_version,
                round_id=request.round_id,
                decision_at=request.decision_at,
                submission_id=draft.submission_id,
                evidence_ids=packet.evidence_ids,
                assessor_ids=assignment.assessor_ids,
                assessment_ids=tuple(
                    item.assessment_id for item in used_assessments
                ),
                aggregation_rule=self.aggregation_rule,
                aggregate_score=draft.aggregate_score,
                rank=draft.rank,
                slots=draft.slots,
                seed=request.seed,
                random_key=draft.random_key,
                input_hash=input_hash,
            )
            decision_id = canonical_hash({
                "provenance": asdict(provenance),
                "outcome": draft.outcome,
            })
            decision_effects: tuple[ResourceEffect, ...] = ()
            if draft.outcome == "accept" and self.accepted_author_delta != 0:
                actor_id = submission_by_id[draft.submission_id].author_ids[0]
                effect = ResourceEffect(
                    effect_id=canonical_hash({
                        "decision_id": decision_id,
                        "actor_id": actor_id,
                        "category": "evaluation_acceptance",
                        "delta": self.accepted_author_delta,
                    }),
                    decision_id=decision_id,
                    actor_id=actor_id,
                    category="evaluation_acceptance",
                    delta=self.accepted_author_delta,
                )
                decision_effects = (effect,)
                effects.append(effect)
            decisions.append(DecisionRecord(
                decision_id=decision_id,
                submission_id=draft.submission_id,
                outcome=draft.outcome,
                aggregate_score=draft.aggregate_score,
                rank=draft.rank,
                provenance=provenance,
                resource_effects=decision_effects,
            ))

        ledger, closing = apply_resource_effects(request.opening_balances, effects)
        errors = reconcile_resource_effects(effects, ledger)
        if errors:
            raise EvaluationInputError(
                "Resource effects failed reconciliation: " + "; ".join(errors)
            )
        return EvaluationResult(
            mechanism_id=self.mechanism_id,
            evidence=tuple(evidence),
            assignments=tuple(assignments),
            assessments=tuple(assessments),
            decisions=tuple(decisions),
            ledger=ledger,
            closing_balances=closing,
        )
