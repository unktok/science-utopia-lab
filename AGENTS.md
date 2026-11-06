# Project agent instructions

- Start research work from `research/INDEX.md` and `research/STATUS.md`.
- Keep four concepts separate: optimization loss/objective, technical run
  validity, held-out evaluation metrics, and optional promotion policy.
- Historical Metric Constitution and confirmation vetoes are not default
  constraints for new optimization campaigns.
- Run long campaigns only from a clean, commit-pinned experiment worktree.
  Develop code in a separate feature worktree and never modify an active
  experiment worktree.
- Full integration checks that compare runtime bytes with Git HEAD must start
  after committing runtime changes. Do not change runtime or HEAD during those
  checks. Preserve failed source-bound results instead of weakening the guard.
- Declare finite designer connect/read time allowances before dispatch and
  record them even on transport failure. For non-streaming reasoning, check
  their suitability for the declared output budget; a read timeout is not a
  scientific loss. Preserve missing responses/token costs as unknown, without
  output salvage, hidden retries or changes to active experiment settings.
- Keep raw caches and outputs out of Git. Track compact results, hashes,
  manifests, protocols, and interpreted reports.
- Before expensive model-authored campaigns, run the finite real-backend
  designer interface calibration at the exact runtime/model/backend binding.
  Mocked tests, successful JSON parsing and static validity alone are not real
  transport compatibility evidence. A failed/unknown/stale certificate must
  stop the campaign, not trigger hidden retries, source repair or a baseline
  fallback. Preserve exact request UTF-8 bytes as well as parsed dictionaries.
- Check semantic nonconsecutive read loops and retained observed values; do
  not infer planning progress from a finished session or an unchanged parent.
- A directed copy-control pass is not free-design context-capacity evidence.
  Regress actual failed-history editor frames and malformed graph shapes; keep
  exact failure information while avoiding repeated full bodies and opaque
  parser errors. Never call an interface bug-free on copied controls alone.
- Do not execute Apple-provided Python or pip. Use `.venv/bin/python`,
  `~/.local/bin/python3`, `~/.local/bin/pip3`, and `/opt/homebrew/bin/uv`.
- Regress inert institutional edits against full fixed-researcher request
  payloads, not only graph fingerprints or losses. Opaque cell-bound audit IDs
  must not introduce pre-treatment model-input differences. Preserve raw audit
  identities and intentionally authored scientific references; do not rewrite
  historical logs or interpret an unused parameter's loss change as a policy effect.
- Inspect backend-reported input/output counts and length termination together.
  Correctly rejecting a partial reply does not establish sufficient free-design
  context room. Regress actual history-bearing frames, preserve all JSON/string
  contents, and distinguish message-byte savings from measured token capacity.
- Distinguish exact-copy task noncompliance from corrupted operative arguments.
  Allowed optional production annotations must not be silently stripped to pass
  a failed copy control; retain its raw reply/cost and predeclare any new input.
- A changed parameter name or an author's claimed effect is not evidence of
  implemented behavior. Trace the actual consumer and preserve local adapter
  consumption notices as non-veto information, never a new novelty/merit gate.
  Do not make arbitrary parameters operative by silently implementing the
  author's prose; the generated system must contain its own actual consumer.
- HTTP 200 alone is not completion evidence. Preserve incomplete provider
  envelopes and unknown costs, require the declared final-response signal, and
  distinguish a related upstream defect from a proven cause of the local event.
- A paired test with time.time fixed does not establish independence from
  execution clocks. Vary host clocks as well as graph/audit identities, compare
  full scientist request payloads, and retain raw operational timestamps. Fix
  unintended renderer/argument-shadowing paths instead of regex-scrubbing
  arbitrary authored scientific timestamps or mutating old logs to match.
- Schema-rejected model actions are untrusted JSON, not validated tool objects.
  Regress rebuilding the next prompt and UI history for malformed member types
  and missing keys, not only the immediate rejection. Retain exact raw actions,
  errors and charged steps; never fabricate a missing terminal journal during
  analysis or call a limited component diagnostic a successful original audit.
