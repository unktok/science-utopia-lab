# Research index

This is the canonical entry point for the Science Utopia research program.
Existing documents keep their paths because they are cited by frozen protocols
and results. New work uses the forward-only taxonomy below.

## Current state

- [Program status](STATUS.md)
- [Program map: goals, dependencies, and parallel tracks](program-map.md)
- [Research overview](../RESEARCH.md)
- [Roadmap](roadmap.md)
- [Research charter](charter.md)
- [Closed-loop optimization contract](objectives/losses/closed-loop-v1.md)
- [Future objective catalog v1](objectives/catalog/objective-catalog-v1.md)
- [Metric / Objective Landscape v1](objectives/landscape/metric-objective-landscape-v1.md)
- [Objective Constitution / LossSpec compiler v1](objectives/constitutions/objective-constitution-compiler-v1.md)
- [Differentiable whole-system surrogate v0](optimizers/methods/differentiable-system-design-surrogate-v0.md)
- [Whole-system graph foundation](components/system-spec-graph-v1.md)
- [Generic mechanism graph runtime](components/mechanism-graph-runtime-v1.md)
- [Heterogeneous production mechanism graph](components/heterogeneous-production-graph-v1.md)
- [Production structural optimization](components/production-structural-optimization-v1.md)
- [Stateful government policy mechanism](components/stateful-government-policy-v1.md)
- [Communication and knowledge diffusion mechanism](components/communication-knowledge-diffusion-v1.md)
- [Simulator-backed workload bridge](components/simulator-workload-bridge-v1.md)
- [SystemSpec-to-simulator experiment plan compiler](components/system-spec-simulator-experiment-plan-v1.md)
- [Native prospective communication broker](components/native-communication-broker-v1.md)
- [Native government policy runtime](components/native-government-policy-runtime-v1.md)
- [Black-box ask/tell boundary](optimizers/blackbox-ask-tell-v1.md)
- [First closed-loop engineering protocol](protocols/campaigns/first-closed-loop-engineering-v1.md)
- [First closed-loop engineering result](results/first-closed-loop-engineering-v1-interpretation.md)
- [Metric-conditioned optimization v1 preregistration](protocols/campaigns/metric-conditioned-optimization-v1.md)
- [Metric-conditioned optimization v1.1 repair/reuse amendment](protocols/campaigns/metric-conditioned-optimization-v1-1.md)
- [Metric-conditioned v1.1 artifact-reuse implementation contract](protocols/campaigns/metric-conditioned-optimization-v1.1-reuse.md)
- [Metric-conditioned v1.1 optimization result](results/metric-conditioned-optimization-v1-1.json)
- [Metric-conditioned v1 zero-query failure audit](audits/metric-conditioned-v1-zero-query-failure.md)
- [Metric-conditioned held-out metric suite](metrics/metric-conditioned-held-out-suite-v1.json)
- [Report-only semantic instrumentation v1](metrics/semantic-instrumentation-v1.md)
- [Prospective semantic recorder/checkpoint v1](metrics/prospective-semantic-recorder-v1.md)
- [Metric-conditioned results graphics pipeline](decisions/0009-metric-conditioned-results-graphics-pipeline.md)
- [Metric-conditioned automatic paper slice](decisions/0010-metric-conditioned-automatic-paper-slice.md)
- [Pre-held-out optimization completion analysis](decisions/0012-pre-held-out-optimization-completion-analysis.md)
- [Optimization completion analysis runbook](protocols/campaigns/metric-conditioned-optimization-completion-analysis-v1.md)
- [Post-optimization cross-objective runbook](protocols/campaigns/metric-conditioned-post-optimization-comparison-v1.md)
- [Objective catalog v1 decision](decisions/0011-objective-catalog-v1.md)
- [Semantic instrumentation decision](decisions/0013-report-only-semantic-instrumentation.md)
- [Prospective semantic recorder decision](decisions/0014-prospective-semantic-recorder-checkpoint.md)
- [Post-optimization cross-objective decision](decisions/0015-post-optimization-cross-objective-comparison.md)
- [Metric / Objective Landscape decision](decisions/0016-metric-objective-landscape-v1.md)
- [Objective Constitution compiler decision](decisions/0017-objective-constitution-compiler-v1.md)
- [Differentiable whole-system surrogate decision](decisions/0018-differentiable-system-design-surrogate-v0.md)
- [Native government policy runtime decision](decisions/0019-native-government-policy-runtime.md)
- [First closed-loop artifact manifest](artifacts/first-closed-loop-engineering-v1.manifest.json)
- [Milestone 3: first real result-dependent closed loop](milestones/2026-10-27-first-closed-loop-engineering.md)
- [Parallel benchmark](optimizers/compute/parallel-benchmark-v1.md)
- [Held-out progress monitor v1](optimizers/compute/held-out-progress-monitor-v1.md)
- [Game UI vertical slice](tracks/game-ui-slice.md)
- [Game UI v2 creative direction](tracks/game-ui-v2-creative-direction.md)
- [Game UI v3 evidence-driven vertical slice](tracks/game-ui-v3-vertical-slice.md)
- [Game UI intervention branch comparison](tracks/game-ui-branch-comparison-v1.md)
- [Game UI v4 spatial activity](tracks/game-ui-v4-spatial-activity.md)
- [Game UI verified real-campaign adapter](tracks/game-ui-real-campaign-adapter-v1.md)

## Conceptual objects

| Object | Meaning | New location |
|---|---|---|
| `SystemSpec` | complete science-system graph being designed | `components/` and `objectives/design-spaces/` |
| loss / objective | quantity directly optimized on search worlds | `objectives/losses/` |
| design space | parameters or structures the optimizer may change | `objectives/design-spaces/` |
| evaluation metric | held-out measurement used to understand a frozen candidate | `metrics/` |
| optimizer method | grid, random, Sobol, Bayesian, evolutionary, gradient, etc. | `optimizers/methods/` |
| protocol | plan frozen before a campaign | `protocols/campaigns/` |
| run | one concrete design × seed execution | `runs/` |
| result | aggregation and interpretation across runs | `results/` |
| artifact manifest | hashes and current raw-output locator | `artifacts/` |
| decision | durable architecture or governance choice | `decisions/` |
| logbook | chronological working record | `logbook/` |

## Forward-only taxonomy

```text
research/
  objectives/
    losses/
    design-spaces/
    constitutions/
  metrics/
  optimizers/
    methods/
    harness/
    compute/
  components/
  protocols/
    campaigns/
    templates/
  runs/
  results/
  artifacts/
  decisions/
  logbook/
  literature/
  milestones/
```

Historical documents are indexed rather than moved immediately:

- [`optimization.md`](optimization.md): early optimization framing
- [`metric-constitution-v1.md`](metric-constitution-v1.md): historical
  governance experiment, not the default optimizer contract
- [`metric-cards-v0.md`](metric-cards-v0.md): initial measurement cards
- [`design-space-v0.md`](design-space-v0.md): initial parameter inventory
- [`harness.md`](harness.md): seed-replicated execution harness
- [`confirmation-comparison-v1.md`](confirmation-comparison-v1.md): frozen
  historical promotion policy
- [`compute-and-parallelization-plan.md`](compute-and-parallelization-plan.md):
  measured runtime and hardware planning

## Record rules

- Do not use an evaluation metric to tune a candidate and still call it held-out.
- Technical invalidity means an observation cannot be used; a poor simulated
  outcome is still a valid observation.
- A protected slice is reported by default. It becomes a veto only when an
  explicit versioned constraint or promotion policy says so.
- Generated reports use `.generated.md`; human interpretation uses a separate
  file.
- Closed campaigns retain immutable paths and hashes. Relocation is recorded as
  a new locator rather than rewriting historical manifests.
