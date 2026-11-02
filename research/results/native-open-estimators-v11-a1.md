# V11: open native institutions and expected-loss gradient execution

## Outcome

The bounded native pilot completed **8/8 fresh worlds**, without technical
failure, using the original fixed-Qwen researcher simulation. Both optimization
arms observed the same loss path:

```text
generation 0: [0.7833333333333337, 1.2000000000000002]
generation 1: [1.2000000000000002, 1.2000000000000002]
```

Neither arm improved on its first observed best institution. This is an
execution/integration result, not an optimization-success, superiority,
variance-reduction or scientific-quality result.

The independently regenerated [machine-readable report](native-open-estimators-v11-a1.json)
re-extracts native losses, replays both policies and the prior-only estimator,
checks actual code/wire/reply evidence, and retains every observed candidate and
every exact best-loss tie. Running the unchanged audit twice produced
byte-identical JSON. All **129 raw files** remained unchanged.

## Bound source, objective and world

- Actual experiment source: `acf3a2e4b995f8a04f4b0b56011a7051fe73a112`.
- Original native Simulation, five fixed `qwen3:8b` researchers, two native years,
  development seed42, and the original four-year real-paper corpus. No miniature
  numerical science world, researcher weight training, or scale-up was used.
- Exact existing objective: `L = 3.25 A - Q + 0.05 R`, minimized. `A` is actual
  accepted decisions, `Q` the sum of original integer-parsed accepted-paper
  reviewer mean scores, and `R` actual review records. No additional fairness,
  quality, novelty, merit or promotion veto was applied.
- Two own-history generations × two IID mixed-design draws per method.
  Generation0 definitions match except declared authorship provenance; the arms
  did not share physical simulations or response caches.
- Initial SystemSpec is not assigned an unobserved baseline score. The best
  value above is an actually evaluated generation0 draw, not a baseline claim.

## What was designed and optimized

The root integration author supplied an explicit new Python review-evidence
aggregator and Python selection consumer, with a new evaluation protocol and
explicit native wiring. The instantiated systems contain17 nodes and24 edges.
The open source/protocol/wiring interface is not restricted to these examples.
This pilot nevertheless searches a deliberately small authored vocabulary:
`mean-evidence` versus `minimum-evidence` aggregation and one bounded numeric
cutoff. It does **not** establish that an autonomous Qwen institution inventor
discovered the source or that topology was optimized during these two batches.

The numeric coordinate is a Gaussian latent with fixed sigma1, pushed through
`2.75 + 1.5 * sigmoid(z)` into the actual Python consumer's cutoff. Each draw's
raw assignment, latent, code and actual cutoff is preserved. Generation1 keeps
executable source and semantic coordinate/support meanings unchanged so the
score arm can use its own two previous observations as a frozen control
variate. Code/graph changes remain possible but would invalidate that reuse
and trigger a recorded plain-LR fallback.

| Method | Generation | Draw | Actual aggregation | Actual cutoff | Native loss |
|---|---:|---:|---|---:|---:|
| Black-box | 0 | 0 | mean | 3.583782567 | 0.783333333 |
| Black-box | 0 | 1 | mean | 3.695329426 | 1.200000000 |
| Black-box | 1 | 0 | mean | 3.874144085 | 1.200000000 |
| Black-box | 1 | 1 | minimum | 3.825174127 | 1.200000000 |
| Expected-loss gradient | 0 | 0 | mean | 3.583782567 | 0.783333333 |
| Expected-loss gradient | 0 | 1 | mean | 3.695329426 | 1.200000000 |
| Expected-loss gradient | 1 | 0 | minimum | 3.794671283 | 1.200000000 |
| Expected-loss gradient | 1 | 1 | minimum | 3.740044063 | 1.200000000 |

The first draw in each arm accepts one paper, with native accepted peer-score
sum `3.6666666666666665` and24 review records. All six other draws accept zero
papers and still have24 reviews, yielding loss1.2. Five researchers remain
active in every world. These are descriptive native measurements, not a claim
that accepting fewer or more papers measures scientific benefit.

## Which update was actually tested

The black-box arm recenters its generation1 proposal on its own observed best
latent and explicitly favors that aggregation choice. This is an externally
authored derivative-free redesign heuristic, not a named Bayesian optimizer.

The score arm's generation0 has no compatible earlier observations, so it uses
plain likelihood-ratio estimation. Its recorded gradient is
`dL/dmean = 0.40776843992307504` and aggregation-logit gradient
`[0.49583333333333346, -0.49583333333333346]`. A learning-rate0.1 update yields
mean `-0.04077684399230751` and logits
`[-0.04958333333333335, 0.04958333333333335]`. Those values are explicitly
carried into generation1; the two ensuing native worlds are the actual
forward evaluations under that updated **proposal distribution**. Their sampled
latent cutoffs need not be lower than the previous realized draws.

After generation1, the fitted-control estimator uses exactly the score arm's
two generation0 observations, not current observations, black-box outcomes,
future data or an estimated likelihood for source generation. The model has
linear/quadratic latent terms and joint-assignment indicators. Its exact
expectation correction includes both categorical logits and Gaussian mean.

| Generation1 estimator diagnostic | Gaussian-mean gradient | Aggregation-logit gradient |
|---|---:|---|
| Plain LR on these same two observations | 0.9452500525202172 | `[-0.57027435624215, 0.5702743562421501]` |
| Independent leave-one-out comparator | 0 | `[0, 0]` |
| Exact control expectation correction | 0.8220815695989002 | `[0.06930112202655483, -0.06930112202655483]` |
| Residual LR + exact correction, used update | 0.742394964214292 | `[0.10975356399749771, -0.10975356399749772]` |

The final stored mean becomes `-0.1150163404137367` and logits
`[-0.06055868973308312, 0.06055868973308312]`. **No subsequent native worlds
were sampled after this final control-variate update.** Therefore this run
verifies computation, recording and replay of that update, but not its effect
on later native performance. The generation1 native outcomes test the earlier
plain-LR-driven proposal update, not the final corrected update.

Equal generation1 losses are retained. Raw LR and frozen-control estimates may
be nonzero due to finite-sample noise, while the LOO comparator is zero here.
The two prior points do not establish an accurate quadratic response model or
reduced estimator variance. Conditional design-distribution gradients are not
full-native-world/LLM/source pathwise derivatives.

## Physical evidence and measured cost

| Item | Audited count |
|---|---:|
| Fresh native worlds | 8 |
| Physical Qwen replies | 742 |
| Logical completed-world replies | 742 |
| Replayed/shared replies | 0 |
| Actual recorded HTTP inputs | 742 |
| Black-box replies | 372 |
| Score-arm replies | 370 |
| Recorded sandbox source executions | 64 |
| Committed generated-code events | 64 |
| Completed process receipts / process invocations | 16 / 32 |
| Delivered contexts / contexts found in completed HTTP inputs | 32 / 32 |
| Transport retries / failed prompts | 0 / 0 |

The sum of each world's final checkpoint's
`portable.llm_call_stats.elapsed_seconds` is **2552.9907422065735 seconds
(42.55 minutes)**: black-box1289.7828187942505 seconds and
score-arm1263.207923412323 seconds. This is accumulated measured model-call
elapsed time, not total experiment wall time, GPU compute time, or a speedup
estimate. Setup, external-authoring waits, native CPU/container work and
analysis are not all represented by this counter. There is no audited overall
wall-clock timer in these receipts, so a precise overall duration is not claimed.

The audit checks all annual checkpoints, initialized states, actual native
source/image/context/result receipts and wire/response bindings without
executing generated source. Eight replay-critical helper/kernel/optimizer
source blobs match the actual source pin exactly. The independent audit makes
zero model calls and zero container executions.

## Immutable receipts and remaining scope

- Raw root: `outputs/native-open-estimators-v11-a1` in the main repository.
- Raw evidence-file SHA256:
  `62d40edf1595ef6ae824106674f1914b5cc56bcea27b23dcbad3c00c6dcddd03`.
- Raw129-file inventory SHA256:
  `2d711bfe55cd2e967c390790ec71bf8ea0d8c7aaff040cb34153862eb1db9d76`.
- Independent report content SHA256:
  `0d75a366dc32b8f75dab96ca32d7daa90a91c6e98db140df28bbbc21d6547426`.
- Both complete audits produced identical report bytes; raw inventories remained
  unchanged before and after each run. No source, raw checkpoint, response,
  generated institution or model was changed by this analysis.

This closes the finite small-scale native execution and independent-audit
slice. It does not close autonomous useful source invention, recursive
designer improvement, gradient variance validation, post-final-control-update
native testing, comparison across objectives or replicated method superiority.
Those empirical questions remain explicit rather than being inferred from a
successful software loop.
