# Program status

Updated: 2026-10-28 05:15 JST

## Overall position

The project has a working stochastic simulation, evaluation environment, and
persistent closed-loop controller. The first commit-pinned Qwen3-8B campaign
completed all nine runs and a real result-dependent adaptive update. The first
metric-conditioned study is now executing: it changes the optimization metric,
optimizes the scientific system independently under each metric, freezes one
winner per arm, and only then compares those systems on a shared held-out
metric suite. This remains a synthetic research experiment, not a validated
science-policy result.

Repository: `/Users/shiro/unktok/dev/science-utopia-lab`

Remote: `unktok/science-utopia-lab`

## Capability map

| Layer | Status | Evidence / next gap |
|---|---|---|
| local Qwen3-8B simulation | operational | stable four-year runs through Ollama/Metal |
| repeated seeded execution | operational | registry, retry, checkpoint, provenance |
| parameter design space | partial | eight parameters; first closed loop can use this fixed topology |
| measurement | executable v1 | participation, topic spread, burden, coverage, attrition, activity, funding/resource diagnostics |
| optimization loss | three-arm study executing | participation/review, topic-entropy, and review-burden losses are frozen as experimental interventions |
| held-out evaluation metrics | executable v1 | versioned common suite, native evaluator, cross-objective analyses; real held-out runs remain |
| candidate generation | integrated foundation | random/Sobol plus generic black-box `ask/tell` API |
| closed-loop optimizer | operational | restart-safe ask/tell plus multi-loss study controller, winner seal, and held-out firewall |
| parallel campaign execution | measured | bounded workers safe; one local Ollama endpoint gives no material n=4 speedup |
| canonical event replay | integrated | deterministic sidecar and game-view payload |
| Evaluation System API | first vertical slice | one example mechanism family, not the project abstraction |
| whole-system `SystemSpec` | executable foundation | typed model, validator, generic registry/runner, canonical provenance, legacy compiler |
| structural system optimization | not started | production mechanism adapters, checkpointed graph state, and topology mutation remain |
| differentiable optimization | not started | surrogate/relaxation research remains |
| game UI | v2 vertical slice verified | fixed-grid production art, six evidence-linked flows, deterministic browser review; intervention/branching remain |

## Metric-conditioned study execution snapshot

The scientific independent variable is the optimization `LossSpec`. The
primary outcome is the resulting optimized `SystemSpec` and its held-out
behavior—not whether a metric merely separates a small set of preselected
candidates.

| Stage | Current state |
|---|---|
| frozen protocol | complete at source commit `9f9868d5bac631f6c7c373229d7807a26695a62f` |
| three initial proposals per arm | byte-identical and registered; 27 initial logical runs total |
| total optimization budget | 45 runs = 3 losses × 5 candidate systems × 3 development seeds |
| completed optimization runs | 4; all development seeds for the first candidate system plus seed 601 for the second |
| currently running | 1, participation/review arm, design `d61de1ee4e74b`, seed 617 |
| retryable failed runs | 1, design `d61de1ee4e74b`, seed 607; attempt 1 failed in year 4 and retains one checkpoint-resuming attempt |
| remaining optimization runs | 40 logical runs, including the retryable seed 607 run and later result-dependent suggestions |
| frozen arm winners | 0 of 3 |
| held-out evaluation runs | 0; seeds 701, 709, 719, 727, and 733 remain unused |

The live scheduler is intentionally single-worker. A measured four-worker
microbenchmark against one local Ollama endpoint improved throughput only
about 1.016× while increasing request latency, so local concurrency is not
being treated as a fourfold speedup.

## Completed experiment boundary

The 30% versus 50% funding-capacity experiments are repeated evaluations of two
manually chosen design points, not a parameter search. Their historical
promotion decision remains preserved, but its protected-slice veto is not a
default constraint for future optimization.

## Next milestone

Execute `Optimization v2` without consuming held-out seeds early. The
preregistered `Metric-Conditioned Optimization Study v1` will hold the
simulator, design space, optimizer, budget, and development seeds constant;
change only the `LossSpec`; then compare the frozen arm winners on one common,
untouched evaluation split. Seeds 523, 541, and 547 remain attached to the
first campaign and are forbidden in the new study.

The next execution steps are:

1. **complete:** freeze and audit the three experimental loss arms, executable
   common evaluator, analysis contract, and seed firewalls;
2. **in progress:** from the clean commit-pinned worktree, run equal-budget
   optimization after verifying byte-identical initial suggestions; objective
   resolution remains a secondary measurement-quality check rather than the
   scientific target;
3. freeze one winner per arm before consuming the new study-held-out split,
   then report a cross-evaluation matrix, rank reversals, trade-offs, gaming,
   and generalization without selecting a universal winner;
4. expand executable `SystemSpec` freedom beyond eight parameters in the fixed
   legacy topology;
5. add campaign/replay comparison to the game UI;
6. keep every model-backed run commit-pinned and separate from active
   development worktrees.

The first closed-loop result is frozen at revision `9a10029807d5`. Its untouched
held-out seeds must not be repurposed for tuning.
