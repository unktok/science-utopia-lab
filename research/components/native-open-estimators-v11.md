# Open native design and expected-loss estimator integration v11

## Purpose

Optimize freely authored scientific institutions under an explicit `LossSpec`.
Whole-world differentiability is one possible tool, not a required completion
criterion. This slice connects an expected-loss gradient estimator to the SAME
generated source/protocol/wiring/continuous design boundary as black-box
redesign, preserving the original researcher world as the forward evaluator.

This is an implementation description, not a live-Qwen result or evidence that
a generated institution or estimator improves scientific outcomes.

## Executable boundary

`NativeAdaptiveDesignCampaign` continues to accept caller-trusted generators
returning a hash-bound `GeneratedMixedDesign` definition:

```text
{base_patch, factors, continuous, provenance, optional logits}
```

The base patch and factor edits may contain arbitrary isolated Python source,
ports/contracts, nodes, wires, schedules and native process edits. They are not
choices from a host-authored institution catalogue. Each continuous coordinate
declares `{id,path,lower,upper,mean,sigma}`. The sampler draws independent
Gaussian latents, then maps them through fixed logistic bounds. Discrete factors
may have explicit conditional support. All declared assignments are preflighted;
invalid outcomes are never removed from the sampling distribution.

The original `Simulation` executes the resulting `SystemSpec`; actual native
measurements are evaluated by the unchanged caller loss. No fairness, merit,
novelty or promotion veto is added. Researcher LLM weights are fixed, not their
responses. No generated code executes as a host function.

## New estimator configuration

The backward-compatible default remains the v7 independent leave-one-out score
update, with byte-identical old campaign binding fields. An optional constructor
setting enables the new kernel:

```python
expectation_estimator={
    'name': 'frozen-prior-control-variate-v11',
    'ridge': 1e-6,
}
```

This option is valid only for score/hybrid mode. The v11 pilot uses score mode
and a single external designer strategy, so an outer strategy-selection
heuristic is not confounded with the within-vocabulary estimator.

The actual expected-loss estimate is opaque native loss times the exact
conditional design score. After compatible prior observations exist, a frozen
prior-only fitted polynomial/joint-assignment control is subtracted and its
exact expectation derivative is added back. The first batch has no such model
and explicitly records a plain-LR fallback. Plain LR and independent LOO
comparators are recorded on the same observed draws without additional worlds.

See [kernel assumptions and primary references](native-expectation-gradient-estimators-v11.md).
This is neither LLM/world/source pathwise differentiation nor an implementation
of Total Propagation X. A poor control can increase variance. Two new native
samples per batch do not establish variance reduction or estimator superiority.

## Prior provenance and semantic compatibility

Only completed valid observations in the SAME arm's preceding request history
may train the control. Current batch/sample IDs must be disjoint from prior fit
IDs. No future or other-arm outcomes are loaded. Technical failures are not
numeric targets; a failed current batch receives no policy update, numeric
penalty, filtered replacement draw or retry-for-improvement.

`expectation_compatibility` deliberately requires identical:

- Executable source, base graph/state, protocols, wires and schedules.
- Factor IDs, complete choices/operations, conditional supports and provenance.
- Continuous coordinate IDs/order, paths, bounds and fixed Gaussian scales.

Only logits, Gaussian means and base values overwritten by declared continuous
draws may differ. Generation remains free to invent new source/structure, but
such a semantic change resets this fitted control to plain LR; there is no
guessed dimension transport. The independent generation/conditional-design
scope remains explicit: unknown probabilities of externally authored source are
not differentiated.

Requests, definitions and samples are saved BEFORE execution. Model parameters,
prior/current sample IDs, compatibility identity, scores, correction terms,
sample gradients and updated weights are retained. Campaign restart recompiles
the proposals, refits from immutable preceding native records and exactly
recomputes the report. Report tampering is rejected.

## Bounded actual-Qwen pilot driver

`scripts/run_native_open_estimators_v11.py` fixes:

- One existing native net-reviewed-utility loss, not a new quality construct.
- Black-box external redesign versus the new score-control-variate arm.
- Two generated vocabularies × two conditional IID draws × two arms: at most
  eight worlds, no success-conditioned additions.
- Original five researchers, two native years, four-year original paper corpus,
  seed 42 and fixed local Qwen3:8B weights. No population/seed/horizon scale-up.
- Separate physical trajectories and own-arm histories; no shared-prefix claim.
- External request-bound, self-reported Codex source author; not Qwen invention.

The CLI requires `--output`, `--data-cache`, `--inference-lock` and the exact
`--loss research/objectives/losses/native-joint-v5-net-reviewed-utility.json`.
It rejects dirty source worktrees and competing output writers. Missing external
manifests are durable waits; unexpected errors are not objective penalties.
Any completed batch with a technical or estimator failure stops the pilot before
further batches/arms execute, including on reopening. The already executed batch
is retained and no replacement native attempts are authorized automatically.

The black-box arm is honestly labeled loss-conditioned external redesign, not
Bayesian optimization or a statistically superior method. Source freedom and
the estimator's conditional sampling scope are separate objects.

## Software QA

The v11 integration test runs four original six-year native worlds with scripted
corpus/retrieval/LLM transport and actual isolated code/protocol/wiring execution.
It stops after one committed native draw, reopens without calling the generator
again, then verifies plain LR → prior-only control fitting on two disjoint
native observations, actual research/publication phases and native review
measurements, exact cold-restart report reproduction and tamper rejection.

This scripted fixture is software QA, not local-Qwen behavior or scientific
evidence. Its six-year fixture horizon is not the two-year actual pilot horizon.
