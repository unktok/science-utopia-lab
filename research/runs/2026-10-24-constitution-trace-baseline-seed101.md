# Constitution-bound trace validation: baseline / seed 101

## Identity

- Date: 2026-10-24
- Status: complete
- Purpose: validate Metric Constitution binding and funding-application conservation with a real Qwen3-8B run
- Study: `evaluation-v0`
- Study revision: `6fcbf8bae1`
- Design: baseline (`dce5399cf6d0b`)
- Seed role / seed: exploration / 101
- Run ID: `opt-evaluation-v0-6fcbf8bae1-smoke-exploration-dce5399cf6d0b-s101`
- Source commit: `390d3d09497660712ebc214f3dce13d3f10838e1`
- Metric Constitution SHA-256: `0b9cb462d1a161514eda80033b3e62a5360d14dc455b2c03f8689fefdb389f05`

## Operational result

- Backend / model: Ollama / `qwen3:8b`
- RAG device: CPU; LLM inference: Metal GPU through Ollama
- Registry state: complete, 1 attempt, 0 failures
- Wall-clock: 1,433.25 seconds (23 minutes 53 seconds)
- LLM prompts: 74; first-attempt successes: 74; transport retries / failures: 0 / 0
- Prompt / completion tokens: 60,308 / 63,271
- Papers / reviews / accepted: 2 / 6 / 1
- Active researchers / final total resources: 10 / 960.0
- Native integrity check: passed, 0 failures

Activity counts are operational diagnostics, not scientific-value measures or
policy conclusions. The campaign currently has 1 complete and 9 planned runs,
so this is not a replicated estimate of any institutional effect.

## Funding-application conservation

The trace summary passed with no unexplained attrition:

```text
26 targets
  = 26 validated
  = 25 submitted + 1 declined_by_agent
  = 25 evaluated
  = 25 decided
  -> 3 funded
  = 3 allocations recorded
  = 3 allocations applied
```

- Generation attempts: 48
- Semantic-invalid attempts: 22
- Request-error attempts: 0
- Terminal drops: 0
- Invalidity reasons: 21 × `>50% invalid paper indices (3/3)`, 1 × `(2/2)`
- Non-submission reason: 1 × `submit_false`

The previously observed difference between 26 initial targets and 25 saved
applications is therefore explained by an explicit agent decision, not silent
pipeline loss. The declined trace is `y1-a000023`, for
`institution_0001_researcher_3` and `NSF_AI_FOUNDATIONS`; no prompt or proposal
text is stored in the audit trace.

## Constitution and provenance evidence

- The study snapshot contains the complete Metric Constitution and its
  canonical SHA-256. The constitution content participates in the study
  revision, so changing objectives, constraints, evaluators, or governance
  creates a distinct campaign.
- The native manifest records the exact clean source commit, model, dataset and
  embedding revisions, resolved configuration, package versions, source hashes,
  token counts, and timestamps.
- Harness completion required the native manifest, native integrity report, and
  funding trace summary all to pass.
- The prompt-free JSONL trace contains 154 stage events. The separately logged
  application file contains exactly the 25 submitted applications.

## Evidence hashes

- Run manifest: `8893919b9e901139272201be7fb28ef987de9693c92f5f7ceaf10d619b9a819a`
- Native integrity report: `fb7152e86344e2cdc46dee17cd8f1c3edbc266b022e1f022ce95735afe7841b1`
- Funding trace JSONL: `357ac91a2ab82f8131a4ade001a69735b5ceb9cfecf65f9ae8abf7d8e38f49f5`
- Funding trace summary: `f4eb814e939db4233f1debaec71a01b82292aa2b51a33d63412e77471a306843`
- Registry report: `c9c28df2f93ddc4d3f25fde926903183e6f50ce3696791f13675dc067386b673`

## Interpretation and next gate

This run validates the audit mechanism and closes the unexplained-attrition
question. It does not validate the provisional metric proxies, demonstrate
evaluator independence, or identify an optimal science policy. Before comparing
designs, the remaining nine planned runs should be treated as a compute decision:
the full campaign is expected to require roughly four hours at the observed
single-run cost. The constitution also requires at least five runs for the
provisional objective uncertainty summaries; one run is deliberately
insufficient.
