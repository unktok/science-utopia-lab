# Stateful government policy mechanism v1

## Research role

This slice adds government as an independent, stateful mechanism family. It is
not a label attached to evaluation. A government node:

1. receives typed outputs from evaluation, funding, and publication;
2. requires the canonical event lineage attached to those observations;
3. makes a versioned policy decision under one of two implementations;
4. sends the same validated policy envelope to evaluation and funding over
   independently delayed typed edges;
5. checkpoints its observation history, policy-version cursor, trigger state,
   issued policy ids, and last policy fingerprint.

The directives and thresholds are explicitly arbitrary engineering fixtures.
They do not encode a claim that higher acceptance, more funding, government
intervention, or either government implementation is scientifically superior.
The black-box fixture loss measures control-plane coverage only, not scientific
outcomes or held-out performance.

## Policy contract and fail-closed behavior

The policy envelope is `scienceutopia.government-policy.v1` and has exactly:

```text
schema_version
policy_id
policy_version
issuer_id
system_fingerprint
issued_period
observed_event_ids
directives
```

The schema rejects unknown root fields, unknown directive targets, unknown
target fields, non-finite numbers, invalid ranges, empty or duplicate observed
event ids, non-positive versions, and a non-SHA-256 system fingerprint.

Consumer resolution additionally rejects:

- a policy bound to a different complete `SystemSpec` fingerprint;
- an issuer that differs from the actual source mechanism on the delivery;
- an issued period that differs from the delivery's emitted period;
- a policy routed to a target without that target's directive;
- duplicate, stale, or replayed versions;
- multiple issuers without an explicit conflict-resolution mechanism.

This behavior is fail-closed. The adapters do not ignore malformed policy,
coerce values, choose an issuer implicitly, or silently fall back to their
base parameters after receiving an invalid envelope.

## Government implementations

Both implementations observe the same values and emit the same policy schema:

- `production.governance.event-responsive-policy-v1` issues a new monotonic
  policy version whenever new observed system values arrive;
- `production.governance.threshold-policy-v1` accumulates observed values and
  issues only when the configured count threshold is crossed, then advances
  the next threshold by a configured interval.

An observation must have canonical lineage. The government state stores unique
lineage event ids and rejects an already-consumed event. The policy decision
event carries the runtime-generated `input_event_ids`, so every policy can be
traced to the evaluation, funding, and publication events it observed.

For the deterministic fixture, the configured directives are:

```json
{
  "evaluation": {"acceptance_rate": 1.0},
  "funding": {"award_amount_multiplier": 2.0}
}
```

These values are chosen solely to make delivery effects unmistakable in a
four-period test. They are not defaults or recommendations for a real system.

## Policy-aware production consumers

The conference evaluation and compact funding adapters accept an optional
`CONSTRAINT / government-policy` input.

Evaluation persists the latest validated policy and uses its acceptance rate
until superseded. Funding persists the latest validated policy and applies its
award multiplier or slot count until superseded. Their canonical events record
the applied policy id and version in provenance.

Both consumer state schemas advance from v1 to v2 by adding `active_policy`.
Existing v1 checkpoints migrate to v2 with no active policy. The generic graph
checkpoint still owns delivery queues and system identity; the consumer state
owns the monotonic policy cursor needed to reject replay after resume.

Publication is an observed family in this slice but not a policy consumer. The
v1 policy schema supports a fail-closed publication directive for a future
edge, while the demonstrated requirement is delivery to two independent
families: evaluation and funding.

## Structural design space

`stateful-government-science-system-v1` contains 145 valid graphs. The base
evaluation, funding, and publication flow is fixed so government effects are
comparable. The structural optimizer can change:

- government absent versus present;
- event-responsive versus cumulative-threshold implementation;
- presence of each evaluation/funding/publication observation edge;
- presence of each evaluation and funding policy edge;
- one- versus two-period policy latency independently for both consumers.

Legal one-step neighbors therefore cover `node-presence`, `implementation`,
`edge-presence`, and `latency`. Every candidate is executable through the same
production registry, including disconnected intermediate structures that
perform an empty government transition.

The government structural black-box fixture uses
`government_engineering_loss`. It targets two emitted policy decisions plus
technical blocked/connection overhead. It deliberately excludes accepted
papers, publication records, and awarded resources, so the integration loop
does not hard-code a scientific preference for the policy's downstream effect.

## End-to-end evidence

In the fully connected, one-period-latency graph over four periods:

| Structure | Policy decisions | Accepted | Total awarded |
|---|---:|---:|---:|
| no government | 0 | 6 | 100 |
| event-responsive | 4 | 9 | 175 |
| cumulative threshold | 2 | 8 | 150 |

The table demonstrates causal effect, not ranking. Period-zero evaluation and
funding use base settings. The first responsive policy is observed at the end
of period zero, becomes available after one period, and appears in evaluation
and funding event provenance from period one. The threshold implementation
acts later because it must accumulate enough observations.

A four-period uninterrupted execution is byte-equivalent in events and final
checkpoint to two periods, strict-JSON checkpoint round-trip, and two resumed
periods. Changing only a policy-edge latency changes the complete system
fingerprint and makes the old checkpoint incompatible.

The same `AdaptiveRandomSearch` ask/execute/loss/tell boundary samples five
candidates containing government absence, both implementations, and both
policy latencies. Observation metadata remains bound to the complete candidate
fingerprint.

## Test evidence

`tests/optimization/test_government_structural.py` verifies:

- fail-closed policy parsing and consumer resolution;
- event lineage, monotonic policy versions, and government state;
- delayed application to evaluation and funding;
- distinct behavior for absent, responsive, and threshold government;
- deterministic checkpoint/resume and structural incompatibility;
- all 145 candidates execute with unique fingerprints;
- legal structural mutation kinds;
- black-box exploration of absence, implementation, and latency.

## Deliberate limits

- This is a government control-plane mechanism, not a model of a real state,
  electorate, ministry, or democratic process.
- The government observes typed mechanism outputs, not arbitrary hidden
  simulator state.
- Directives are deterministic fixture parameters; no legitimacy, welfare,
  epistemic-quality, distributional, or budget objective is defined.
- Multiple government issuers fail closed because coalition or jurisdiction
  resolution has not been specified.
- Publication policy application, policy expiry, repeal, appeal, and
  constitutional constraints remain future mechanism contracts.
- A scientific campaign needs a separately versioned objective, held-out
  metrics, seeds, budget, and interpretation protocol before this structural
  freedom can be used for substantive claims.
