from __future__ import annotations

from dataclasses import replace

import pytest

from utopia.agents.conference import Conference, ConferenceStatus
from utopia.mechanisms.evaluation import (
    Assessment,
    Assessor,
    EvaluationRequest,
    EvidenceItem,
    FutureInformationError,
    InformationTime,
    LegacyPeerReviewEvaluation,
    LedgerEntry,
    SeededLotteryEvaluation,
    Submission,
    reconcile_resource_effects,
)


SUBMITTED = InformationTime(1, 2)
REVIEWED = InformationTime(1, 3)
DECIDED = InformationTime(1, 4)


def request(*, seed: int | None = None) -> EvaluationRequest:
    scores = {
        "paper-a": (4, 4),
        "paper-b": (5, 3),
        "paper-c": (3, 3),
        "paper-d": (1, 1),
    }
    submissions = tuple(
        Submission(
            submission_id=paper_id,
            author_ids=(f"author-{suffix}",),
            submitted_at=SUBMITTED,
            evidence=(
                EvidenceItem(
                    evidence_id=f"evidence-{suffix}",
                    submission_id=paper_id,
                    kind="manuscript",
                    value={"title": f"Paper {suffix.upper()}"},
                    available_at=SUBMITTED,
                ),
            ),
        )
        for suffix, paper_id in zip("abcd", scores)
    )
    assessors = tuple(
        Assessor(
            assessor_id=f"reviewer-{index}",
            available_at=InformationTime(1, 1),
        )
        for index in range(8)
    )
    assessments = []
    for paper_index, (paper_id, paper_scores) in enumerate(scores.items()):
        suffix = paper_id[-1]
        for review_index, score in enumerate(paper_scores):
            reviewer_index = paper_index * 2 + review_index
            assessments.append(Assessment(
                assessment_id=f"review-{paper_id}-{review_index}",
                submission_id=paper_id,
                assessor_id=f"reviewer-{reviewer_index}",
                score=score,
                observed_at=REVIEWED,
                evidence_ids=(f"evidence-{suffix}",),
                justification=f"Fixture review {review_index}",
            ))
    return EvaluationRequest(
        round_id="testconf-1",
        decision_at=DECIDED,
        submissions=submissions,
        assessors=assessors,
        supplied_assessments=tuple(assessments),
        acceptance_rate=0.5,
        seed=seed,
        opening_balances={
            "author-a": 100,
            "author-b": 100,
            "author-c": 100,
            "author-d": 100,
        },
    )


def test_legacy_adapter_matches_mean_score_and_stable_cutoff() -> None:
    result = LegacyPeerReviewEvaluation().evaluate(request())

    assert [
        (decision.submission_id, decision.aggregate_score, decision.outcome)
        for decision in result.decisions
    ] == [
        ("paper-a", 4.0, "accept"),
        ("paper-b", 4.0, "accept"),
        ("paper-c", 3.0, "reject"),
        ("paper-d", 1.0, "reject"),
    ]


def test_legacy_adapter_matches_current_conference_on_fixture(capsys) -> None:
    evaluation_request = request()
    expected = {
        decision.submission_id: decision.outcome
        for decision in LegacyPeerReviewEvaluation().evaluate(
            evaluation_request
        ).decisions
    }
    conference = Conference(
        conference_id="testconf-1",
        name="Fixture Conference",
        topics=["replay"],
        acceptance_rate=0.5,
    )
    # Config can provide the constructor default; the fixture pins the tested rule.
    conference.acceptance_rate = 0.5
    conference.status = ConferenceStatus.UNDER_REVIEW
    conference.submitted_papers = [
        {
            "id": submission.submission_id,
            "author_id": submission.author_ids[0],
        }
        for submission in evaluation_request.submissions
    ]
    conference.reviews = {
        submission.submission_id: [
            {"overall_score": assessment.score}
            for assessment in evaluation_request.supplied_assessments
            if assessment.submission_id == submission.submission_id
        ]
        for submission in evaluation_request.submissions
    }

    conference.make_acceptance_decisions()
    capsys.readouterr()
    actual = {
        paper["id"]: outcome
        for outcome, papers in conference.decisions.items()
        for paper in papers
    }

    assert actual == expected


def test_seeded_legacy_tie_break_matches_current_conference(capsys) -> None:
    tie_break_seed = 917
    evaluation_request = request(seed=tie_break_seed)
    expected = {
        decision.submission_id: decision.outcome
        for decision in LegacyPeerReviewEvaluation(
            tie_break_mode="seeded"
        ).evaluate(evaluation_request).decisions
    }
    conference = Conference(
        conference_id=evaluation_request.round_id,
        name="Seeded Fixture Conference",
        topics=["replay"],
        acceptance_rate=0.5,
    )
    conference.acceptance_rate = 0.5
    conference.status = ConferenceStatus.UNDER_REVIEW
    conference.submitted_papers = [
        {
            "id": submission.submission_id,
            "author_id": submission.author_ids[0],
        }
        for submission in evaluation_request.submissions
    ]
    conference.reviews = {
        submission.submission_id: [
            {"overall_score": assessment.score}
            for assessment in evaluation_request.supplied_assessments
            if assessment.submission_id == submission.submission_id
        ]
        for submission in evaluation_request.submissions
    }

    conference.make_acceptance_decisions(tiebreak_seed=tie_break_seed)
    capsys.readouterr()
    actual = {
        paper["id"]: outcome
        for outcome, papers in conference.decisions.items()
        for paper in papers
    }

    assert actual == expected


def test_every_decision_has_complete_input_provenance() -> None:
    result = LegacyPeerReviewEvaluation().evaluate(request())

    for decision in result.decisions:
        provenance = decision.provenance
        suffix = decision.submission_id[-1]
        assert provenance.mechanism_id == "legacy-peer-review"
        assert provenance.round_id == "testconf-1"
        assert provenance.evidence_ids == (f"evidence-{suffix}",)
        assert len(provenance.assessor_ids) == 2
        assert len(provenance.assessment_ids) == 2
        assert provenance.rank == decision.rank
        assert len(provenance.input_hash) == 64
        assert len(decision.decision_id) == 64


def test_seeded_lottery_is_deterministic_and_auditable() -> None:
    mechanism = SeededLotteryEvaluation()

    first = mechanism.evaluate(request(seed=73))
    second = mechanism.evaluate(request(seed=73))
    reordered_request = request(seed=73)
    reordered = mechanism.evaluate(replace(
        reordered_request,
        submissions=tuple(reversed(reordered_request.submissions)),
        supplied_assessments=tuple(
            reversed(reordered_request.supplied_assessments)
        ),
    ))

    assert first == second
    assert [
        item.submission_id for item in first.decisions if item.outcome == "accept"
    ] == [
        item.submission_id
        for item in reordered.decisions
        if item.outcome == "accept"
    ]
    assert [item.outcome for item in first.decisions].count("accept") == 2
    assert all(
        item.provenance.seed == 73
        and item.provenance.random_key
        and len(item.provenance.random_key) == 64
        for item in first.decisions
    )


@pytest.mark.parametrize("future_kind", ["evidence", "assessment"])
def test_future_information_is_rejected(future_kind: str) -> None:
    original = request()
    if future_kind == "evidence":
        first_submission = original.submissions[0]
        future_evidence = replace(
            first_submission.evidence[0],
            available_at=InformationTime(2, 1),
        )
        changed = replace(
            original,
            submissions=(
                replace(first_submission, evidence=(future_evidence,)),
                *original.submissions[1:],
            ),
        )
    else:
        changed = replace(
            original,
            supplied_assessments=(
                replace(
                    original.supplied_assessments[0],
                    observed_at=InformationTime(2, 1),
                ),
                *original.supplied_assessments[1:],
            ),
        )

    with pytest.raises(FutureInformationError, match="future"):
        LegacyPeerReviewEvaluation().evaluate(changed)


def test_resource_consequences_are_ledger_reconciled() -> None:
    result = LegacyPeerReviewEvaluation(
        accepted_author_delta=25
    ).evaluate(request())
    effects = tuple(
        effect
        for decision in result.decisions
        for effect in decision.resource_effects
    )

    assert [(entry.actor_id, entry.delta) for entry in result.ledger] == [
        ("author-a", 25.0),
        ("author-b", 25.0),
    ]
    assert result.closing_balances == {
        "author-a": 125.0,
        "author-b": 125.0,
        "author-c": 100.0,
        "author-d": 100.0,
    }
    assert reconcile_resource_effects(effects, result.ledger) == []

    first = result.ledger[0]
    tampered = (
        replace(first, balance_after=999),
        *result.ledger[1:],
    )
    assert reconcile_resource_effects(effects, tampered) == [
        f"ledger arithmetic fails for effect {first.effect_id}"
    ]
