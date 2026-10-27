# Program status

Updated: 2026-10-27

## Overall position

The project has a working stochastic simulation, evaluation environment, and
persistent closed-loop controller. The controller has completed an automated
result-dependent loop against deterministic test observations; the first
commit-pinned Qwen3-8B campaign has not yet completed.

Repository: `/Users/shiro/unktok/dev/science-utopia-lab`

Remote: `unktok/science-utopia-lab`

## Capability map

| Layer | Status | Evidence / next gap |
|---|---|---|
| local Qwen3-8B simulation | operational | stable four-year runs through Ollama/Metal |
| repeated seeded execution | operational | registry, retry, checkpoint, provenance |
| parameter design space | partial | eight parameters; first closed loop can use this fixed topology |
| measurement | partial | participation, review burden, topic spread, funding/activity shadows |
| optimization loss | engineering v1 frozen | executable demo loss; not a validated scientific-value construct |
| held-out evaluation metrics | contract defined | executable campaign-specific specs remain |
| candidate generation | integrated foundation | random/Sobol plus generic black-box `ask/tell` API |
| closed-loop optimizer | implemented, campaign pending | persistent ask/register/run/observe/tell; real Qwen3-8B result pending |
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

Complete `Optimization v1` execution:

1. **complete:** define one versioned engineering `LossSpec` on optimization seeds;
2. declare separate held-out evaluation metrics;
3. **complete:** integrate bounded workers and benchmark the local endpoint;
4. run the two-design, three-seed initial batch from a clean protocol tag;
5. **complete at API level:** feed observations into result-dependent `ask/tell`;
6. **complete in deterministic integration:** persist the campaign and verify a
   result-dependent third proposal;
7. complete the same update using real simulator outputs, then freeze the
   engineering result without making a science-policy claim.

This milestone may begin with parameters of the legacy fixed topology for a
small end-to-end proof. Its optimizer boundary must accept a design object that
can later become a whole-system `SystemSpec`; optimizing the evaluation
subsystem alone is not the research endpoint.
