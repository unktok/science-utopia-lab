# Staged authoring v15 a2: automatic native feedback, exact parent retention

The operational automatic loop now runs in the original fixed-Qwen researcher
world: a local Qwen3:8B designer explicitly finishes a candidate, the native
world evaluates it, and the next designer receives its own measured loss.
Both objective arms complete two generations. **All four finished candidates
exactly retain their supplied parent.** This establishes an executable
own-feedback loop, not newly invented institutions or objective-dependent
design changes.

This is the separately bounded [a2 protocol](../protocols/campaigns/native-staged-search-v15-a2.md),
not an extension or successful-only reinterpretation of [a1](native-staged-search-v15-a1.md).
Actual source is `51d9cbbd49054cdb89c24ea5bc192ff9b63e9155`.
The [compact independent audit](native-staged-search-v15-a2.json) contains exact
source/raw inventories, tool receipts, native checkpoints, candidate deltas,
own-history joins and recorded costs. Large prompts and HTTP bodies remain raw
outside Git.

## What changed, and what did not

A2 presents continuing conversational tool history and technical progress cues
to the same local designer. Its separately declared budget is four scheduled
native slots, two generations per objective and at most 16 designer calls per
generation. The scientists, model weights, original five-author/two-year world,
seed42, corpus, objectives and supplied developer-authored seed are unchanged.
The optimization loss is explicit; there is no hidden quality, fairness,
novelty, usefulness or adoption constraint. Retention is a legal design choice.

Each generation emits 15 `inspect` calls followed by one valid explicit
`finish`. None emits `edit`, `splice` or `configure`. Each draft has zero
authored operations, null `base_patch`, no discrete factors and no continuous
coordinates. The compiled parent remains exactly the same **19 nodes and 27
wires**, including its source, state, protocol and process contracts:

`88912a72e5d2f30eace4a595548bcce0ee828bb8e1c40301c438daf13abaa2f4`.

All literal source/node/wire/process/configuration change counts are zero
against both parent and initial system. Executed Python belongs to that
disclosed inherited seed; it is not attributed to Qwen as newly authored code.
Different generation-definition and observation IDs preserve the separate
requests without implying different institutional designs.

## Loss paths and original-world measurements

Let A be accepted native review-history decisions, Q the sum of original
reviewer-score arithmetic means for accepted decisions, and R actual review
records. Q is not an institution-written final score. These are disclosed,
gameable engineering proxies, not scientific welfare.

| Objective arm | G0 loss | G1 loss | A / Q / R in each world | Literal design change |
|---|---:|---:|---|---|
| Throughput, `L=-A` | -1 | -1 | 1 / 4 / 24 | exact parent retention |
| Reviewed production, `L=-Q+0.5R` | 8 | 8 | 1 / 4 / 24 | exact parent retention |

The second throughput authoring request receives observation
`observation-native-adaptive-318ece4077805037e060b138` with complete loss -1;
the second reviewed-production request receives
`observation-native-adaptive-20e59827eaad933cf2b6a409` with complete loss 8.
The auditor reconstructs these exact own histories, scalar values and
`based_on_observation_id` links, along with every conversational model request.
Feedback reaching the next author does not establish that the author used it
effectively; its observed action is retention.

The two objective values are also recomputed from each same saved checkpoint:
every cell cross-scores -1 under throughput and 8 under reviewed production.
This descriptive remeasurement starts no extra simulation. There is no new
best, loss improvement or objective-dependent institutional divergence. The
fresh world directories and distinct checkpoint identities account for
physical executions, not independent random seeds or a controlled comparison.

## Physical execution and cost

| Quantity | Actual a2 |
|---|---:|
| Scheduled / charged native slots | 4 / 4 |
| Explicit valid designer finishes | 4 |
| Designer dispatch intents / recorded POSTs / known replies | 64 / 64 / 64 |
| Interrupted response-unknown turns | 0 |
| `inspect` / `finish` actions | 60 / 4 |
| Physically executed original researcher worlds | 4 |
| Original-scientist responses / wire requests | 368 / 368 |
| Committed / recorded code executions | 32 / 32 |
| Technical failures | 0 |

Each native world has 92 scientist responses and eight committed code events.
The native capability/activity receipts are joined to the exact source and
checkpoint, rather than inferred from drawing nodes in the UI. The new generic
`native.researcher.work.v15` capability is **not invoked** in this pilot. Its
separate original-world SCRIPTED proof remains distinct from actual Qwen use;
the a2 seed-node index does not automatically expose its ABI for discovery.

The durable supervisor starts `2026-11-03T08:44:21.999547Z` and exits0 at
`09:23:41.244360Z`: **39 min 19.245 s** wall time. Recorded costs are:

- Designer adapter time: 989.672382 seconds; POST transport: 988.184575 seconds.
- Designer input/output tokens: 561,586 / 1,781 across 64 known replies.
- Original-scientist model-call time: 1,275.043923 seconds across 368 replies.

Adapter and transport times describe overlapping measurements, not additive
extra runs. Binding/native-factory `GET /api/tags` metadata preflights are
separate, incompletely journalled and not inferred to be zero. A1's 64 earlier
designer replies, 523,598 input tokens, 2,112 output tokens and 411.432748 adapter
seconds remain charged to a1; they are neither refunded nor pooled into a
controlled a1/a2 method comparison.

## Independent verification and interpretation

Two strict read-only audits are byte-identical. They preserve **209 raw files**
unchanged and verify **242 replay-critical source blobs** against the actual
source pin. The full audit content hash is
`80d7daaa31fcbebdbf67a0d3aecf2cc21a819620b9b1cdc807ecfbd1d3d8c96d`.
Verification performs zero new model calls and zero container executions.
It replays raw tools, draft, source, definition, native results, queue budgets,
all tied losses, own histories, exact transport requests and original replies.

Separate SCRIPTED positive tests exercise newly added literal source/schedule
effects through original-world Docker execution and next-generation native
feedback. Those software tests establish supported behavior, not an additional
actual-Qwen scientific outcome. Historical actual/runtime tests are kept
separate from later production-source changes.

The finite v15 operational goal is met in both arms. No scientist or designer
weights are trained. No scientific benefit, gradient-method superiority,
autonomous useful invention, same-society adoption, held-out generalization,
full-world pathwise differentiation or finished management game is claimed.
The [whole-project inventory](../milestones/2026-11-03-staged-native-loop-v15.md)
keeps those remaining research and implementation boundaries explicit.

## Reproduction

Use the historical matching analysis branch
`origin/feature/staged-search-a2-report-v15`; its exact analysis-commit locator
is recorded in the publication verification receipt. Resolve that branch once
and create a fresh detached analysis worktree. Do **not** run this old audit
from newer main with changed authoring instructions/interpreters: strict
source comparison deliberately rejects that mismatch. This command reads raw
evidence and writes its report outside the raw root:

```sh
git worktree add --detach /tmp/science-utopia-v15-a2-analysis \
  origin/feature/staged-search-a2-report-v15
cd /tmp/science-utopia-v15-a2-analysis
CUDA_VISIBLE_DEVICES= PYTHONHASHSEED=42 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  /Users/shiro/unktok/dev/science-utopia-lab/.venv/bin/python \
  scripts/analyze_native_staged_search_v15.py \
  --run /Users/shiro/unktok/dev/science-utopia-lab/outputs/native-staged-search-v15-a2 \
  --expected-source 51d9cbbd49054cdb89c24ea5bc192ff9b63e9155 \
  --output /tmp/native-staged-search-v15-a2-audit.json --compact
```
