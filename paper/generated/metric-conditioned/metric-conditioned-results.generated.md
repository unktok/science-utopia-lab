# Metric-conditioned optimization results (generated)

> Generated only after the sealed three-arm optimization and common held-out split passed the completion gate.

The three objectives selected 2 distinct frozen institutional designs under otherwise identical search conditions.
The identity of the best frozen system changed across held-out scoring losses, a descriptive rank reversal between the frozen designs.
All 9 paired held-out loss contrasts have 95% intervals containing zero, so five seeds do not establish stable pairwise superiority.
The topic-entropy and review-burden objectives selected the same design; their arm-labelled held-out trajectories are independent stochastic repetitions, not distinct institutional systems.
The experiment changes the optimization LossSpec, not the simulator, design space, optimizer, budget, or seeds. Narrow proxy objectives are contrasts, not normative recommendations, and the report-only protocol selects no universal winner.

## Frozen systems and own-objective generalization

| Optimization objective | Design | Proposal | Development loss | Held-out own loss (95% CI) | Generalization gap |
|---|---:|---:|---:|---:|---:|
| Participation-review | `db197e2eb5b1a` | 2 | 0.322 | 0.295 [0.229, 0.350] | -0.026 |
| Topic-entropy proxy | `d3536002463db` | 1 | -1.697 | -1.712 [-1.854, -1.563] | -0.015 |
| Review-burden proxy | `d3536002463db` | 1 | 1.669 | 1.454 [1.335, 1.585] | -0.215 |

## Institutional parameters selected by each objective

| Parameter | Participation-review | Topic-entropy proxy | Review-burden proxy |
|---|---:|---:|---:|
| acceptance_rate | 0.496777 | 0.113159 | 0.113159 |
| funding_application_cost | 1 | 1 | 1 |
| funding_budget_slots_frac | 0.390677 | 0.327413 | 0.327413 |
| resubmission_cost | 12.8905 | 16.3863 | 16.3863 |
| review_policy | persona | standardized | standardized |
| reviewer_capacity | 8 | 2 | 2 |
| reviewer_matching | topic | random | random |
| reviews_per_paper | 3 | 4 | 4 |

## Runtime and provenance

The slice covers 45 logical optimization runs, 29 physically executed optimization runs, 16 provenance-linked adopted logical runs, 15 terminal technical failures retained without numeric penalties, and 15 held-out runs. Recorded attempt runtime totals at least 52.35 hours; 1 interrupted attempt(s) lack a recoverable wall-time value. Source commit: `1078279d1ce833afe9ffb6b7c262da15357b76ab`; winner-freeze SHA-256: `254c3366e921787ad6a36776801b1cb3b278e2cb36ef247da4cb127b6459244d`.

The full cross-objective matrix, paired effects, metric uncertainty, triggered gaming diagnostics, and source-file hashes are in `metric-conditioned-paper-slice.json`.
