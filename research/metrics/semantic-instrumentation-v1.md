# Semantic instrumentation v1

Status: report-only vertical slice; not an optimization objective or held-out
evaluation metric.

## Purpose

Provide the minimum typed observation surface needed to study future
epistemic-progress and robustness objectives. This slice validates contracts
and shadow analysis on deterministic synthetic fixtures. It does not yet wire
semantic events into the stochastic simulator.

## Contracts

The bundle schema is
[`../specs/semantic-instrumentation-bundle-v1.schema.json`](../specs/semantic-instrumentation-bundle-v1.schema.json).
Its event families identify themselves independently:

| Family | Schema identifier | Event types |
|---|---|---|
| claim | `scienceutopia.semantic-claim-event.v1` | created, revised, withdrawn |
| evidence | `scienceutopia.semantic-evidence-event.v1` | attached, invalidated |
| verification | `scienceutopia.semantic-verification-event.v1` | completed |
| replication | `scienceutopia.semantic-replication-event.v1` | attempted, resolved |
| correction | `scienceutopia.semantic-correction-event.v1` | issued, propagated |

All causal references point backward in the same run. Claim versions are
contiguous. Evidence and downstream dependency relationships are checked at
the referenced version, not only by an unversioned object name.

Lineage has five explicit dimensions: method, data, model, evaluator, and
organization. A verification or replication is derived as independent only
when every dimension is observed and none overlaps the originating evidence.
`independence_claimed` is retained for audit but does not determine the derived
status.

## Missingness

Core identifiers and references cannot be missing. Measurements that may be
unknown—truth target, prior/posterior probability, evidence strength, lineage,
and replacement references—must use an observed/missing wrapper. Missing
records require one of the versioned reasons and a human-readable detail.

An incomplete lineage produces `independence_status: unknown`; it never
becomes an independent success. Missing probabilities reduce the computable
numerator while the claim/result remains in coverage denominators. A gaming
test that requires an unavailable truth/difficulty universe is marked
`not_evaluable` with `triggered: null`, never reported as a clean negative.

## Fixtures

- `tests/fixtures/semantic-instrumentation-ground-truth-v1.json` includes a
  verified true claim, an independently challenged false claim, a replication
  attempt/result, claim withdrawal, correction issuance, dependent-claim
  revision, and correction propagation.
- `tests/fixtures/semantic-instrumentation-gaming-counterexample-v1.json`
  produces apparently successful verification by testing only easy targets,
  splitting one target into multiple claim IDs, and reusing the original
  lineage while declaring independence.

The second fixture must trigger all three gaming counterdiagnostics and must
receive no verification-weighted information-gain credit.

## Generate a shadow report

From the repository root:

```bash
PYTHONPATH=. ~/.local/bin/python3 -m scripts.reports.semantic_instrumentation_shadow \
  --bundle tests/fixtures/semantic-instrumentation-ground-truth-v1.json \
  --output /tmp/semantic-instrumentation-shadow-report.json
```

The writer refuses overwrite and atomically publishes one JSON document
validated by
[`../specs/semantic-instrumentation-shadow-report-v1.schema.json`](../specs/semantic-instrumentation-shadow-report-v1.schema.json).
The source bundle is read-only.

## Interpretation

The report is evidence about instrumentation behavior, not evidence that any
current Science Utopia institution improves real science. Synthetic truth is a
contract test, not a real-world truth oracle. Shadow diagnostics cannot rank or
select systems, veto a candidate, modify a winner freeze, or reuse the current
metric-conditioned held-out split.

## Promotion requirements

Before any component becomes a future LossSpec:

1. integrate events into a separately versioned simulator mechanism;
2. measure missingness, latency, runtime, and seed dispersion;
3. validate construct behavior under heterogeneous scope and truth regimes;
4. add adversarial tests beyond the three v1 gaming signatures;
5. allocate a new optimization split and untouched evaluation split; and
6. preregister aggregation, direction, constraints, and stopping rules.
