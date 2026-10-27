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
| measurement | partial | participation, review burden, topic spread, funding/activity shadows |
| optimization loss | engineering v1 executed | real closed loop complete; objective resolution is coarse and not policy-valid |
| held-out evaluation metrics | contract defined | executable campaign-specific specs remain |
| candidate generation | integrated foundation | random/Sobol plus generic black-box `ask/tell` API |
| closed-loop optimizer | operational | 3 suggestions × 3 seeds completed; restart-safe result-dependent update verified |
| parallel campaign execution | measured | bounded workers safe; one local Ollama endpoint gives no material n=4 speedup |
| canonical event replay | integrated | deterministic sidecar and game-view payload |
| Evaluation System API | first vertical slice | one example mechanism family, not the project abstraction |
| whole-system `SystemSpec` | integrated foundation | typed model, validator, fingerprint, legacy compiler |
| structural system optimization | not started | general graph runtime and topology mutation remain |
| differentiable optimization | not started | surrogate/relaxation research remains |
| game UI | first vertical slice | local pixel-art replay viewer; intervention/branching remain |

## Completed experiment boundary

The 30% versus 50% funding-capacity experiments are repeated evaluations of two
manually chosen design points, not a parameter search. Their historical
promotion decision remains preserved, but its protected-slice veto is not a
default constraint for future optimization.

## Next milestone

Design `Optimization v2` without consuming held-out seeds:

1. justify a research objective from science-of-science evidence and keep it
   separate from held-out evaluation metrics;
2. measure whether the objective resolves meaningful differences at affordable
   simulator fidelities;
3. expand executable `SystemSpec` freedom beyond eight parameters in the fixed
   legacy topology;
4. add campaign/replay comparison to the game UI;
5. preregister a new search budget, seed partition, optimizer, and stopping
   rule before model-backed execution.

The first closed-loop result is frozen at revision `9a10029807d5`. Its untouched
held-out seeds must not be repurposed for tuning.
