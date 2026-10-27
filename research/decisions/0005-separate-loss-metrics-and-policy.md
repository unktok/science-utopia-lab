# ADR 0005: Separate loss, evaluation metrics, validity, and policy

Date: 2026-10-27
Status: accepted

## Context

Earlier documents allowed a metric to act simultaneously as an optimization
objective, a technical gate, and a promotion veto. This obscured what the
optimizer actually changes and led a campaign-specific protected-slice rule to
look like a permanent project constraint.

The intended analogy is supervised learning: a search optimizes a loss, while
held-out metrics such as accuracy evaluate the frozen result.

## Decision

New campaigns define four separate versioned objects:

1. `LossSpec`: the signal returned to the optimizer on optimization seeds;
2. `ValiditySpec`: whether a run is complete and technically usable;
3. `EvaluationMetricSpec`: held-out measurements of a frozen candidate;
4. `DecisionPolicy`: an optional post-evaluation promotion rule, defaulting to
   `report_only`.

The system design or structure is the optimization variable. Metrics do not
change unless a later research campaign explicitly versions and studies them.
Protected-slice measurements are reported by default, but become constraints or
vetoes only when a campaign explicitly declares them.

## Consequences

- The completed confirmation campaign and its veto remain historically valid.
- Its `not_confirmed` decision does not constrain future optimizer campaigns.
- Any metric used to tune or select a candidate is recorded as an effective
  search criterion and cannot also serve as untouched held-out evidence.
- The first closed-loop milestone requires an executable `LossSpec`; it does
  not require a promotion policy.
