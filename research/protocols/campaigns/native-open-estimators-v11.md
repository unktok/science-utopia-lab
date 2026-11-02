# V11 prospective small native open-design estimator pilot

Recorded before any v11 actual-Qwen inference on 2026-11-02. Development pilot,
not scale-up, held-out evaluation or estimator-superiority study.

## Shared native world and objective

Original native researchers, actual corpus/retrieval/project/paper/review/
publication/resource lifecycle, five authors, two years, seed42, four-year
corpus, fixed Qwen3:8B. Generated code runs only through the existing isolated
networkless executor. No privileged generated host execution, model-weight
training, new model download or paid provider.

Use exactly the existing `native-joint-v5-net-reviewed-utility` LossSpec:
`L = 3.25 A - Q + 0.05 R`, with original accepted decisions A, integer-parsed
accepted-paper reviewer-score sum Q and actual review-record count R. This
illustrative loss is not a validated measure of scientific value. No additional
quality/fairness/participation/promotion constraint or structural-novelty bonus.

## Two method arms and open design freedom

- `blackbox`: native loss feedback to the next external design generation;
  existing explicit derivative-free strategy feedback, no claimed derivative.
- `score-control-variate`: the same generated mixed-design boundary, explicit
  conditional assignment/Gaussian log likelihood, and a prior-only frozen
  tractable control variate with expectation correction. With no eligible prior
  fit, retain the declared baseline score method. Plain LR can be reconstructed
  offline on the same samples; it is not a separately executed third arm.

Each arm has two generations, two conditional IID design draws per generation:
eight new native attempts total, no success-conditioned additional budget.
Generation0 uses scientifically identical design definitions across methods;
each executes its own native trajectories, not shared independent evidence.
The first observations may differ because live Qwen execution is stochastic.
Do not infer an arm effect from those differences.

Externally authored definitions may add/rewrite arbitrary institution source,
protocols, nodes, explicit edges or processes. The researcher world is retained,
not replaced by synthetic production equations. No particular instrumented
institution ID or fixed code catalog is mandatory. Empty/identity design choices
are legal, no forced diversity. Authoring is self-reported external Codex, not
Qwen invention or authenticated independent authorship.

The disclosed optional pilot authoring example is
`scripts/author_native_open_estimators_v11.py`, not the generic search space or
an autonomous source-invention model. It explicitly replaces the existing
feature/tensor/router chain with a Python review-evidence protocol and Python
selection consumer, with mean/minimum aggregation choices and one bounded
evidence cutoff. For this estimator pilot generation1 retains those algorithms
and wiring; the score arm explicitly carries learned weights, while the
derivative-free arm recenters on its own observed best latent/choice when
losses differ (ties keep the distribution). This is NOT a claim of new source
or topology invention in every generation. The generic runner still accepts
arbitrary new manifests and falls back honestly when prior meanings change.

Generation1 requests contain only that arm's completed past outcomes, loss,
source/graph and sampled coordinates plus explicit learned weights. They never
include the other arm's outcomes or unobserved future outcomes. A coordinate's
semantic compatibility with training observations must be explicit; a changed
vocabulary does not silently inherit a fitted response model or logits. The
control variate is fixed before drawing the current scored batch. Its fit loss
is not the native optimization loss and does not select a hidden merit gate.

## Execution and persistence

Freeze a clean source commit in a separate experiment worktree before inference.
Before consuming authoring responses, statically compile exact saved JSON (with
integer/float identity preserved), every reachable discrete factor combination
and deterministic planned draws. This executes no native/LLM world and must not
turn into loss-conditioned screening. Record the source, Docker image, model,
corpus, exact objective, proposal distributions, sampler settings, source
authoring requests/responses and all update/fit receipts.

Advance round-robin by generation, blackbox then score-control-variate. Missing
external source pauses resumably without scientific failure. No automatic retry
or replacement of an executed technical failure. A completed bad scientific
outcome remains a valid loss. A technical failure has null loss and the affected
batch does not manufacture an estimator update. Preserve partial outputs; stop
before launching further batches after a technical failure, and report
the actual budget consumed. Any change requires a separately recorded
prospective amendment, not rewriting this attempt.

## Verification and interpretation

Use analytical tests to check the estimator identity and saved/reloaded
updates. Use original-world scripted-provider execution only as software QA;
never count it as actual Qwen evidence. Actual inference must retain saved native
checkpoints and request/reply/code/event evidence. Independently reconstruct the
native loss, source/graph actually installed, exact likelihoods, eligible prior
fit and update decisions; count physical calls separately from logical use.
Record current/proposed and incumbent paths separately, all ties and worsening
observations, and raw hashes before/after read-only audit.

Completion does not require a better incumbent. Eight small development worlds
cannot establish estimator efficiency, unbiasedness empirically, causal policy
benefit, generalization or recursive designer improvement. Full-world
differentiability is neither necessary nor a pass/fail condition of this goal.
