# Confirmation comparison protocol v1

> Historical scope: this document froze a campaign-specific promotion policy.
> Its protected-slice veto is not the default loss or constraint for subsequent
> optimization campaigns. See
> [`objectives/losses/closed-loop-v1.md`](objectives/losses/closed-loop-v1.md).

Status: preregistered before confirmation runs

Date frozen: 2026-10-26

## Question

Does the previously selected increase in annual fixed university funding capacity
from 30% to 50% reproduce its participation-continuity pattern on the untouched
confirmation seeds 401, 409, 419, 421, and 431?

The candidate, objectives, capability floor, protected slice, fidelity, model,
and five confirmation seeds were all fixed before this protocol. No new candidate
is selected from confirmation outcomes.

## Capability failures are outcomes

A technically complete simulation can produce an institutionally unacceptable
world. These are distinct states:

- technical inadmissibility: integrity failure, missing measurement, unreliable
  funding pipeline, mismatched provenance, or incomplete run;
- capability failure: a technically valid world falls below a frozen
  Constitution capability floor.

Technical inadmissibility makes the confirmation comparison incomplete.
Capability failure does not remove or replace a seed and does not make the
comparison incomplete. It is retained as a noncompensable institutional outcome.

For each design, report capability pass/fail/unknown counts. For each paired seed,
report pass-to-pass, pass-to-fail, fail-to-pass, and fail-to-fail transitions.
No pooled mean may compensate for a capability failure.

## Frozen candidate gates

The candidate passes the noncompensable confirmation gates only if all of the
following hold over the five fixed confirmation pairs:

1. candidate capability failures are zero;
2. candidate capability unknowns are zero;
3. no baseline-pass seed becomes candidate-fail;
4. no paired low-resource participation delta is negative;
5. mean aggregate participation delta is at least zero.

If any gate fails, the candidate is `not_confirmed`. If all gates pass but mean
grant input increases, it is `confirmed_tradeoff`, not dominant. If all gates
pass without greater mean grant input, it is eligible only for a subsequent
non-dominance review across the full frozen vector.

These labels concern this simulator and fidelity only. Five seeds do not estimate
a small real-world failure probability, prove statistical significance, or
authorize an optimal-policy claim. Even zero observed failures out of five is
only a provisional robustness result.

## Frozen vector and analysis

The metrics and descriptive paired bootstrap remain those in
[`first-system-comparison.md`](first-system-comparison.md). All five paired deltas
are retained. Resource input is reported beside participation. The bootstrap is
descriptive and uses seed 20261025 with 10,000 resamples.

The comparison code must verify that baseline and candidate share source commit,
model/backend, dataset, evaluator, configuration, fidelity, and every design
variable except `funding_budget_slots_frac`.

## Execution order

1. Freeze this protocol, comparison implementation, tests, and both study specs
   in one clean source commit.
2. Plan baseline and candidate confirmation registries from that commit.
3. Execute all five baseline seeds, then all five candidate seeds. Outcomes do
   not alter the candidate or gates.
4. Generate machine-readable and narrative paired reports.
5. Retain failed institutional outcomes; retry only technical execution failures
   under the existing maximum-attempt policy.
