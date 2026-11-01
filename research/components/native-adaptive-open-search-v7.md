# Continuing mixed open-design generation v7

`utopia.optimization.native_adaptive_search` connects **continued arbitrary
institution authoring** to actual native-world losses and subsequent designer
strategy selection. It does not replace the researcher world with numeric rules,
train researcher LLM weights, or execute generated Python on the research host.
The caller retains the same `LocalQwenNativeFactory`/native Simulation interface.
There is no implicit fairness, merit, participation, quality or promotion veto.

## Integration API

```python
campaign = NativeAdaptiveDesignCampaign(
    output_directory,
    initial_system=system,
    loss_spec=declared_loss,
    seeds=[development_seed],
    world_binding={"source_commit": source_pin, "model_digest": model_digest,
                   "corpus_sha256": corpus_digest, "years": horizon},
    strategies={"invent": {"implementation_sha256": inventor_source_hash},
                "revise": {"implementation_sha256": reviser_source_hash}},
    mode="hybrid",  # or "blackbox", "score"
    seed=42,
)
record = campaign.advance(
    simulation_factory=native_factory,
    generators={"invent": inventor, "revise": reviser},
    count=2,
)
```

Each caller-provided, **trusted** generator takes one complete JSON request and
returns:

```text
{
  base_patch: complete SystemSpec patch or null,
  factors: arbitrary NativeFactorizedDesignSearch edit factors (possibly []),
  continuous: [{id, path, lower, upper, mean, sigma}, ...],
  provenance: nonempty explicit author/source/version object,
  logits: optional complete per-factor initial logits
}
```

`base_patch` and factor choices can contain new Python bodies, algorithms,
producers/consumers, new protocols, nodes, explicit edges and schedules. The host
does not choose a new institution, fill a missing wire, repair an algorithm, or
limit generated code to a built-in rule catalogue. The next generator is invoked
again after actual outcomes, not only asked to pick from the first vocabulary.
Every returned vocabulary has an immutable version hash binding its entire
definition, exact generation request, source/provenance and preceding history.
Options may be added, removed or rewritten in a NEW version; old versions are
never rewritten. No semantic novelty is inferred from a new hash or option ID.

Requests include the explicit loss/world binding, actual observations (including
failed attempts), incumbent SystemSpec, all prior generated vocabularies/source,
sampled assignments/latent values, policy reports, selected designer identity
and current strategy state. They expose no unobserved future outcomes.
`PatchProposerGenerator` adapts existing four-argument native patch proposers;
its optional definition builder can author mixed factors/coordinates.
`InboxVocabularyGenerator` uses the existing exact-request `ManifestInbox` and
external authoring receipts. Generator provenance/identity is self-reported, not
provider authentication. Arbitrary *generated* host functions are never imported
or evaluated; installing a trusted generator remains caller authorization.

## Mixed optimization and designer strategy feedback

For each version, conditional discrete edits reuse the v6 factorized compiler.
Every reachable discrete combination is statically preflighted; invalid grammar
rejects the WHOLE vocabulary rather than dropping probability mass. Factor count
and vocabulary sizes can change between versions. Enumeration retains the v6
explicit finite preflight cap (4096), not an exhaustive open-ended grammar.

Continuous coordinates explicitly name existing finite numeric fields in every
reachable structure. Independent Gaussian latent samples pass through the fixed
transform `lower + (upper-lower)*sigmoid(z)`; bounds, mean and sigma are caller
design choices, not host-imposed merit thresholds. Floating-point saturation can
map different latents to the same endpoint; the original latent and its Gaussian
likelihood are kept, never post-hoc remapped or assigned an inverse density.
Sigma is fixed within one version. Integer-only or otherwise invalid transformed
fields fail technically, with null loss; there is no rounding/repair/resampling.

- `blackbox`: sample mixed designs and feed actual losses back into ongoing
  generation; update designer selection towards negative empirical mean costs.
  This explicit exploration/selection heuristic does not claim a gradient.
- `score`: native costs update conditional categorical/Bernoulli logits and
  Gaussian means through exact latent log likelihoods and an independent
  leave-one-out baseline. A separate fixed-baseline strategy score updates
  designer-selection logits.
- `hybrid`: apply the score components plus the explicit black-box strategy
  heuristic. Their combination is a heuristic, not an unbiased full optimizer
  derivative or a guarantee of better institutions.

The strategy is sampled **once per batch**; conditional design draws are IID.
The batch likelihood is `log q(strategy) + sum(log q(discrete_i,z_i | version))`,
not one strategy likelihood per draw. Continuous/discrete inner advantages use
other IID conditional draws; the shared-strategy outer score uses an independent
fixed baseline, not that dependent leave-one-out baseline. Equal inner costs
produce exactly zero inner score updates. The outer fixed-baseline score may
still have finite-sample noise: it is not evidence that designers differ.

The likelihood is conditional on the externally generated vocabulary. Unknown
probabilities of source invention are not included, and a generator's direct
dependence on exposed strategy weights/history is not differentiated. These are
current-vocabulary score components, NOT pathwise derivatives of source text,
arbitrary Python, researcher token generation or the whole native world.
Learned means/logits are supplied to the next generator. Reusing them across a
changed vocabulary requires explicit caller-authored dimensional transport; the
host does not silently choose corresponding options or invent missing weights.

## Durability, validity and evidence

Saved stages separate the exact request, raw vocabulary, compiled mixed draws,
each actual observation, and the completed update. A cold restart reuses already
saved definitions/draws and deterministically reconstructs all versions,
likelihoods, strategy choices and updates without calling generators. Factory
year/response checkpoints own interrupted native-run recovery. A generator crash
before its returned JSON is persisted still requires an idempotent generator or
the external inbox; it is not falsely labelled an exactly-once external call.
One writer must own the campaign directory.

Each successful native observation is bound to its actual saved checkpoint,
SystemSpec, complete horizon, event stream, source/model/corpus and replicate
seeds by the existing native verifier. Losses are recomputed from recorded
measurements. Independent scientific audit should additionally re-extract those
measurements from raw domain state; the controller is not that independent audit.
Changing settings, provenance, source/grammar, weights, sampled choices, latent
likelihoods, history or checkpoints fails reopening rather than quietly adapting.

Technical generation/compile/native failures retain their error/null evidence.
No penalty number or replacement candidate is fabricated. Any failed draw or
replicate prevents the whole mixed/strategy update; successful observations stay
visible. This does not establish an unbiased objective over runtime-undefined
designs, nor silently optimize a conditional-on-success target. Subsequent
explicit generations can observe the failure and author a different version.

Verification in `tests/optimization/test_native_adaptive_search.py` distinguishes
synthetic estimator units from actual native software QA. The latter executes
six complete six-year original Simulation worlds with scripted HTTP/corpus,
arbitrary isolated code, typed protocols, conditional edges and continuous
thresholds. It interrupts after one committed draw, cold-reopens without source
regeneration, observes actual losses, generates a larger new code vocabulary,
explicitly transports learned weights, executes the next batch and reopens its
updated designer strategy. It is not live-Qwen institutional invention, causal
benefit, held-out improvement, recursive self-modification of the optimizer's
implementation, or a solved open science-system ontology.
