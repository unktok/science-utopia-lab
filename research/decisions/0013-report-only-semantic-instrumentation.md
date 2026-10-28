# Decision 0013: Validate semantic instrumentation before objective promotion

- Status: accepted vertical-slice boundary
- Date: 2026-10-28
- Scope: future epistemic-progress and robustness measurement

## Context

Objective Catalog v1 marks epistemic progress and robustness as not yet
implementable. Publication counts, review scores, reviewer agreement, and an
absence of retractions do not establish either construct. The missing
primitives are typed claim versions, evidence lineage, independent
verification, replication attempts and outcomes, corrections, and downstream
propagation.

Adding a scalar objective before those primitives are validated would reward
missingness, correlated verification, easy-claim selection, or claim splitting.
It would also risk consuming the active metric-conditioned study's held-out
evidence for a different purpose.

## Decision

Introduce semantic instrumentation v1 as a strictly `report_only` observation
layer. It defines separate versioned contracts for:

- `claim.created`, `claim.revised`, and `claim.withdrawn`;
- `evidence.attached` and `evidence.invalidated`;
- `verification.completed`;
- `replication.attempted` and `replication.resolved`; and
- `correction.issued` and `correction.propagated`.

Every event has exact fields, a contiguous sequence, run identity, actor and
institution, earlier source-event references, and family-specific payload.
Claims use explicit `claim-id@version` references. Verification and replication
carry method, data, model, evaluator, and organization lineage.

Observed semantic values use `{status: observed, value: ...}`. Unknown values
use `{status: missing, reason: ..., detail: ...}`. Missing lineage remains in
the denominator and can never count as independence. Invalid structure—forward
references, version gaps, orphan evidence, replication results without an
attempt, corrections without a prior challenge, or propagation outside a
dependency relation—fails closed.

## Shadow diagnostics

The report keeps components separate:

- claim–evidence and verification coverage;
- lineage completeness and explicit missingness;
- derived independence versus declared independence;
- verification-weighted entropy reduction;
- synthetic-truth Brier improvement;
- replication attempt and resolution coverage;
- synthetic-truth alignment of independent results;
- correction issuance, latency, propagation, and stale dependencies; and
- gaming counterdiagnostics for correlated independence, claim splitting, and
  avoidance of hard synthetic targets.

No composite progress or robustness score is emitted. Entropy reduction and
synthetic truth are distinct because confidence can increase in the wrong
direction. Replication coverage and correction performance remain a vector.

## Authorization boundary

The bundle contract requires `instrumentation_use: report_only`. The report
records `optimization_input: false`, `candidate_selection: false`, and
`promotion_veto: false`. The implementation exposes validation and report
construction but no `LossSpec`, optimizer adapter, ranker, or promotion API.

Synthetic truth is permitted only in bundles classified as synthetic fixtures.
An experimental shadow stream must record ground truth as explicitly missing;
it cannot pretend that a simulator or expert label supplies an oracle.

This slice does not change Objective Catalog v1's promotion status. Promotion
would require simulator integration, observational validation across seeds,
latency and variance measurement, a new optimization split, and a new
preregistered campaign. The active v1.1 LossSpecs, study manifest, held-out
suite, seeds, and experiment worktree remain untouched.

## Consequences

- Later simulator mechanisms can emit a stable semantic log without deciding
  the final objective in advance.
- Full attempt denominators, negative results, failed replications, missing
  lineages, and corrections cannot silently disappear.
- Self-declared independence is auditable against actual lineage.
- Synthetic fixtures demonstrate both recovery of known truth/correction and
  explicit Goodhart counterexamples before any optimizer exposure.
