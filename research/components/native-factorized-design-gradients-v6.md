# Factorized native-design score gradients v6

This adds exact **joint action-likelihood** backward for component choices in
the original researcher world. It does not differentiate native transitions,
LLM token generation, institution source synthesis or LLM weights. It does not
claim a new useful scientific institution or an empirical live-model result.

## Design object and public API

`utopia.optimization.native_factorized_gradient` provides:

- `NativeFactorizedDesignSearch(base_system, factors, *, loss_spec,
  design_provenance, seed=42, learning_rate=.1, baseline=0., logits=None,
  max_assignments=4096)` with `ask`, `tell`, `state_dict`, `from_state`,
  `compile_assignment`, and `action_log_probability`.
- `NativeFactorizedGradientCampaign(directory, search, *, loss_spec, seeds,
  world_binding)` with durable `advance(simulation_factory=..., count=...)`.

The caller supplies the **actual arbitrary edit programs**, not one of the
host's institution templates. A factor is an ordered JSON object:

```json
{
  "id": "implementation",
  "kind": "categorical",
  "choices": [
    {"id": "first", "operations": [], "provenance": {"author": "external"}},
    {"id": "second", "operations": [], "provenance": {"author": "external"}}
  ]
}
```

The empty operations above illustrate syntax only. Real choices can contain
arbitrary existing design-patch `add`/`replace`/`remove` operations, including
free Python strings, new nodes, port/payload schemas, artifact protocols,
parameters, schedules and connections. A `bernoulli` factor has exactly two
caller-named choices; it learns one scalar logit, rather than an entire-system
categorical logit. Discrete parameter values are another independent factor.
Continuous parameter distributions are not added by this module.

All selected operations are concatenated in factor order and applied as one
**atomic final transaction**. Intermediate code/protocol/port inconsistencies
are not mistaken for invalid finished designs. Source is validated, never
rewritten or executed on the host by the compiler. Execution remains subject
to the existing isolated native-code runtime.

## Explicit conditional support, not success filtering

A factor may provide `support` rules, for example:

```json
[
  {"when": {"implementation": "first"}, "allow": ["off"]},
  {"when": {"implementation": "second"}, "allow": ["off", "on"]}
]
```

Each reachable prefix must match exactly one rule; rules may reference only
earlier factor choices. No rule means all choices are allowed. These are
explicit externally supplied grammar conditions, not a hidden acceptance,
fairness, quality, participation or promotion filter. The implementation
enumerates the reachable grammar for static technical preflight, subject to
the explicit support-size budget. It does **not** convert the result into a
bank of complete-SystemSpec policy actions.

If any declared combination is structurally or source-invalid, the **entire
grammar definition is rejected before sampling**. It is not silently masked,
resampled, repaired, remapped or assigned a numerical cost. A corrected grammar
is a new definition/hash, not retroactive reinterpretation of earlier samples.
Static validity cannot ensure that arbitrary programs will execute successfully.

## Exact distribution and estimator

For assignment `a`, the exact ancestral joint policy is
`q(a) = product_j q_j(a_j | a_<j, declared_support_j)`. Categorical factors use
log-softmax normalized **within that prefix's declared support**. Two-way
Bernoulli factors use stable log-sigmoid probabilities. Singleton conditional
support has probability one and exactly zero score gradient, not the score of
an unconditioned coin toss.

The update uses autograd on the mean of
`(actual_full_native_loss - independent_baseline) * log q(a)`. The baseline is
either an explicit finite constant, or `"leave-one-out"` for IID batches of at
least two draws. The latter excludes the sample's own cost; it is not the
biased same-batch mean baseline and is not used with dependent antithetic draws.

Every execution includes complete researcher activities and downstream fixed-
weight LLM responses through the ordinary native evaluator. The next `ask`
uses the updated component logits and compiles a new joint design. This learns
the distribution over **composed code/protocol/wiring/parameter choices**, not
only probabilities over a supplied bank of whole systems. It does not invent
new code strings, differentiate their contents, or produce an unseen option.
New externally invented choices require a new explicit grammar definition.

The expectation/score identity assumes a defined complete native cost for
every supported action. Any failed draw or failed declared replicate aborts
the **whole batch update**, preserving null failure losses and all successful
observations. There is no partial-success estimator or implicit
conditional-on-success objective. Undefined failed-world costs remain a
limitation, not a numerical penalty to be guessed by the optimizer.

## Provenance, aliases and uncertainty

Pending records retain the full assignment, each conditional allowed support
and log probability, exact joint log probability, atomic patch, complete
SystemSpec, draw/iteration/sampler seed and definition hash. Original source
bytes, per-choice provenance, base design, learning settings and loss hash are
bound in durable state. Sampling is regenerated exactly on restore and before
update; changed programs, RNG, assignments or likelihoods fail closed.

Different assignments may compile to the same system. The **original latent
assignment** and its joint likelihood are retained; neither is replaced by a
canonical equivalent design. Draws still have distinct suggestion/run IDs.
This many-to-one mapping is compatible with the score identity, but duplicate
designs are not independent scientific conditions or proof of comparison.

Reports expose per-draw score terms, distinct assignment/design counts, raw
costs, baselines, and equal/zero-cost flags. Equal costs provide no comparative
evidence: a fixed-baseline finite batch can nevertheless yield nonzero score
noise. Equal costs with the IID leave-one-out baseline give zero advantages
and zero update. No new-best, variance-free estimator or held-out benefit is
inferred from a nonzero gradient.

The generic ask/tell interface assumes its supplied observations are truthful.
The durable native campaign additionally replays all loss/measurement arithmetic
and exact optimizer history, and verifies successful native checkpoint hashes,
executed SystemSpec, source commit, model digest, corpus digest and declared
replicate seeds. Independent scientific reporting should still reconstruct
domain measurements from archived checkpoints.

## Verification and boundaries

Software tests use arbitrary **developer-authored** source fixtures, never a
claim of LLM invention. Twelve reachable combinations couple a categorical
consumer implementation, conditional Bernoulli edge, parameter values and a
typed producer/consumer protocol with changed source. Exact enumerated
expectation gradients agree with score autograd and central finite differences;
singleton scores, illegal support, many-to-one aliases, zero/equal costs,
sampling noise and tamper/resume behavior are tested.

An original six-year scientific-world QA runs eight complete sampled worlds
with scripted corpus/retrieval/HTTP only. Actual completed native losses drive
the factorized backward update and next-design sampling, exercising both
Bernoulli-edge states and both protocol implementations, including an
interruption after the first committed observation and an exact durable resume.
There are **no new real-Qwen inference calls** or large-scale comparisons in
this implementation task. The fixed supplied option set, explicit finite
preflight budget, discrete parameters and absent full-world pathwise derivative
remain stated limitations.
