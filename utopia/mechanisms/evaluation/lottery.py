"""A deterministic seeded lottery evaluation mechanism."""

from __future__ import annotations

import hashlib
from statistics import fmean
from typing import Sequence

from .base import (
    Assessment,
    AssessorAssignment,
    DecisionDraft,
    EvaluationInputError,
    EvaluationMechanism,
    EvaluationRequest,
    EvidencePacket,
)
from .legacy import LegacyPeerReviewEvaluation


class SeededLotteryEvaluation(LegacyPeerReviewEvaluation):
    """Choose accepted submissions by an auditable seeded random ordering.

    Review scores remain in the decision record as diagnostics but do not
    affect selection. The random key is a SHA-256 digest of mechanism, seed,
    round, and submission identity, so results do not depend on process-global
    RNG state or input iteration order.
    """

    mechanism_id = "seeded-submission-lottery"
    aggregation_rule = "uniform_seeded_lottery_score_diagnostic_only"

    def __init__(self, *, accepted_author_delta: float = 0.0) -> None:
        EvaluationMechanism.__init__(
            self, accepted_author_delta=accepted_author_delta
        )

    def aggregate(
        self,
        request: EvaluationRequest,
        evidence: Sequence[EvidencePacket],
        assignments: Sequence[AssessorAssignment],
        assessments: Sequence[Assessment],
    ) -> tuple[DecisionDraft, ...]:
        if request.seed is None:
            raise EvaluationInputError("Seeded lottery requires an explicit seed")
        scores: dict[str, list[float]] = {
            item.submission_id: [] for item in request.submissions
        }
        for assessment in assessments:
            scores[assessment.submission_id].append(float(assessment.score))

        keyed: list[tuple[str, str, float]] = []
        for submission in request.submissions:
            submission_scores = scores[submission.submission_id]
            if not submission_scores:
                raise EvaluationInputError(
                    f"Submission {submission.submission_id} has no assessments"
                )
            random_key = hashlib.sha256(
                (
                    f"{self.mechanism_id}|{request.seed}|"
                    f"{request.round_id}|{submission.submission_id}"
                ).encode("utf-8")
            ).hexdigest()
            keyed.append((
                random_key,
                submission.submission_id,
                fmean(submission_scores),
            ))
        keyed.sort(key=lambda item: (item[0], item[1]))
        slots = self.slots(request)
        return tuple(
            DecisionDraft(
                submission_id=submission_id,
                outcome="accept" if rank <= slots else "reject",
                aggregate_score=score,
                rank=rank,
                slots=slots,
                random_key=random_key,
            )
            for rank, (random_key, submission_id, score) in enumerate(keyed, 1)
        )
