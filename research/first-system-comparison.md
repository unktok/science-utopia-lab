# First paired system comparison

## Research question

Does expanding annual fixed university funding capacity from 30% to 50% of
the initial researcher count improve participation continuity in the calibrated
four-year ScienceUtopia fidelity, and what review-burden, topic-breadth, and
resource-input changes accompany it?

This is the first controlled system comparison, not a claim about real-world
science policy and not a search for a globally optimal system.

## Prospective design choice

The candidate was selected before running the four remaining longitudinal
baseline seeds. It changes exactly one design variable:

| Variable | Baseline | Candidate |
|---|---:|---:|
| `funding_budget_slots_frac` | 0.3 | 0.5 |

All acceptance, review, application-cost, resubmission-cost, population,
fidelity, model, dataset, and seed settings remain fixed. The intervention was
chosen because the calibration run directly observed two resource-driven exits
at the end of year 4. The upper design-space boundary tests whether additional
funding capacity can preserve participation. It also deliberately exposes the
resource-cost trade-off; a participation increase cannot be described as a
cost-free improvement.

Candidate file:
[`specs/first-candidate-funding-slots-v1.json`](specs/first-candidate-funding-slots-v1.json).

## Runs and pairing

- Fidelity: 4 years, 2 institutions, 10 initial researchers, 1 conference.
- Model/backend: Qwen3-8B through local Ollama.
- Exploration seeds: 101, 103, 107, 109, 113.
- Baseline registry: `participation-fidelity-v1` revision `79ec3468cf`.
- Candidate registry: `first-candidate-funding-slots-v1`, revision
  `34349bc4d7`, design `dd6ee5effe4b1`.
- Pairing key: exploration seed. No run is substituted based on outcome.
- Retry policy: at most two harness attempts; resumed checkpoints retain the
  same design and seed identity.

## Prospective operational amendment: global reviewer assignment

The initial replication batch exposed the same order-dependent reviewer
assignment failure in baseline seeds 101 and 107. Seed 101 reached year 4 with
12 submissions; seed 107 reached year 3 with 13. In both cases total capacity
was sufficient to give every paper at least one review, but the greedy seeded
order exhausted all reviewers eligible for a late paper. Seed 103 completed,
and seed 109 was deliberately interrupted after the repeated mechanism was
identified. These artifacts remain diagnostic and are not mixed into the
comparison.

Before any candidate run, reviewer assignment policy
`global-capacitated-review-assignment` version `1.0.0` replaces the greedy
order with a deterministic minimum-cost capacitated bipartite flow. It:

- gives every paper at least one review or fails only when no global matching
  exists;
- maximizes the number of reviews up to the configured per-paper target;
- preserves authorship, conflict-of-interest, reviewer-capacity, topic
  preference, and seeded tie-breaking rules;
- records any paper below the target rather than silently dropping it.

The exact observed 10-reviewer, 13-paper, capacity-4 case is a regression
fixture: 38 of 39 target reviews are globally feasible and every paper receives
at least one. This amendment changes no objective, threshold, design parameter,
candidate, seed, or fidelity. Because it can change trajectories, all five
baseline and all five candidate runs are restarted under one clean source
commit rather than combining pre- and post-fix results.

The replacement registries are `longitudinal-comparison-baseline-v1` and
`first-candidate-funding-slots-v2`; their revisions are frozen by planning
after the repair commit.

The remaining baseline runs are executed first, but their results do not alter
the candidate or analysis rules. Candidate execution begins only after all five
baseline runs pass integrity and funding reliability.

## Admissibility

Every compared run must satisfy:

1. native integrity and resource-ledger reconciliation;
2. Metric Constitution 1.1 hard and capability constraints;
3. funding reliability policy 1.0.0;
4. complete aggregate and fixed low-resource-slice measurements;
5. matching fidelity, model, dataset identity, evaluator version, and seed.

The participation-suitability policy is a fidelity-calibration test, not a
candidate-outcome constraint. Baseline seed 113 already passed policy 1.0.0 at
revision `79ec3468cf`. Applying its strict interior rule to candidates would
incorrectly reject genuine complete retention or complete attrition as a
measurement failure. Candidate runs therefore cite the passed calibration but
do not reapply the interior rule as a ranking gate.

## Frozen comparison outputs

No scalar welfare score is formed. For each metric, retain all five paired
deltas (`candidate - baseline`) and report mean, median, sample standard
deviation, range, and positive/zero/negative pair counts.

| Priority | Metric | Preferred direction |
|---|---|---|
| Primary | aggregate active-researcher fraction | higher |
| Protected slice | low-resource active fraction | no aggregate gain may conceal severe slice harm |
| Secondary | aggregate and low-resource review burden per active researcher-step | lower |
| Diagnostic | final topic entropy | portfolio; no monotonic winner claim |

Exploratory uncertainty for the mean paired delta uses a deterministic
seed-20261025 percentile bootstrap with 10,000 paired resamples. With only five
pairs, intervals are descriptive and no null-hypothesis significance claim is
authorized.

Shadow diagnostics include final total resources, grant income/allocation,
applications, papers, reviews, acceptances, failures, and wall time. Because the
candidate changes funding capacity, any retention gain must be reported beside
additional grant allocation. Pareto or lexicographic language is permitted only
with the full vector and protected slice visible. “Optimal science policy,”
“scientific value,” and real-world causal claims are not authorized.

## Decision rule

- If either design lacks five admissible paired runs, comparison is incomplete.
- If the candidate harms the low-resource participation slice, it is not
  promoted on the basis of aggregate participation.
- If participation improves but resource input increases, record a trade-off,
  not dominance.
- If the full permitted vector weakly improves and at least one decision-active
  metric strictly improves without greater resource input or slice harm, the
  candidate may be called exploratory Pareto-improving inside this simulator.
- Otherwise retain both systems or reject the candidate according to the
  observed trade-off; do not tune this rule after seeing results.
