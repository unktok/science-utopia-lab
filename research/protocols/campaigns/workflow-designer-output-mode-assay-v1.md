# Finite prospective output-mode assay after known workflow-v3 stop

Implemented and SCRIPTED-unit verified, not real-model executed in this revision.
No endpoint generation or new scientific dispatch has yet occurred under this protocol. It changes neither
the stopped study nor its certificate criteria, raw outputs, losses or slots.

## Why this assay, before another scientific study

Workflow-v3 finishes two real reference cells, then two own submissions fail
on graph duplication and an unexpected `rationality` property. The next
history-bearing calibration returns the prior failed proposal's exact added/
removed edges and explanation text instead of its different supplied control.
It is a known final response, not a timeout:26,527 input/2,709 output tokens,
done_reason=stop. Original cold replay reproduces all three failures. No
transport/client rewriting is observed; no general backend bug or intrinsic
model inability is established. The existing wire requests `format:"json"`
and `think:false`; the graph schema is only supplied in the prompt.

[Ollama structured-output documentation](https://docs.ollama.com/capabilities/structured-outputs)
distinguishes JSON mode from a JSON schema supplied as `format`.
[Thinking controls](https://docs.ollama.com/capabilities/thinking) are model-
dependent. Those are public API capabilities, not proof that this installed
local MLX model/backend supports or enforces either feature. We must observe
the actual local return and keep unsupported/invalid outputs as failures.

## Fixed inputs and finite budget

Use the exact retained content-utility:g1 failed-calibration frame at source
6625d8e3/plan60d8758d as technical input. Preserve its messages, history, schema,
model/digest/backend/runtime, seed, temperature0.6, context40,960, output8,192,
connect/read10/900s and owned-worker1,200s. No scientist weights, world, objective,
scientific scores or data are re-executed or changed. Model stays the installed
approved local `qwen3.6:35b-mlx-64k`; no paid/external model or new download.

The retained original JSON/nonthinking result is historical baseline, never
resent or relabelled. Three new, one-shot arms run in this fixed order:

1. Schema/nonthinking: set only `format` to the exact existing response schema.
2. JSON/thinking: set only `think:true`.
3. Schema/thinking: set those same two fields.

Do not change prompt text, repair output keys/graphs, alter seeds, truncate
history, expand budgets or keep resampling until success. Preserve actual UTF-8
request/response bytes, provider finish/token evidence and every API error.
An unsupported-mode HTTP error is a known technical result, not a zero cost or
scientific loss. Unknown completion stops every remaining arm immediately.

After all three known completions, use the predeclared technical priority
schema/thinking > JSON/thinking > schema/nonthinking among arms whose literal
calibration output compiles under the unchanged original graph domain. If any
qualifies, make at most one free-design call on the exact retained throughput:g0
proposal frame, changing only that chosen output-mode pair. This is an assay
output, not replacement/repair of the original T:g0 slot, not admission to the
stopped study, and not a native world or loss observation. If none qualifies,
make no free-design call. A failed free proposal ends the assay without refill.

Total maximum is four fresh model calls, zero scientific worlds. Selecting a
technical interface here is not selecting a scientific policy by hidden merit.
Copy equality is diagnostic; actual literal schema/graph conformance is checked.

## Required evidence before this is used

Implement/test fixed-arm payload reconstruction, exact wire retention,
known-vs-unknown stop semantics, no retries/repair and the actual original
compiler's public return type. Commit/freeze the assay source before dispatch.
Recheck that original writer/continuations are terminal and raw input hashes
unchanged. Inspect host-wide inference/CPU, bind actual local model/backend,
and do not stop other projects or run independent heavy QA during this assay.

Replaying retained records is not new model evidence. A successful calibration
or free graph alone is not a successful original experiment, proof of reliable
invention, institutional improvement or publication readiness. A changed setting
must not enter scientific dispatch without its own prospectively bound complete
production calibration/cold/native interface proof. Subsequent science, if any,
needs a separate finite protocol; old failed/stopped slots remain literal.

## Implementation and current verification

`scripts/diagnose_native_workflow_output_modes_v1.py` exposes exclusive prepare,
run and read-only replay actions. The plan retains original sealed frames and
exact-file hashes; all historical runtime files must remain byte-identical.
The actual shared transport worker and unchanged public workflow compiler are
used. A started assay is replay-only: even a missing terminal cannot resume.
The cold reader rebuilds every changed payload, outcome, priority choice and
terminal from actual original raw receipts, without model calls. This is not
a production calibration certificate or authorization to resume science.

Seventeen SCRIPTED tests (nine new assay cases plus eight existing designer
cases) pass in27.34s. They cover exact three-mode payloads/seed/history/wire,
fixed four-call ceiling/priority, known HTTP400 unsupported schema, known length
termination without salvage, unknown HTTP200/missing worker stops, all-null
results with no free call, incomplete attempt refusal, historical-file mutation
and resealed raw-literal tampering. Their fake backend is explicitly not local
model compatibility, real free-design evidence, or a native scientific world.
JUnit `outputs/workflow-output-mode-assay-tests-v1-a1/junit.xml` SHA256
`329e691f2ff30e6d4e43eebc9ab67fde57406ed8582c96def7752445deeb28c8`.
