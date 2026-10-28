# ADR-0017: Compile declared objective constitutions through validated metrics

- Status: accepted
- Date: 2026-10-28

## Context

The project can optimize a scalar LossSpec and now has a plural Metric /
Objective Landscape. What remained missing was a governed boundary between
the question “what should this scientific system pursue?” and the mechanical
formula supplied to an optimizer.

Directly writing coefficients into a LossSpec hides stakeholder standing,
construct meaning, distribution, time horizon, uncertainty, and the evidence
supporting each proxy. Conversely, an uncompiled normative note cannot drive a
reproducible black-box campaign.

## Decision

Adopt two versioned inputs and one deterministic output:

1. `ObjectiveSpec v1` records governance, stakeholders, constructs, horizons,
   distribution, uncertainty, phase weights, explicit non-veto tradeoffs,
   Goodhart review, and evidence requirements.
2. `ValidatedMetricCardRegistry v1` records the construct-to-observable mapping,
   normalization, direction, limitations, and hash-verified validation evidence.
3. `ObjectiveCompilation v1` emits one standard `LossSpec v1` per declared
   phase plus a provenance and constitution receipt.

The compiler fails closed on unvalidated cards, version or hash mismatch,
missing evidence scopes, failed artifact hashes, unsupported distributions or
time windows, broken references, implicit single-objective phases, and hidden
hard constraints.

ObjectiveSpec may encode an authorized policy, including a state science-policy
choice, but its schema forbids a universal-objective claim. The compiler does
not infer weights or legitimacy.

## Consequences

- Normative choices are diffable and cannot masquerade as measurement facts.
- Metric promotion becomes evidence-gated rather than availability-gated.
- Weight schedules compile reproducibly while remaining visible as policy.
- Existing LossSpec execution can consume future compiled phase objects without
  changing the evaluator contract.
- Phase execution semantics still require a future campaign protocol.
- Rights floors or safety vetoes, if later justified, require a distinct
  explicit constraint design; they are not smuggled in as tradeoffs.
- The current fixture proves the compiler only. It is synthetic and cannot
  promote the Metric / Objective Landscape cards.

## Boundary

The active metric-conditioned study, its three LossSpecs, runtime state, and
evaluation split are neither inputs nor outputs of this decision. This work is
prospective and future-campaign-only.

## Evidence

- [`../objectives/constitutions/objective-constitution-compiler-v1.md`](../objectives/constitutions/objective-constitution-compiler-v1.md)
- [`../objectives/landscape/metric-objective-landscape-v1.md`](../objectives/landscape/metric-objective-landscape-v1.md)
- `research/specs/objective-spec-v1.schema.json`
- `research/specs/validated-metric-card-registry-v1.schema.json`
- `research/specs/objective-compilation-v1.schema.json`

