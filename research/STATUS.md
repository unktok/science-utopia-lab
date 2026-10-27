# Program status

Updated: 2026-10-27

## Overall position

The project has a working stochastic simulation, evaluation environment, and
persistent closed-loop controller. The first commit-pinned Qwen3-8B campaign
has completed all nine runs and a real result-dependent adaptive update. This
is an engineering demonstration, not a validated science-policy result.

Repository: `/Users/shiro/unktok/dev/science-utopia-lab`

Remote: `unktok/science-utopia-lab`

## Capability map

| Layer | Status | Evidence / next gap |
|---|---|---|
| local Qwen3-8B simulation | operational | stable four-year runs through Ollama/Metal |
| repeated seeded execution | operational | registry, retry, checkpoint, provenance |
| parameter design space | partial | eight parameters; first closed loop can use this fixed topology |
| measurement | executable v1 | participation, topic spread, burden, coverage, attrition, activity, funding/resource diagnostics |
| optimization loss | engineering v1 executed | real closed loop complete; objective resolution is coarse and not policy-valid |
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
2. commit-pin a clean experiment worktree, verify byte-identical initial
   suggestions, then run equal-budget optimization while treating objective
   resolution as a secondary measurement-quality check rather than the
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
