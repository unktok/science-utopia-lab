# System Optimization Continuum v1

Status: synthetic-tested common boundary; model-backed outer integration pending

Decision: [0022](../../decisions/0022-two-axis-system-optimization-continuum.md)

## The map

The progression the project wants is visible only after separating two axes.
The rows increase what may change; the columns change how candidates are
found.

| Design freedom | Manual / grid | Gradient-free black box | Differentiable surrogate | Hybrid |
|---|---:|---:|---:|---:|
| fixed graph, parameters | existing foundations | executable common slice | executable common slice | executable common slice |
| mechanism implementations | finite enumeration possible | executable common slice | executable common slice | executable common slice |
| node and edge structure | discrete grammar exists | executable common slice | executable common slice | executable common slice |
| schedules / latency | discrete grammar exists | separate structural slice | not yet in common relaxation | not yet |
| open-ended typed system | not meaningful at scale | future graph/program synthesis | future learned generator | future |

"Executable common slice" currently means synthetic development execution on
one six-family template. It does not mean model-backed completion.

## Nested design freedoms

```text
parameters
  subset of mechanism configuration
    subset of graph structure
      subset of future open-ended system synthesis
```

The same initial template, surrogate, projection rule, `LossSpec`, scenarios,
and outer evaluator are retained while the mutable mask expands. This makes
the comparison interpretable: increasing freedom does not silently replace
the entire experiment contract.

The current graph template spans research, evaluation, publication, funding,
governance, and communication. Graph freedom changes mechanism presence and
typed edge presence in addition to continuous parameters and implementation
choices.

## Search methods

### Gradient-free black box

`AdaptiveRandomSearch` sees only bounded raw coordinates and returned scalar
losses. It neither calls the surrogate nor reads gradients. After each
proposal, the common projector creates a discrete `SystemSpec`; only the outer
loss is returned through `tell`. Later proposals record the observation that
they depend on.

### Differentiable surrogate

The analytic development surrogate returns gradients over relaxed features.
The pullback converts them to raw logits and normalized parameters. A freedom
mask makes gradients exactly zero for frozen variables. The optimized relaxed
vector is projected once and evaluated by the same outer evaluator used by
black-box search.

This is a differentiable **proposal mechanism**, not a differentiable claim
about the simulator.

### Hybrid

The hybrid first obtains a gradient proposal, then centers a local
result-dependent black-box episode on that raw vector. Its first discrete
candidate and every subsequent mutation still cross the common projector and
outer evaluator. This is the likely practical architecture when the simulator
is expensive and non-differentiable.

## Small deterministic probe

With eight gradient steps and four black-box outer evaluations per freedom
level, the regression fixture produced:

| Freedom | Mutable raw variables | Black-box best outer loss | Gradient projected outer loss |
|---|---:|---:|---:|
| parameters | 6 | 1.133806 | 1.133800 |
| mechanism configuration | 16 | 1.133806 | 1.133800 |
| graph structure | 26 | 0.111956 | 0.000056 |

A three-evaluation structural hybrid retained outer loss `0.000056`. These
numbers describe a hand-constructed synthetic surface and are regression
evidence only. They must not be interpreted as optimizer rankings or science
policy results. In particular, the gradient was given the analytic surface
that generated the fixture; an equal-budget learned-surrogate comparison has
not been run.

## Evidence contract

Each projected evaluation records:

- both optimization coordinates;
- source relaxed vector;
- deterministic projection decisions;
- complete discrete `SystemSpec` and fingerprint;
- proposal lineage;
- outer status, loss, scenarios, and objective binding returned by the opaque
  evaluator.

Technical failure remains a status rather than a fabricated loss. Held-out
metrics and promotion policy remain outside this development boundary.

## Next integration steps

1. Express schedule/latency choices in the common relaxation and projection.
2. Freeze a smaller executable production grammar shared by both proposal
   paths.
3. Replace the synthetic outer evaluator with the compact model-backed
   simulator while preserving this API.
4. Fit or update a surrogate only from declared development observations.
5. Run equal outer-evaluation budgets for black-box, gradient, and hybrid
   methods at each fixed freedom level.
6. Publish the two-axis path, projections, graph differences, and world events
   to the game observatory.

## Reproduce

```bash
CUDA_VISIBLE_DEVICES='' PYTHONHASHSEED=42 \
  .venv/bin/python -m pytest -q \
  tests/optimization/test_continuum.py \
  tests/optimization/test_differentiable_system.py \
  tests/optimization/test_blackbox.py
```

