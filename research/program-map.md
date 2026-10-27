# Science Utopia Lab — program map

Updated: 2026-10-28

![Science Utopia Lab program map](figures/science-utopia-program-map.png)

Editable source: [`science-utopia-program-map.svg`](figures/science-utopia-program-map.svg).

## What this project is trying to do

Treat a complete scientific system as a design object. Evaluation, publication,
funding, governance, communication, and other mechanisms may be added, removed,
replaced, parameterized, or eventually rewired. Run candidate systems as
stochastic simulations and study which institutions emerge as desirable under
different explicitly chosen objectives.

The central experiment is **metric-conditioned system optimization**:

```text
choose optimization metric A -> optimize the system -> freeze system A*
choose optimization metric B -> optimize the system -> freeze system B*
choose optimization metric C -> optimize the system -> freeze system C*
                                              |
                                              v
                 evaluate A*, B*, C* on the same held-out metric suite
```

Here, an optimization metric (`LossSpec`) is analogous to a training loss: it
changes which system the optimizer searches for. A held-out evaluation metric
(`EvaluationMetricSpec`) is analogous to accuracy, F1, calibration, or a test
set diagnostic: it is used after candidates are frozen to understand what each
objective produced. Technical validity and an optional policy decision are
separate again. Objective resolution is useful QA, but it is not the research
question by itself.

Accordingly, the central comparison is a matrix: rows are systems obtained by
optimizing different losses, while columns are shared held-out evaluation
metrics. A result such as “loss A produced system A*, which scores this way on
metrics A/B/C” is the intended evidence. Testing whether loss A can reliably
distinguish two already chosen systems is only supporting measurement QA.

## Current tracks

| Track | Current state | What is actually finished | Next evidence-producing step |
|---|---|---|---|
| Reproducible simulator | operational | local Qwen3-8B, repeated seeds, restart/provenance, longitudinal runs | keep frozen during metric-conditioned study |
| Metric-conditioned optimization | executing from frozen worktree | three alternative-loss arms, identical initial proposals, study controller, winner seal, seed firewall; 4/45 optimization runs complete and 1 running at the 2026-10-28 04:26 JST snapshot | finish all arms, freeze three winners simultaneously, then run held-out cross-evaluation |
| Evaluation metrics | executable common suite | participation, entropy, burden, coverage, attrition, activity, funding/resource ledger plus rank/trade-off/gaming/generalization analyses | run the untouched split and produce cross-objective result graphics |
| Whole-system abstraction | executable foundation implemented | typed `SystemSpec`, validator, generic implementation registry/runner, canonical provenance, legacy compiler | checkpointable state and production adapters for interchangeable mechanisms |
| Black-box optimization | baseline operational | opaque `ask/tell`, persistent adaptive random search, real result-dependent suggestion | compare stronger methods only after the multi-loss baseline closes |
| Structural optimization | not started | graph objects can describe broader systems, but the simulator cannot execute arbitrary topology | topology mutation after the general runner exists |
| Differentiable systems | not started | conceptual direction only | differentiable surrogate/relaxation after stable black-box targets and measurements |
| Game and replay | v2 vertical slice verified | replay v2, Phaser renderer, 13 fixed-grid production assets, evidence drill-down, deterministic screenshots | increase environmental density and animation, then add intervention branching |
| Paper and scientific graphics | working draft | seven-page NeurIPS-style PDF and initial figures | add program diagram and metric-conditioned result figures after data exists |
| Compute | measured | one local Ollama endpoint at four workers gave only about 1.016x throughput | use independent endpoints/GPUs for material parallel speedup; retain seed isolation |

## Dependency logic

The project is deliberately not a single linear backlog.

- The research core now moves from an engineering closed loop to the first
  comparison of **systems optimized under different objectives**.
- The system-abstraction track now executes small family-independent mechanism
  graphs. It next expands from examples to checkpointable production adapters,
  so the optimizer may change mechanisms and graph structure rather than only
  eight parameters in one topology.
- The game track consumes canonical replay; it does not reimplement research
  logic. It can progress while commit-pinned experiments run elsewhere.
- The paper/graphics track records claims only after their evidence boundary is
  clear, but can continuously improve explanatory diagrams and methods text.
- Differentiable optimization is downstream of a trustworthy simulator target
  and held-out evaluation suite; otherwise it would optimize an undefined
  proxy faster.

## Immediate milestone

Complete `Metric-Conditioned Optimization Study v1` without consuming its
held-out worlds early:

1. **complete:** freeze three contrasting proxy objectives, identical search
   conditions, common evaluation suite, and analysis code;
2. **in progress:** run equal-budget black-box optimization for each objective
   from the clean commit-pinned worktree;
3. freeze one winner per arm before opening the evaluation split;
4. cross-evaluate all winners on the same metrics and visualize rank reversals,
   trade-offs, generalization gaps, and proxy gaming;
5. report what changed in the optimized systems—without declaring one metric or
   system universally correct.

In parallel, expand the verified game v2 slice and turn the generic mechanism
runner into checkpointable production adapters. Long model campaigns must run
from a clean commit-pinned worktree, separate from active game and abstraction
development.

