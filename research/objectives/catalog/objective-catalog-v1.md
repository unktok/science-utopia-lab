# Objective catalog v1: future LossSpec research space

**Status:** versioned research catalog for campaigns after metric-conditioned
optimization v1.1  
**Machine-readable source:** [`objective-catalog-v1.json`](objective-catalog-v1.json)  
**Schema:** [`objective-catalog-v1.schema.json`](objective-catalog-v1.schema.json)

## What this is

This catalog turns the project's science-of-science and local
`ai-scientist-survey` notes into falsifiable future objective proposals. It is
not an executable `LossSpec`, a ranking of the active v1.1 arms, or a claim that
one metric represents scientific value.

The active three LossSpecs remain unchanged:

- `participation-review-tradeoff-probe`;
- `topic-diversity-probe`;
- `review-burden-probe`.

The catalog begins the *next* research cycle: specify the construct, ask what
the simulator actually observes, name what is missing, then allocate new
optimization and held-out evidence before exposing a proxy to search.

## Why no universal composite

Epistemic progress, novelty, robustness, diversity, participation, efficiency,
and public value answer different normative questions. A fixed weighted sum
would hide who chose the weights and turn a collection of imperfect proxies
into one more target. Catalog v1 therefore permits separate metric arms,
Pareto/vector comparison, temporary campaign-specific scalarization, and
explicit epsilon constraints, but marks none as the default or universal
answer.

The preferred empirical design remains metric-conditioned comparison: hold the
simulator, design space, optimizer, budget, and seed roles fixed; change the
declared `LossSpec`; freeze each winner; then cross-evaluate on common untouched
diagnostics. Rank reversals and different selected systems are results, not
problems to average away.

## Construct and implementation map

| Construct | Candidate observable | Current feasibility | Main missing capability | Main Goodhart failure |
|---|---|---|---|---|
| epistemic progress | verification-weighted information gain | not yet implementable | claim, belief, evidence, verifier lineage | easy claims or manipulated priors |
| novelty | conventional-core + atypical discriminating-test portfolio | partially derivable | lineage, typed tests, later validation | incoherence and surprise arbitrage |
| robustness | replication and correction profile | not yet implementable | replication/correction graph | easy-test selection and correlated “independence” |
| diversity | Rao–Stirling + branch survival/coherence | partially derivable | disparity matrix and branch lineage | ontology splitting or incoherent fragmentation |
| participation | cohort + route-specific participation profile | partially derivable | opportunity denominators and exit reasons | forced/nominal retention and activity inflation |
| efficiency | marginal verified return profile | not yet implementable | defensible return numerator and full cost ledger | suppressing hard research or shifting unlogged costs |
| public value | mission-outcome distribution profile | not yet implementable | mission, stakeholder, outcome, standing model | official KPI substitution and hidden externalities |

“Partially derivable” is not permission to optimize. It means a report-only
prototype can be computed from some native fields while its missing construct
components remain explicit.

## Loss versus held-out diagnostic

The catalog records this boundary per proxy:

- `optimization_input`: it may become a future LossSpec component only after a
  new optimization split is allocated. It names no held-out diagnostic as an
  input.
- `held_out_only`: it remains invisible to the optimizer until its construct
  and measurement model are validated.
- `shadow_diagnostic`: it can be reported beside an optimization input but may
  not select candidates.

Current held-out activity diagnostics—review coverage, submissions, decisions,
accepted papers, attrition, and the funding/resource ledger—remain useful for
detecting induced behavior. They do not certify truth, robustness, efficiency,
or public value.

## Evidence boundary

The machine-readable citations pin two repository snapshots:

- ScienceUtopia at `b528d0a93a21287f62bbc3d9ab252e8c94bc40ba`;
- `t46/ai-scientist-survey` at
  `02b437b854e73f1bd8a274399e56167ee05a4400`.

Each source has a path/identifier and section or line locator. Local synthesis
documents are design evidence, not independent empirical confirmation. Where
the catalog relies on published definitions or empirical findings, it also
records DOI-level sources. The source review started from the survey's
`research/TOPIC-MAP.md`, as required by that repository's continuity contract.

## Promotion path for a future candidate

1. Implement and version all required event fields; missing values stay
   unknown rather than receiving a favorable penalty.
2. Validate the observable against synthetic ground truth or independently
   coded fixtures, including explicit gaming counterexamples.
3. Measure seed variance, missingness, latency, and runtime without optimizer
   exposure.
4. Preregister a future campaign with a distinct `LossSpec`, optimization
   split, common held-out suite, design space, budget, and stopping rule.
5. Freeze arm winners before held-out evaluation and report all component
   values, system differences, rank reversals, and generalization gaps.

This process can reject a candidate. A catalog entry is a testable proposal,
not a commitment to make the proxy decision-active.
