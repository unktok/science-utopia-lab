# V9: actual fixed-Qwen responses connected to institution backpropagation

## Goal and scope

Connect the existing original ScienceUtopia world to a local, response-aware
differentiable representation, then project its gradient proposal back into the
original simulator and measure the SAME fixed loss. This is a finite integration
goal, not a claim that all pre-scale research or useful self-improvement is done.
The [protocol](../protocols/campaigns/native-qwen-response-gradient-v9.md) and
[a3 amendment](../protocols/campaigns/native-qwen-response-gradient-v9-a3.md)
fix the learning rule and conditional-history design before inference.

## What is actually connected

| Boundary | Implementation and evidence |
|---|---|
| Original world | Five original authors, two native years, seed42, the original four-year real-paper corpus and fixed Qwen3:8B; research, retrieval, submissions, review, publication and funding still execute. |
| Changeable institution | An executable review charter exposes one evidence/originality-weight coordinate after final-year submissions. Public input contains the payload, not internal lineage IDs. Other existing code/graph authoring capabilities are retained, not exercised by this one-coordinate probe. |
| Real replies to numbers | Opt-in native task receipts bind reviewer/paper/conference identities to exact prompt, cache and wire hashes. Each actual score passes the original integer parser before the paper-level average. No uniform-score assumption or invented missing response. |
| Fixed objective | Existing `native-joint-v5-net-reviewed-utility`: `L = 3.25 A - Q + 0.05 R`, with actual accepted decisions, accepted native peer-score sum and review-record count. This is an explicit engineering objective, not a scientific-welfare measure. No additional promotion veto. |
| Response-aware backward | Fit the local response operator on weights0.2/0.5/0.8 only. Autograd includes learned response, relaxed parsing and the existing tensor program. It does not backpropagate exactly through Qwen text generation or every native operation. |
| Projection and native check | Freeze the center0.5 gradient proposal before examining unused0.35/0.65 worlds, then run the projected candidate in the original world. A zero/tiny-gradient no-op is retained, not replaced by a favorable calibration sample. |

## Why there are three attempts

A1's independently regenerated histories differ before the intervention, so
their differences cannot be attributed solely to the charter. A2 corrects an
over-strict server-envelope comparison but cannot remove scientific-history
drift. Both owned runners were intentionally stopped; two completed worlds and
two partial worlds retain all228 actual replies. Missing partial losses are null.
[A1 audit](../results/native-qwen-response-v9-a1.md),
[A2 audit](../results/native-qwen-response-v9-a2.md).

A3 reuses one sealed ACTUAL pre-intervention history only on byte-identical
requests, then generates affected reviews and later replies freshly. Only
identity-checked Year1 `review_time` metadata is coupled after the original
insertion, because original Year2 prompts include those archived timestamps.
All non-time scientific fields must match. Global/transport clocks and Year2
review clocks stay live. Each full original forward still runs. Historical
replays are not new physical calls or independent replications.

## Independently audited actual result

The frozen actual source is `fb2d1b6f07aadba39148bd5871dac2fd0595b618`.
All six a3 logical worlds have executed. The frozen candidate is EXACTLY0.5:
the nonzero represented center gradient is about`1.15e-15`, whose requested
floating-point step rounds back to the center. Native candidate and center both
have loss0.9. Calibration0.8 has loss0.8166667, but the preregistered local
gradient rule does not select it. Do not relabel this as successful optimization.
All six completed endpoints are independently remeasured and their reply
identities rejoined. [Result](../results/native-qwen-response-v9-a3.md),
[machine-readable audit](../results/native-qwen-response-v9-a3.json).
All101 raw files are unchanged before/after audit, and a repeated audit produces
byte-identical results. Content SHA-256:
`92d6a9b630d9bcd44e379ec48833aed2de71490b85907068fed740361826abbf`.

| Role | Charter weight | Native loss | Accepted decisions |
|---|---:|---:|---:|
| Calibration | 0.20 | 0.900000 | 0 |
| Calibration / gradient center | 0.50 | 0.900000 | 0 |
| Calibration | 0.80 | 0.816667 | 1 |
| Unused check | 0.35 | 0.900000 | 0 |
| Unused check | 0.65 | 0.900000 | 0 |
| Frozen gradient candidate | 0.50 | 0.900000 | 0 |

Every world has18 native review records. The single accepted paper at0.8 has
native mean score3.3333333. Calibration loss RMSE selects temperature0.01 and is
only1.1562e-5, but predicted unused loss at0.65 is0.81676694 versus actual0.9
(absolute error0.08323306). The unused finite-change prediction is-0.08394601
versus actual0, failing the fixed diagnostic; frozen responses predict0 here.
Neither the failure nor the tied/no-op proposal is hidden or used to reroll.

Each world has84 logical replies, comprising53 historical replays and31 fresh
actual Qwen replies. Total504 logical =318 replays +186 new physical replies;
53 unique anchor-origin calls plus186 fresh calls support this conditional
campaign. All attempts including the preserved228 earlier calls cost414 fresh
physical replies, without double-counting the anchor. Native execution totals
about589 seconds, excluding development, calibration analysis and verification.

Clean actual-source full regression passes1718 tests/6 skipped (822.60s).
Later audit/figure/control checks have separate, overlapping scopes. Publication
verification is recorded separately; it must not be attributed to the earlier
runtime-only suite. The later final audit/figure/control suite passes55 checks.
The40-page working paper is built from committed text`65b671f`, with actual
loss/gradient/error and frozen-landscape figures. All pages are rendered and
visually reviewed; pages1/26/27/28/29/32/39 are individually enlarged and
inspected. There are no overfull boxes or undefined references; cosmetic
underfull warnings and the deliberate dedicated full-size figure page remain.
[Source/artifact verification](../results/native-qwen-response-v9-verification.json).
The owned experiment processes have exited. This completes the finite v9
integration goal, not all future non-scale research or the scientific claims
listed below.

## What this does not establish / next non-scale questions

- Six coordinates share ONE actual history; there are no held-out seeds,
  uncertainty estimates or causal scientific-policy conclusions.
- Calibration loss accuracy does not certify local derivative accuracy. A
  sharp relaxation can represent a better distant point while having an almost
  flat center. The finite path check and point gradient are separate evidence.
- No exact full-world/LLM Jacobian, expectation-level gradient, useful automatic
  institutional invention or recursively improving designer is established.
- Response identity/shape is fixed locally. Changes in participation, paper
  count, actor vocabulary or graph structure need another representation or
  estimator; a missing correspondence must fail explicitly, not be padded.
- Broader source/protocol/wiring generation and game-like UI remain the existing
  separately tested tracks. This pilot neither replaces nor newly validates
  their long-term claims. No population/seed/horizon scale-up was performed.
- A next gradient-method study should preregister how to assess gradients and
  choose useful updates, without tuning the present frozen result post hoc.

