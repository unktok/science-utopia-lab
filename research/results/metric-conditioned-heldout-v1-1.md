# Metric-conditioned Optimization Study v1.1: held-out result

Status: complete experimental simulation result; not a validated science-policy
claim.

## Question

When the simulator, eight-parameter design space, optimizer, budget, and seeds
are held fixed, does changing the optimization `LossSpec` change the selected
institutional system and its held-out behavior?

## Protocol boundary

- optimization arms: participation/review, topic-entropy proxy, and
  review-burden proxy;
- development budget: five candidates per arm on seeds 601, 607, and 617;
- common held-out seeds: 701, 709, 719, 727, and 733;
- source commit: `1078279d1ce833afe9ffb6b7c262da15357b76ab`;
- study revision: `23cbe8a107e5`;
- winner freeze:
  `254c3366e921787ad6a36776801b1cb3b278e2cb36ef247da4cb127b6459244d`;
- decision policy: `report_only`; no promotion veto or universal-winner rule.

All 15 held-out runs completed. The commit-pinned cross-evaluation report has
SHA-256 `51f077a33c6823e2c3b0ca9d66a53a53be7dc7fcd16ccf5845bd2e8833db05cb`.
The independently validated paper slice has SHA-256
`47c444af57a84d86a9fc8d9136fd710305a7b634f30723fdd452f48366ada513`.

## Selected institutional designs

The three objectives selected two, not three, distinct designs.

| Parameter | Participation/review design | Topic and burden design |
|---|---:|---:|
| acceptance rate | 0.4968 | 0.1132 |
| reviews per paper | 3 | 4 |
| reviewer capacity | 8 | 2 |
| reviewer matching | topic | random |
| review policy | persona | standardized |
| funding slots fraction | 0.3907 | 0.3274 |
| resubmission cost | 12.89 | 16.39 |

Topic entropy and review burden independently selected the same design
`d3536002463db`. Their arm-labelled held-out trajectories are independent
stochastic repetitions of that design and must not be interpreted as two
different institutions.

## Held-out findings

The two distinct designs exhibit a descriptive rank reversal across losses.
The participation/review design has held-out aggregate losses 0.295 on its own
loss, 2.076 on review burden, and -1.732 on topic entropy. The duplicated
topic/burden design has corresponding estimates around 0.288, 1.449--1.454,
and -1.712. Lower is better in every loss column. Thus the low-capacity design
ranks better under participation/review and burden scoring, whereas the
high-capacity design ranks better under topic-entropy scoring.

This ordering is not a stable-winner result. All nine paired loss contrasts
(three losses times three arm-labelled pairs) have 95% intervals containing
zero. With five held-out seeds, the experiment supports objective-dependent
descriptive differences but not pairwise superiority.

The most visibly resolved institutional outcomes are operational rather than
normative:

| Held-out metric | Participation/review design | Topic/burden design |
|---|---:|---:|
| active-researcher fraction | 0.82 | 0.80 |
| low-resource active fraction | 0.64 | 0.60 |
| topic entropy | 1.771 | 1.750 |
| review burden per active step | 1.959 | 1.415--1.421 |
| review coverage | 1.000 | 0.552--0.558 |
| accepted papers | 11.6 | 4.0 |

The high-acceptance, high-capacity design produced far more accepted papers
and complete review coverage, but also substantially higher review burden. The
activity and topic-entropy differences are small relative to their five-seed
uncertainty. Accepted-paper count and review coverage are diagnostics here,
not an implicit welfare function.

## Generalization and gaming diagnostics

All three own-objective held-out aggregates are numerically lower than their
development losses, with gaps -0.026, -0.015, and -0.215. None of the three
arm-labelled winners remains the best arm label under its own held-out loss.
This does not identify a failed optimizer: only the three frozen winners, not
all five candidates per arm, received held-out evaluation.

Five preregistered pairwise gaming flags trigger. They are diagnostic alerts,
not technical invalidity, rejection, a protected-slice veto, or a promotion
policy. Interpretation is additionally limited because two arm labels encode
the same institutional design.

## Runtime and integrity

- optimization: 45 logical rows, 30 complete and 15 terminal technical
  failures with `loss: null`;
- physically executed optimization rows: 29, with 45 process attempts;
- provenance-safe adopted logical rows: 16;
- held-out: 15 complete runs and zero terminal failures;
- recorded attempt runtime: at least 52.35 hours in total;
- one interrupted held-out attempt lacks a recoverable wall-time value;
- report-generation errors: zero.

## Interpretation boundary and next experiment

The strongest result is methodological: changing an explicit objective can
change the institution selected by a closed-loop optimizer, and a common
held-out matrix can reveal trade-offs and ranking instability without silently
adding policy constraints. The result does not establish a best scientific
system or external validity for real science policy.

The next confirmatory experiment should increase the held-out seed budget,
repeat the optimizer under multiple search seeds, analyze the duplicated
design as one system, and add objectives with stronger construct validity.
Structural mechanism search should remain a separately sealed campaign.

