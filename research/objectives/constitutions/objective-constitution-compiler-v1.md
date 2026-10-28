# Objective Constitution / LossSpec compiler v1

Status: prospective future-campaign infrastructure. No real metric card is
promoted by this work.

## Why this object exists

Choosing what a state, funder, scientific community, or public institution
wants from science is a normative and governance decision. It cannot be
recovered automatically from simulator columns. Yet a black-box optimizer
eventually needs a numerical loss.

The compiler keeps these layers separate:

```text
ObjectiveSpec
  stakeholders + standing + authority
  constructs + non-equivalences
  time horizon + distribution
  uncertainty/risk
  explicit tradeoffs + phase weights
  Goodhart audit + evidence policy
                 |
                 | exact version/hash match and evidence gates
                 v
ValidatedMetricCardRegistry
  construct -> measured observable
  normalization + preferred direction
  construct/adversarial/reliability evidence
  distribution/time support + limitations
                 |
                 v
ObjectiveCompilation receipt
  constitution summary + evidence provenance
  phase schedule + component coefficients
  ordinary scienceutopia.loss-spec.v1 objects
```

Compilation is translation, not moral discovery. It proves that a declared
policy can be represented by compatible, versioned metric cards. It does not
prove that the policy is legitimate, the weights are socially optimal, or the
metrics work outside their evidence scope.

## ObjectiveSpec constitution

`scienceutopia.objective-spec.v1` requires the following choices to remain
visible in review and in the compilation receipt:

| Field | Question it prevents us from hiding |
|---|---|
| governance | Who has authority, under what mandate, and how can the objective be amended? |
| stakeholders | Who benefits, works, pays, or bears risk, and which rights do they have? |
| constructs | What value is meant, and what common proxies must not be equated with it? |
| time horizon | Which near, delayed, and terminal effects count? |
| distribution | Across which groups is benefit and burden incidence reported? |
| uncertainty | How are seed variation, ignorance, and missing measurements handled? |
| components | Which validated metric card operationalizes each construct? |
| weights/phases | What exchange rate is chosen, when, and for what stated reason? |
| tradeoffs | Which objectives may compensate one another without becoming a hidden veto? |
| Goodhart audit | How could optimization detach the proxy from the construct? |
| evidence policy | What validation and independent review are required before compilation? |

The v1 schema fixes `hard_constraints` to an empty list. This is deliberate:
the compiler cannot silently revive historical protected-slice vetoes. A
future campaign that genuinely needs rights floors or safety constraints must
declare them in a separate, versioned constraint or decision-policy design and
study their authority explicitly. Shadow monitors remain diagnostics.

The governance block also fixes `universal_objective_claim` to `none`. An
ObjectiveSpec may express one authorized policy choice, including a national
science-policy choice, but cannot present that scalarization as the universal
value of science.

## Evidence gate

The compiler accepts a component only when all of these match:

1. metric-card ID, version, and canonical SHA-256;
2. construct identity;
3. status `validated-for-optimization`;
4. required construct-validity, adversarial-validity, and measurement-
   reliability evidence;
5. independent review;
6. declared distribution groups and outcome windows;
7. artifact bytes and their SHA-256;
8. a Goodhart test and normalization evidence.

The Metric / Objective Landscape cards are therefore not automatically
compileable. Their report-only or research-candidate status must first be
supported by a new validation registry. The included registry and evidence are
explicitly synthetic test fixtures; they demonstrate the gate but confer no
real promotion.

## Weight schedules and LossSpecs

Current `LossSpec v1` is scalar and static. The compiler represents an explicit
schedule as one ordinary LossSpec per contiguous phase. For a metric card with

```text
normalized = offset + multiplier * raw
```

the compiler uses `-weight` for a preferred maximize direction and `+weight`
for minimize, then compiles the offset into the intercept. Every phase retains
at least two positive components in v1 so a declared tradeoff cannot silently
become a single-objective phase.

The receipt preserves phase bounds and component coefficients. A future
campaign protocol must additionally declare whether optimizer state continues
or resets at a phase boundary. This compiler does not execute a campaign or
change an optimizer's loss mid-run.

## Synthetic end-to-end fixture

The test fixture balances a synthetic verified-progress index against a
synthetic review lifecycle cost:

| Phase | verified progress | lifecycle burden |
|---|---:|---:|
| explore | 0.50 | 0.50 |
| consolidate | 0.75 | 0.25 |

The negative compiled coefficient for progress means that a larger value lowers
the minimized loss; the positive burden coefficient means that a larger cost
raises it. These are fixture weights, not policy recommendations or empirical
estimates.

Run the compiler:

```bash
.venv/bin/python -m utopia.optimization.objective_compiler \
  tests/fixtures/objective-constitution/objective-spec.synthetic-test.json \
  tests/fixtures/objective-constitution/validated-metric-cards.synthetic-test.json \
  --objective-schema research/specs/objective-spec-v1.schema.json \
  --registry-schema research/specs/validated-metric-card-registry-v1.schema.json \
  --evidence-root .
```

## Non-goals and promotion boundary

- No current LossSpec, campaign registry, runtime record, or evaluation split is
  an input.
- No metric in this change is empirically validated for real science policy.
- Compilation does not select stakeholders, constructs, weights, or schedules.
- Compilation does not turn a shadow diagnostic into an optimizer input.
- A real use requires a new preregistration, evidence artifacts, campaign
  split, protocol, and reviewed ObjectiveSpec.

