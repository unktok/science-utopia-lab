# Program status

Updated: 2026-10-28 11:32 JST

## Overall position

The project has a working stochastic simulation, evaluation environment, and
persistent closed-loop controller. The first commit-pinned Qwen3-8B campaign
completed all nine runs and a real result-dependent adaptive update. The first
metric-conditioned study reached eight complete runs, then correctly paused
after one run exhausted its retry budget on a zero-query retrieval defect. A
minimal repair and provenance-safe initial-trajectory adoption are now tested
and integrated. Protocol v1.1 has restarted the same scientific design from
clean source commit `1078279d1ce833afe9ffb6b7c262da15357b76ab`; its first
canonical physical trajectory is running. This remains a synthetic research
experiment, not a validated science-policy result.

Repository: `/Users/shiro/unktok/dev/science-utopia-lab`

Remote: `unktok/science-utopia-lab`

## Capability map

| Layer | Status | Evidence / next gap |
|---|---|---|
| local Qwen3-8B simulation | operational | stable four-year runs through Ollama/Metal |
| repeated seeded execution | operational | registry, retry, checkpoint, provenance |
| parameter design space | partial | eight parameters; first closed loop can use this fixed topology |
| measurement | executable v1 | participation, topic spread, burden, coverage, attrition, activity, funding/resource diagnostics |
| optimization loss | v1 archived; v1.1 running | participation/review, topic-entropy, and review-burden losses remain the frozen experimental interventions |
| held-out evaluation metrics | executable v1 | versioned common suite, native evaluator, cross-objective analyses; real held-out runs remain |
| candidate generation | integrated foundation | random/Sobol plus generic black-box `ask/tell` API |
| closed-loop optimizer | operational | restart-safe ask/tell plus multi-loss study controller, winner seal, and held-out firewall |
| parallel campaign execution | measured | bounded workers safe; one local Ollama endpoint gives no material n=4 speedup |
| canonical event replay | integrated | deterministic sidecar and game-view payload |
| Evaluation System API | first vertical slice | one example mechanism family, not the project abstraction |
| whole-system `SystemSpec` | stateful government slice | typed model, validator, generic registry/runner, checkpointable evaluation/publication/funding, plus versioned event-observing government policy delivered to two families |
| structural system optimization | government production slice | 145 government candidates vary absence, implementation, observation/policy edges, and latency through one ask/loss/tell and fingerprint-bound checkpoint boundary |
| differentiable optimization | not started | surrogate/relaxation research remains |
| game UI | verified real-campaign adapter | completed seed-521 campaign is converted by Python into 71 canonical events / 72 authoritative frames after commit, manifest, integrity, completion, and artifact-hash verification; the running v1.1 study is not represented early |

## Metric-conditioned study execution snapshot

The scientific independent variable is the optimization `LossSpec`. The
primary outcome is the resulting optimized `SystemSpec` and its held-out
behavior—not whether a metric merely separates a small set of preselected
candidates.

| Stage | Current state |
|---|---|
| frozen protocol | v1 is retained at source commit `9f9868d5bac631f6c7c373229d7807a26695a62f`; active v1.1 is tagged `protocol/metric-conditioned-optimization-v1.1` at `1078279d1ce833afe9ffb6b7c262da15357b76ab` |
| three initial proposals per arm | byte-identical and registered; 27 initial logical runs total |
| total optimization budget | 45 runs = 3 losses × 5 candidate systems × 3 development seeds |
| completed optimization runs | active v1.1: 0 of 45 logical, 0 of 27 expected physical; archived v1 evidence remains 8 complete plus 1 terminal failure and is not pooled |
| currently running | 1 canonical physical run: participation/review design `d3536002463db`, seed 601, attempt 2 |
| failures / retries | active v1.1: 0 terminal failed rows and 1 preserved 240.8-second operator interruption after a missing derived RAG cache was detected; archived v1: 1 empty-query failure, repaired before the new source freeze |
| remaining optimization runs | 45 logical; with successful audited adoption of the common initial trajectories, 27 physical simulations total |
| frozen arm winners | 0 of 3 |
| held-out evaluation runs | 0; seeds 701, 709, 719, 727, and 733 remain unused |

The long-run v1.1 scheduler started at 11:04 JST and is intentionally
single-worker. Its first attempt was interrupted after detecting an avoidable
103,107-document CPU embedding rebuild. The replacement cache was admitted
only after dataset identity, ordered semantic corpus hash, tensor shape,
finiteness, and SHA-256 verification; attempt 2 started at 11:09 JST. A
measured four-worker
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
2. **in progress:** run the canonical nine initial physical simulations from
   the clean commit-pinned worktree, adopt their exact artifacts into the two
   other LossSpec arms through the audited content-addressed boundary, then
   continue each arm's two adaptive candidates; objective resolution remains a
   secondary measurement-quality check rather than the scientific target;
3. freeze one winner per arm before consuming the new study-held-out split,
   then report a cross-evaluation matrix, rank reversals, trade-offs, gaming,
   and generalization without selecting a universal winner;
4. expand executable `SystemSpec` freedom beyond eight parameters in the fixed
   legacy topology;
5. connect the hash-verified branch comparison UI to real commit-pinned campaign/replay manifests;
6. keep every model-backed run commit-pinned and separate from active
   development worktrees.

The first closed-loop result is frozen at revision `9a10029807d5`. Its untouched
held-out seeds must not be repurposed for tuning.
