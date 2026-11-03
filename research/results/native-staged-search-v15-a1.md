# Staged authoring v15 a1: closed inspection loops, no native execution

This is the first, separately bounded staged-authoring revision. It is not an
extension, replacement or successful-only subset of the closed v14 budgets.
Actual execution uses immutable source
`f969f7cc2f88549ce12c5afbbbeba7b30f38828e` and the
[prospective protocol](../protocols/campaigns/native-staged-search-v15.md).
The [compact independent audit](native-staged-search-v15-a1.json) indexes exact
source/raw-file hashes. Large raw prompts and HTTP bodies remain outside Git.

## What physically happened

The source-pinned local Qwen3:8B designer receives two separate objectives,
throughput `L=-A` and reviewed production `L=-Q+0.5R`. Each has two generations,
16 bounded model/tool steps per generation and one scheduled native slot per
generation. Scientist weights, original five-author/two-year/seed42/four-year-
corpus setup and the disclosed developer seed are unchanged. CLI authorization
uses the same staged queue as the opt-in UI; it is not browser-consent evidence.

| Quantity | Actual a1 |
|---|---:|
| Scheduled/charged native slots | 4 / 4 |
| Free generation sessions | 4 |
| Designer dispatch intents | 64 |
| Recorded generation POST attempts | 64 |
| Known designer HTTP replies | 64 |
| Interrupted response-unknown turns | 0 |
| `inspect` tool actions | 64 |
| Edits/configurations/explicit valid finishes | 0 / 0 / 0 |
| Compiled generated systems | 0 |
| Physically executed native worlds | 0 |
| Scientist replies | 0 |
| Native losses | all null |

Every generation repeats one inspection action 16 times. Throughput G0 and
both reviewed-production generations inspect `world.review`; throughput G1
inspects `world.close`. These are correctly parsed, recorded inspections, not
new institutional designs. No generation issues the required `finish` action.
When the fixed step budget ends, the corresponding scheduled native slot is
charged with null loss. There is no identity fallback, hand-supplied source,
numeric failure penalty or additional native trial.

The queue's `complete` means its finite scheduled budget was exhausted, not
that the automatic institution/native-feedback goal was achieved. The
independent classification is **budget-complete-with-failures**. There is no
evidence here of a new algorithm, scientific improvement or optimizer success.

## Time and cost

The durable supervisor starts `2026-11-03T08:35:43.617402Z` and records exit0 at
`08:42:41.775604Z`: about 6 min 58 s wall time. Across 64 known steps:

- Designer adapter time: 411.432748 seconds.
- Generation POST transport time: 410.361677 seconds.
- Input tokens: 523,598; output tokens: 2,112.

These are recorded sums, not distinct extra runs. Binding and native-factory
`GET /api/tags` metadata preflights are separate from generation POSTs; this
audit does not infer an exact total of those unjournalled metadata reads.
Scientist inference cost is zero because no native world starts.

## Independent verification

The auditor reconstructs exact campaign history, every staged prompt and tool
transition, the unmodified draft, terminal generation-failure definition,
scheduled nulls, best/current state and queue/progress snapshots. It joins each
original model request to its Ollama model digest, exact prompt, response schema,
options, request seed and original HTTP reply. It distinguishes dispatch intent,
recorded POST attempt, known HTTP response and unknown interrupted response.

Two strict read-only audits are byte-identical. Both retain all **153 raw files**
unchanged and verify **242 replay-critical source blobs** against the actual
source pin. No new model call, container execution, source repair or native
probe occurs during audit. Other engineering revisions must use their own
matching runtime/interpreter checkout, not replay a1 through changed prompts.

The general `native.researcher.work.v15` capability is separately implemented
and SCRIPTED-tested, but is not invoked here. Its contract is not automatically
discoverable through this pilot's current-seed node index. This result therefore
does not establish actual Qwen use of newly authored arbitrary scientific work.

## Interpretation and next revision boundary

Staging resolves the requirement to emit a whole executable system in one
response, but this first request/response context repeatedly elicits inspection
without construction or finish. This is an authoring-orchestration failure, not
evidence that native evaluation is slow or that a loss has been optimized.
The original investigator world is not replaced by a numeric miniature.

An improved conversational tool context can be investigated as a **new**
prospectively pinned revision. Do not change the old prompts, overwrite these
nulls, reset this budget, or present a later success as the original a1 outcome.

## Reproduction

Use the approved Python in the historical matching analysis commit
`706d9b26b09dd3f685c304e3d23d07189480a403`, published as
`origin/feature/staged-search-a1-report-v15`. The exact analysis-commit locator is
also recorded by the publication verification receipt. Do **not** run this old
experiment's audit from a newer main whose author interpreter has changed;
strict source comparison deliberately rejects that mismatch. Choose a fresh
analysis-worktree path. The command below is read-only with respect to raw
evidence; place its output outside the raw root:

```sh
git worktree add --detach /tmp/science-utopia-v15-a1-analysis \
  706d9b26b09dd3f685c304e3d23d07189480a403
cd /tmp/science-utopia-v15-a1-analysis
CUDA_VISIBLE_DEVICES= PYTHONHASHSEED=42 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  /Users/shiro/unktok/dev/science-utopia-lab/.venv/bin/python \
  scripts/analyze_native_staged_search_v15.py \
  --run /Users/shiro/unktok/dev/science-utopia-lab/outputs/native-staged-search-v15-a1 \
  --expected-source f969f7cc2f88549ce12c5afbbbeba7b30f38828e \
  --output /tmp/native-staged-search-v15-a1-audit.json --compact
```
