# Independent same-society evidence audit v6

`scripts/analyze_native_society_v6.py` reads an existing, quiescent experiment;
it never constructs a native factory, model client or container and never
executes authored Python. Output must be outside the raw directory. The default
source pin is `f7e3ae454ce53282d5ef75bb7a00f2f7c7b73619`; an independently
preregistered replacement run requires an explicit different `--source-commit`.
This does not rewrite a checkpoint's original source binding.

The audit combines the driver's independent extraction of the eight native
measurements (including accepted decisions and actual raw review scores) with
additional checks:

- Every raw file has the same SHA-256 before and after inspection. Session
  reconstruction does not create or touch its usual lock file.
- The three-year, one-society, two-adoption, one-draft-per-boundary protocol is
  explicit. Actual fixed-Qwen evidence and scripted software QA have different,
  fail-closed classifications.
- Initialized year zero, immutable observation archives and actual year-boundary
  checkpoints share the same scientific binding and actor IDs. Every adopted
  checkpoint equals its observed predecessor except the exact institution
  migration and its declared system fingerprint. Pre-adoption archive bytes
  equal the complete observed society bytes; restored native epochs verify the
  source, graph, event history and full migration chain.
- Cumulative flow-counter differences reproduce interval measurements; endpoint
  stocks such as resources are not subtracted. Saved cumulative LLM timing is
  reported as call time, never total experiment wall time.
- A read-only SQLite connection checks the actual response binding and response
  content hashes. Ordered physical HTTP payload hashes and years reproduce
  checkpoint response counts. Partial-year committed responses remain separate
  from checkpointed outcomes and do not create a loss.
- Exact external requests are reconstructed from their real journal prefix,
  archived domain, parent system, loss, schema and prompt. Canonical and raw-byte
  request/response hashes bind authored patches. Author identity remains a
  self-reported claim, not authenticated Codex provenance.
- Recorded source/context/result bundles and pinned image receipts match every
  checkpointed generated-code event. Partial-year execution contexts are counted
  separately and do not prove a completed or durably applied scientific effect.
  The context recorder's system label is the original founding invocation;
  migrated source identity is established by exact artifact/event receipts.

`--allow-incomplete` is only permission to inspect pending or failed evidence.
It returns `status: incomplete` and the actual native status, not success.
The report schema is `scienceutopia.native-society-v6-audit.v1`.

## Physical attempts versus committed code events

The existing append-only recorder has no attempt/commit identifier. A physical
code call may finish before a later interruption prevents its year checkpoint.
Cold resume can then append a second call for that same year. The audit keeps
every physical row, its original index and bundle hash; it never selects a
preferred attempt or deduplicates identical records.

Each row must use a source actually active in its year. Every committed native
code event must have at least one exact artifact/context/result/image match.
Many-to-one or overlapping matches are explicitly ambiguous. Unmatched records
from a completed year are labelled unattributed, possible uncommitted attempts,
not proven scientific effects. Later-year rows remain uncheckpointed. These
cases set `code_contexts.one_to_one_physical_execution_proven: false` and
`status: physical-attempt-attribution-incomplete`, even if the actual three-year
society checkpoints independently establish native completion. Missing evidence
for a committed native code event remains a hard audit error.

`checkpointed_native_event_count` (and the compatible `checkpointed_executions`
field) counts authoritative native events, never physical contexts. The report
includes all candidate record indices for each native event. Scripted native
regressions stop after the physical code receipt, cold restart from the original
founding configuration, and finish the same society. Both identical replayed
receipts and a discarded attempt with a different result retain their ambiguity
or unattributed classification. They are software QA, not actual-Qwen findings.

## Prospective response-tail replay fix

The restart regression exposed a controller issue: native portable replay keeps
responses from an interrupted later year, but the session's old observation
callback required the response journal count to equal its last completed
checkpoint. That blocked replay before the cached responses could be reused.
The fix is prospective source code, never an edit of a1/a2 run source or raw.

New observations contain an ordered, binding-specific response-prefix digest.
`CompletedResponseCache.committed_prefix_identity` verifies all committed row
identities/content hashes, including the tail, without writing or constructing
a model response. Only idempotent observation of an already observed AND already
adopted same-year boundary may accept an ahead count. It must retain the exact
pinned original prefix. The full captured-state comparison normalizes only that
single transport count; scientific state, RNG, source/model binding, outputs,
events and all other portable fields must still match. New observations,
adoption and durable migration remain strict. Legacy observations lacking a
pinned prefix cannot authorize an ahead-journal replay.

The scripted cold-restart regressions compare completed scientific serializers
to an uninterrupted reference, separately audit receipt identities, prove the
strict adoption-boundary rejection remains, and reject a changed original
response prefix. This is not a claim that historical live runs used the fix.

## Primary plans are not amendment batches

`actual_activity_effects` retains its original, narrow count of nonempty
amendment batches. The additional `rows[].activity_plans` distinguishes all
applied plan batches, amendment batches, and code-authored primary plan batches.
For a full primary plan, the audit follows the actual code event and graph edge
to its exact saved output, reconstructs optional saved amendment commands as
data, checks the applied `plan_sha256`, and compares project/direction fields
with actual saved actor state. Requested submitters are joined to actual paper
identities; an intention alone is not a fabricated successful submission.
Physical record candidates remain explicit if attempt attribution is ambiguous.

```sh
PYTHONHASHSEED=42 CUDA_VISIBLE_DEVICES= PYTHONPATH=. .venv/bin/python \
  scripts/analyze_native_society_v6.py --run /absolute/raw/run \
  --output /absolute/elsewhere/report.json --allow-incomplete
```

Online before/after losses are nonstationary observations, not a causal policy
benefit, held-out superiority or a guarantee of future scientific value. The
researcher model and archived digest stay fixed; no researcher-weight training
or population reset is part of this design loop. Cryptographic hashes check
consistency of supplied local evidence, not authenticity against an adversarial
operator rewriting the entire archive. The focused tests use scripted HTTP,
corpus and execution receipts; they are software QA, not live native findings.
