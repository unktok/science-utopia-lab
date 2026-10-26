# Evaluation System API v1

This vertical slice represents evaluation as a pure, typed five-stage
mechanism:

1. evidence formation
2. assessor selection
3. assessment
4. aggregation and decision
5. consequences and resource effects

It is deliberately separate from simulation.py. The simulator remains the
owner of agent behavior, time progression, and durable state until a later
shadow-mode integration demonstrates exact parity.

## Time and information boundary

Every submission, evidence item, assessor, and assessment has a logical
InformationTime. An EvaluationRequest has a decision time. The API rejects any
request containing information that becomes available after that decision
time, rather than silently filtering it.

This strict boundary is the first defense against future-information leakage.

## Implemented mechanisms

LegacyPeerReviewEvaluation reproduces the current conference rule without
mutating papers:

- arithmetic mean of review scores
- descending score order
- stable submission order for equal scores by default
- exact seeded per-conference tie-breaking when configured
- max(1, round(n * acceptance_rate)) accepted submissions
- optional fixed slot count

SeededLotteryEvaluation supplies a second instance. It records review scores as
diagnostics but chooses the accepted set using SHA-256 keys derived from the
mechanism id, explicit seed, round id, and submission id. It does not use
process-global random state.

## Provenance and consequences

Every decision records:

- mechanism id and version
- round and decision time
- evidence, assessor, and assessment ids
- aggregation rule, score, rank, and slots
- seed and random key when applicable
- a hash of the complete submission and assessment inputs

Consequences are declared as ResourceEffect values before being applied.
Ledger rows retain the originating decision and effect ids. Reconciliation
checks one-to-one coverage, metadata, arithmetic, and per-actor balance chains.

The default acceptance resource effect is zero, matching the fact that current
conference acceptance does not itself create an academic grant. Tests use a
non-zero configured effect to prove that consequence accounting is complete.

## Integration seam

After long-running experiments finish:

1. construct EvaluationRequest immediately before the current phase-4 decision
   using the conference id as round id and the existing per-conference
   tie-break seed when seeded tie-breaking is enabled
2. run LegacyPeerReviewEvaluation in shadow mode
3. compare accepted ids, rejected ids, scores, rank, and provenance
4. fail closed on any mismatch for several stored and fresh runs
5. only then let the typed result drive paper mutation and downstream effects

The initial integration must keep current reviewer assignment and review
generation unchanged. Those are adapted into supplied assessments; replacing
them is a separate experiment.
