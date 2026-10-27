# Metric-Conditioned Optimization Study v1

Status: preregistration draft; **no model-backed run is authorized until this
protocol is frozen on a clean commit**

## Research question

Holding the simulator, fixed-topology `SystemSpec` design space, optimizer,
budget, optimization seeds, and fidelity constant, how does changing only the
`LossSpec` change the system found by optimization? When each arm's winner is
then frozen, how do those systems compare on one common metric suite over one
untouched evaluation split?

The primary object of study is the mapping

```text
declared LossSpec -> optimization trajectory -> frozen SystemSpec winner
                  -> common held-out evaluation profile
```

Objective resolution is a measurement-quality check inside this study. It is
not the study's main purpose and does not itself define a good objective.

## Claim boundary

This is a synthetic metric-conditioning experiment. It can show that different
formal goals induce different simulated institutions, trade-offs, proxy
gaming, or failures to generalize. It cannot identify a correct national
science policy, scientific-value function, or social-welfare optimum.

The three `LossSpec`s are deliberately contrasting probes:

| Arm | Search-visible loss | Why include it | Known proxy risk |
|---|---|---|---|
| A | participation/review trade-off | continuity-centered composite used in the engineering loop | survival is not wellbeing or knowledge quality; weight 0.05 is a value choice |
| B | negative topic entropy | adversarial proxy stress test: deliberately condition search on a metric whose card forbids monotonic operational use | entropy omits topic disparity, coherence, truth, usefulness, and scientific value |
| C | review burden | exposes the institutional destination of a narrow cost metric | may reduce reviews by suppressing submissions, coverage, or useful evaluation |

None is endorsed. The experiment asks what each one *does*.

Arm B is intentionally outside the metric card's authorized operational uses.
That is the experimental manipulation: it is a bounded synthetic stress test
of what happens when a narrow observable is promoted into a target, not a
proposal to govern science by entropy maximization.

## Frozen executable inputs

Top-level study manifest:
`research/specs/metric-conditioned-optimization-study-v1.json`.

Campaigns:

- `research/specs/metric-conditioned-participation-review-v1.json`
- `research/specs/metric-conditioned-topic-diversity-v1.json`
- `research/specs/metric-conditioned-review-burden-v1.json`

Losses:

- `research/objectives/losses/participation-review-tradeoff-probe-v1.json`
- `research/objectives/losses/topic-diversity-probe-v1.json`
- `research/objectives/losses/review-burden-probe-v1.json`

All arms use `study-v3-longitudinal-pilot.json`, `design-space-v2.json`,
Qwen3-8B/Ollama, the calibrated four-year/10-researcher/one-conference
longitudinal fidelity, `AdaptiveRandomSearch`, optimizer seed `20261028`,
mutation scale `0.2`, three initial suggestions, two adaptive suggestions, and
five total suggestions.

Only `LossSpec` and identifiers/output roots differ across arms. Changing any
other scientific or optimizer input creates a new study version.

## Seed firewall

### Optimization split

Every arm uses the same development seeds: `601, 607, 617`. They are visible to
search and may not later be described as held out.

### Study-held-out evaluation split

Seeds `701, 709, 719, 727, 733` are reserved for the common evaluation stage.
They must not be registered, simulated, inspected, or used to tune losses,
weights, fidelity, optimizer settings, stopping, candidate selection, or metric
implementations until all three winners and their exact `SystemSpec`
fingerprints are frozen.

### Legacy held-out split

Seeds `523, 541, 547` remain attached to the completed first closed-loop
campaign. They are forbidden in every stage of this study, including debugging
and evaluation. They are not repurposed merely because they are unused.

Before execution, an automated audit must verify that all three seed sets are
pairwise disjoint and that neither forbidden nor study-held-out seeds occur in
an optimization registry.

## Search protocol and fairness

Each arm begins from the identical optimizer state. Equal optimizer seed,
initial-random count, mutation scale, suggestion budget, and development seeds
provide procedural parity. The first three proposals must therefore be
byte-identical across arms; adaptive proposals may diverge only after their
arm-specific observations are returned.

The winner of an arm is the earliest technically valid observation at the
minimum aggregate loss after all five suggestions. Ties retain the first
observation, matching controller semantics. There is no manual candidate
replacement.

Identical `(source commit, producer configuration, SystemSpec fingerprint,
fidelity, seed)` simulations may be content-addressed and reused across arms,
but only when the complete immutable artifact and hash are linked into each
campaign record. Loss values may be recomputed from that common trajectory;
LLM outputs or partial aggregates may not be copied. Until this provenance-safe
reuse exists, the conservative procedure is to execute each campaign normally.

## Four separate contracts

### 1. Optimization loss

Only an arm's declared `LossSpec` is returned through `optimizer.tell`. Across
the three development seeds, every arm uses

```text
aggregate loss = mean(per-run loss) + 0.25 * population SD(per-run loss)
```

and requires all three technically valid runs. Lower is better. No protected
slice, funding floor, publication count, or later evaluation metric becomes an
implicit penalty.

### 2. Technical validity

A run is usable only if it completes under the frozen producer configuration,
has a valid run manifest and event/measurement schema, passes native integrity
and resource-accounting checks, passes funding-application trace conservation,
and supplies every input required by that arm's loss. Missing/corrupt inputs
make the observation invalid; they never become a large numeric loss.

Technical validity does not judge whether a simulated outcome is desirable.

### 3. Held-out evaluation metrics

After the three winners are frozen, each is run on all five common evaluation
seeds. The common suite reports:

- active-researcher fraction, aggregate and pre-declared lower-resource slice;
- topic entropy over the fixed ontology;
- review burden, aggregate and lower-resource slice;
- accepted submission rounds and submission/decision volume as shadow activity;
- review coverage as a gaming diagnostic;
- funding allocations, grant/resource inflow, ending-resource distribution,
  attrition, and application-pipeline diagnostics as shadow evidence.

The evaluator is frozen as `metric-conditioned-native-evaluator@1.0.0`; its
formulas and native artifact sources are declared in
`research/metrics/metric-conditioned-held-out-suite-v1.json`. Review coverage
is `logged review actions / (submission rounds * frozen
reviews_per_paper)`. It is unknown, not one, when no submissions occur. The
funding/resource result is structured rather than forced into one scalar: it
retains allocation counts, grant and industry inflow, the ending-balance
distribution (including Gini), and every declared application-pipeline count
by year and in total. Initial-cohort attrition is retained as its own common
metric.

These fields are diagnostics, not covert objectives. No held-out metric
updates an optimizer in this study.

### 4. Decision policy

`report_only`. The study produces no promoted/deployed system and has no veto,
protected-slice floor, or winner-across-objectives rule. Any later promotion
policy requires a new version and new untouched evidence.

## Primary analyses

### Cross-evaluation matrix

Rows are the three frozen arm winners. Columns are every common evaluation
metric and, as a derived view, each of the three losses recomputed on held-out
trajectories. Report all seed-level values, mean, median, population SD, range,
and paired winner-to-winner differences. Do not collapse this matrix into one
overall score.

### Rank reversal

For each metric/loss column, rank the three systems with average ranks for
ties. `observe` columns receive a labelled descriptive descending order, not a
preference claim. Report pairwise Kendall tau-b between columns, every winner
reversal, and whether an arm's own winner remains best under its corresponding
held-out loss. With only three systems, display the raw orders alongside
coefficients.

### Trade-offs

For every winner pair and metric, report the paired-seed mean difference,
paired SD, 95% t interval, and paired standardized effect
`d_z = mean(delta) / SD(delta)`. Report Pareto dominance only over explicitly
named metric subsets; do not declare universal dominance.

### Gaming audit

Pre-declared signatures are:

- burden improves while review coverage, submissions, or accepted papers
  collapse;
- topic entropy improves while participation, lower-resource participation,
  or coherent activity volume collapses;
- aggregate participation improves while the lower-resource slice or resource
  concentration worsens;
- optimization loss improves on development seeds without corresponding
  held-out improvement.

These are flags for interpretation, not technical invalidity or automatic
rejection.

### Generalization

For each arm, report optimization-split incumbent loss, the same loss on each
held-out seed, held-out aggregate loss, and the generalization gap. V1 does not
identify whether the winner would change if all five arm candidates were
ranked on held-out evidence: its preregistered budget evaluates only the three
frozen winners. The report records that estimand as `not_identified` rather
than pretending it was measured. Evaluating all candidates requires a new
version, additional untouched evidence, and a larger held-out budget.

## Resolution and stability check (secondary)

For every search loss and evaluation metric:

- exact aggregate tie rate (tolerance `1e-12`);
- within-system between-seed SD and paired contrast SD;
- system-to-seed signal ratio: SD of system means divided by pooled within-
  system SD;
- leave-one-seed-out rank Spearman correlation and top-rank stability;
- empirical resolution floor:
  `max(numeric floor, t_0.975,df * median paired standard error)`.

A column is labelled `low_resolution` when more than half of pairwise system
contrasts fall inside its resolution floor or median leave-one-seed-out
Spearman is below `0.8`. This label limits interpretation of that column. It
does not select the study's preferred loss or system.

## Budget, time estimate, and stopping

The frozen budget is `3 arms x 5 suggestions x 3 optimization seeds = 45`
optimization runs, followed by at most `3 winners x 5 evaluation seeds = 15`
held-out runs: 60 runs total.

Using the conservative measured longitudinal rate of 1.70 hours/run:

- conservative execution without reuse: 102 serial hours (4.25 days);
- if the nine identical initial design-seed trajectories are safely shared
  across all arms: 42 unique optimization runs/evaluations become 71.4 serial
  hours (2.98 days);
- 20% operational allowance: 122.4 hours without reuse or 85.7 hours with
  provenance-safe reuse.

One local Ollama endpoint is budgeted as one worker; the measured four-worker
microbenchmark did not improve throughput materially. Independent GPU/model
replicas may distribute complete design-seed runs after a representative
benchmark, but do not change producer configuration within the study.

There is no outcome-dependent early stopping. Pause the study only for:

1. source/config drift or a dirty experiment worktree;
2. evidence that optimization or evaluation seeds crossed their firewall;
3. repeated technical failure after the declared retry budget;
4. more than 20% terminally invalid runs in an arm;
5. projected serial compute above the 20%-allowance ceiling; or
6. evaluator/schema defects that invalidate a declared metric.

Do not replace a failed seed with a convenient new seed. Repairing code,
metrics, or protocol creates a new commit and study version; completed evidence
from incompatible versions is not pooled.

## Execution sequence

1. Freeze this protocol, study manifest, three campaign files, three losses,
   evaluator versions, source commit, and environment manifest.
2. Validate configs and seed firewalls; initialize all arms without running.
3. Verify their first three suggestions are identical.
4. Run/observe the three initial suggestions for every arm, then complete two
   adaptive suggestions per arm.
5. Freeze one winner fingerprint per arm and publish the optimization-only
   trace before touching evaluation seeds.
6. Create a separate evaluation registry containing only the three frozen
   winners and seeds `701, 709, 719, 727, 733`.
7. Compute the common metric suite and analyses above.
8. Publish a matrix and uncertainty-rich report under `report_only`; do not
   feed evaluation results back into these optimizers.

## Mechanical gates and commands

The study-level controller enforces the seed firewall and phase order. These
commands are run only from the clean, commit-pinned experiment worktree:

```bash
STUDY=research/specs/metric-conditioned-optimization-study-v1.json

.venv/bin/python scripts/run_metric_conditioned_study.py --study "$STUDY" audit
.venv/bin/python scripts/run_metric_conditioned_study.py --study "$STUDY" init
.venv/bin/python scripts/run_metric_conditioned_study.py --study "$STUDY" suggest-initial
```

Each arm then uses the ordinary closed-loop CLI for `run`, `observe`, and the
two adaptive `suggest` rounds. The study controller refuses to seal winners
until all five suggestions in every arm are terminal. Exact loss ties retain
the lower proposal index.

```bash
.venv/bin/python scripts/run_metric_conditioned_study.py --study "$STUDY" freeze
.venv/bin/python scripts/run_metric_conditioned_study.py --study "$STUDY" plan-evaluation
.venv/bin/python scripts/run_metric_conditioned_study.py --study "$STUDY" run-evaluation
.venv/bin/python scripts/run_metric_conditioned_study.py --study "$STUDY" report-evaluation
```

`plan-evaluation` cannot create a held-out registry before the immutable
three-winner seal exists. The final machine-readable report recomputes every
declared LossSpec for every frozen system and keeps the common metric columns
separate. A failed run or unavailable evaluator is retained as an explicit
missingness reason rather than silently removed or converted to a numeric
penalty.

The same report generator emits the preregistered analysis families rather
than stopping at metric profiles: rank orders and pairwise Kendall tau-b,
paired differences/SD/95% t intervals/`d_z`, directional proxy-gaming flags,
development-to-held-out generalization gaps, and secondary resolution labels
for metric and loss columns. Structured funding/resource seed values and their
field-level summaries remain alongside those scalar analyses.

## Acceptance criteria

The study is complete only when all three search traces are auditable; the
three winner fingerprints were frozen before evaluation; no seed firewall was
crossed; every held-out system-metric cell retains all seed-level observations
or an explicit missingness reason; and the report includes cross-evaluation,
rank reversals, trade-offs, gaming flags, generalization gaps, and secondary
resolution labels without declaring a universal winner.
