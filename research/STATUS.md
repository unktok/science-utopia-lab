# Program status

Updated: 2026-10-27

## Overall position

The project has a working stochastic simulation and evaluation environment, but
does not yet have a complete closed-loop optimizer. Two parameter points have
been repeatedly evaluated; the eight-dimensional design space has not yet been
searched.

## Capability map

| Layer | Status | Evidence / next gap |
|---|---|---|
| local Qwen3-8B simulation | operational | stable four-year runs through Ollama/Metal |
| repeated seeded execution | operational | registry, retry, checkpoint, provenance |
| parameter design space | partial | eight parameters; no structural mechanism search |
| measurement | partial | participation, review burden, topic spread, funding/activity shadows |
| optimization loss | not frozen | new `LossSpec` required before search |
| held-out evaluation metrics | needs separation | current documents conflate metrics and objectives |
| candidate generation | partial | random and Sobol sampling exist |
| closed-loop optimizer | not implemented | no `suggest → simulate → observe → suggest` loop |
| parallel campaign execution | integrated | bounded workers and orphan-writer leases; benchmark workers 1/2/4 |
| canonical event replay | integrated | deterministic sidecar fixture; connect future UI consumers |
| Evaluation System API | integrated foundation | auditable interface; shadow-mode simulator integration remains |
| structural system optimization | design stage | typed mechanism graph not implemented |
| differentiable optimization | not started | surrogate/relaxation research remains |
| game UI | design stage | canonical replay is the prerequisite |

## Completed experiment boundary

The 30% versus 50% funding-capacity experiments are repeated evaluations of two
manually chosen design points, not a parameter search. Their historical
promotion decision remains preserved, but its protected-slice veto is not a
default constraint for future optimization.

## Next milestone

Complete `Optimization v1`:

1. define one versioned `LossSpec` on optimization seeds;
2. declare separate held-out evaluation metrics;
3. integrate and benchmark bounded campaign workers;
4. run an initial multi-design sample;
5. feed observations into an optimizer interface;
6. demonstrate at least one full closed-loop proposal update.
