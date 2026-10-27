# Program status

Updated: 2026-10-27

## Overall position

The project has a working stochastic simulation and evaluation environment, but
does not yet have a complete closed-loop optimizer. Two parameter points have
been repeatedly evaluated; the eight-dimensional design space has not yet been
searched.

Repository: `/Users/shiro/unktok/dev/science-utopia-lab`

Remote: `unktok/science-utopia-lab`

## Capability map

| Layer | Status | Evidence / next gap |
|---|---|---|
| local Qwen3-8B simulation | operational | stable four-year runs through Ollama/Metal |
| repeated seeded execution | operational | registry, retry, checkpoint, provenance |
| parameter design space | partial | eight parameters; first closed loop can use this fixed topology |
| measurement | partial | participation, review burden, topic spread, funding/activity shadows |
| optimization loss | not frozen | new `LossSpec` required before search |
| held-out evaluation metrics | contract defined | executable campaign-specific specs remain |
| candidate generation | integrated foundation | random/Sobol plus generic black-box `ask/tell` API |
| closed-loop optimizer | partial | result-dependent `SystemSpec` proposal works; production simulator controller missing |
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

Complete `Optimization v1`:

1. define one versioned `LossSpec` on optimization seeds;
2. declare separate held-out evaluation metrics;
3. **complete:** integrate bounded workers and benchmark the local endpoint;
4. run an initial multi-design sample;
5. **complete at API level:** feed observations into result-dependent `ask/tell`;
6. connect persistent campaign execution and demonstrate one real proposal update.

This milestone may begin with parameters of the legacy fixed topology for a
small end-to-end proof. Its optimizer boundary must accept a design object that
can later become a whole-system `SystemSpec`; optimizing the evaluation
subsystem alone is not the research endpoint.
