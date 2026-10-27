# Black-box ask/tell optimizer boundary v1

Status: implemented foundation

## Contract

The optimizer operates on an opaque JSON design object:

```text
ask(n) -> Suggestion[SystemSpec]
dispatch Suggestion to stochastic simulator replicas
ValiditySpec accepts or rejects each observation
LossSpec aggregates accepted replicas into a finite scalar loss
tell(Observation[SystemSpec, loss])
ask(n) -> result-dependent suggestions
```

The optimizer does not import simulator internals, evaluation metrics, or a
promotion policy. It therefore supports genuinely black-box simulation,
including LLM calls, categorical rules, discrete events, and non-differentiable
mechanisms.

`SearchSpace` is the only candidate-specific adapter. `LegacySystemSpecSpace`
lifts the current eight-variable mutable subspace into nested, executable
whole-system `SystemSpec` JSON. The optimizer therefore uses the final design
object boundary even in the first restricted campaign. Future adapters can
mutate mechanism selection and graph structure without changing the optimizer
API. `LegacyParameterSpace` remains available as the flat compatibility layer.

## Baseline implementation

`AdaptiveRandomSearch` supplies a minimal auditable closed-loop baseline:

1. propose deterministic independent initial candidates;
2. accept only finite losses from technically complete observations;
3. identify the lowest-loss incumbent;
4. propose deterministic gradient-free mutations around that incumbent;
5. serialize pending suggestions, observations, and proposal state as JSON.

This is not intended to be the final search method. Bayesian optimization,
evolution strategies, CMA-ES, or learned policies can implement the same
`ask`, `tell`, and `state_dict` contract. Differentiable optimization is an
additional backend and is not required by the boundary.

## Production connection

`utopia.optimization.closed_loop` now persists each suggestion before job
dispatch, registers its optimization-seed replicas, aggregates them through the
campaign's versioned `LossSpec`, calls `tell`, and resumes optimizer state after
interruption. Held-out seeds are present in the campaign specification but are
not dispatched or consumed by this optimization controller.

The deterministic integration test proves result dependence and crash-resumable
state. The first real Qwen3-8B campaign subsequently completed three suggestions
across three optimization seeds, including one adaptive suggestion explicitly
conditioned on the lower-loss initial observation. The adaptive point tied its
parent, so the result establishes the engineering loop rather than a policy
improvement.
