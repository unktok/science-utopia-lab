"""Pure adapter for the current mean-score, top-rate peer-review decision."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import random
from statistics import fmean
from typing import Sequence

from .base import (
    Assessment,
    AssessorAssignment,
    DecisionDraft,
    EvaluationInputError,
    EvaluationMechanism,
    EvaluationRequest,
    EvaluationResult,
    EvidencePacket,
)


class LegacyPeerReviewEvaluation(EvaluationMechanism):
    """Match Conference.make_acceptance_decisions without mutating papers.

    Scores are arithmetic means. Papers are ranked descending, with stable
    submission order resolving equal scores. The accepted count is
    max(1, round(n * acceptance_rate)), capped at n, unless fixed slots are
    explicitly supplied.
    """

    mechanism_id = "legacy-peer-review"
    aggregation_rule = "mean_score_desc_stable_submission_order"

    def __init__(
        self,
        *,
        accepted_author_delta: float = 0.0,
        tie_break_mode: str = "stable",
    ) -> None:
        super().__init__(accepted_author_delta=accepted_author_delta)
        if tie_break_mode not in {"stable", "seeded"}:
            raise ValueError("tie_break_mode must be stable or seeded")
        self.tie_break_mode = tie_break_mode
        if tie_break_mode == "seeded":
            self.aggregation_rule = "mean_score_desc_seeded_tie_break"

    def form_evidence(
        self, request: EvaluationRequest
    ) -> tuple[EvidencePacket, ...]:
        return tuple(
            EvidencePacket(
                submission_id=submission.submission_id,
                evidence_ids=tuple(
                    item.evidence_id for item in submission.evidence
                ),
            )
            for submission in request.submissions
        )

    def select_assessors(
        self,
        request: EvaluationRequest,
        evidence: Sequence[EvidencePacket],
    ) -> tuple[AssessorAssignment, ...]:
        selected: dict[str, list[str]] = {
            item.submission_id: [] for item in request.submissions
        }
        for assessment in request.supplied_assessments:
            ids = selected[assessment.submission_id]
            if assessment.assessor_id not in ids:
                ids.append(assessment.assessor_id)
        return tuple(
            AssessorAssignment(
                submission_id=submission.submission_id,
                assessor_ids=tuple(selected[submission.submission_id]),
            )
            for submission in request.submissions
        )

    def assess(
        self,
        request: EvaluationRequest,
        evidence: Sequence[EvidencePacket],
        assignments: Sequence[AssessorAssignment],
    ) -> tuple[Assessment, ...]:
        evidence_ids = {
            packet.submission_id: set(packet.evidence_ids)
            for packet in evidence
        }
        selected = {
            assignment.submission_id: set(assignment.assessor_ids)
            for assignment in assignments
        }
        for assessment in request.supplied_assessments:
            if assessment.assessor_id not in selected[assessment.submission_id]:
                raise EvaluationInputError(
                    f"Unassigned assessment {assessment.assessment_id}"
                )
            if not set(assessment.evidence_ids).issubset(
                evidence_ids[assessment.submission_id]
            ):
                raise EvaluationInputError(
                    f"Assessment {assessment.assessment_id} used hidden evidence"
                )
        return request.supplied_assessments

    def aggregate(
        self,
        request: EvaluationRequest,
        evidence: Sequence[EvidencePacket],
        assignments: Sequence[AssessorAssignment],
        assessments: Sequence[Assessment],
    ) -> tuple[DecisionDraft, ...]:
        by_submission: dict[str, list[float]] = defaultdict(list)
        for assessment in assessments:
            by_submission[assessment.submission_id].append(
                float(assessment.score)
            )

        scored: list[tuple[int, str, float]] = []
        for index, submission in enumerate(request.submissions):
            scores = by_submission[submission.submission_id]
            if not scores:
                raise EvaluationInputError(
                    f"Submission {submission.submission_id} has no assessments"
                )
            scored.append((
                index,
                submission.submission_id,
                fmean(scores),
            ))
        random_keys: dict[str, str] = {}
        if self.tie_break_mode == "stable":
            scored.sort(key=lambda item: -item[2])
        else:
            if request.seed is None:
                raise EvaluationInputError(
                    "Seeded legacy tie-break requires an explicit seed"
                )
            key = f"{request.seed}|{request.round_id}"
            derived_seed = (
                int.from_bytes(
                    hashlib.sha256(key.encode("utf-8")).digest()[:4], "big"
                )
                % (2**31)
            )
            rng = random.Random(derived_seed)
            keyed = [
                (item, rng.random())
                for item in scored
            ]
            random_keys = {
                item[1]: format(random_key, ".17g")
                for item, random_key in keyed
            }
            keyed.sort(key=lambda pair: (-pair[0][2], pair[1]))
            scored = [item for item, _ in keyed]
        slots = self.slots(request)
        return tuple(
            DecisionDraft(
                submission_id=submission_id,
                outcome="accept" if rank <= slots else "reject",
                aggregate_score=score,
                rank=rank,
                slots=slots,
                random_key=random_keys.get(submission_id),
            )
            for rank, (_, submission_id, score) in enumerate(scored, 1)
        )

    def apply_consequences(
        self,
        request: EvaluationRequest,
        evidence: Sequence[EvidencePacket],
        assignments: Sequence[AssessorAssignment],
        assessments: Sequence[Assessment],
        drafts: Sequence[DecisionDraft],
    ) -> EvaluationResult:
        return self._materialize_result(
            request, evidence, assignments, assessments, drafts
        )
