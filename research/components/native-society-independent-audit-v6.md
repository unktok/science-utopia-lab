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
