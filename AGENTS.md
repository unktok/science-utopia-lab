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
- A clean-source check also rejects untracked retention artifacts. Wait for the
  original check process to exit before copying data/figures into its worktree;
  asynchronous launch is not completion. Stage artifacts elsewhere if needed.
- Fresh worktrees may have no ignored `outputs/` directory. Before launching
  pytest with an explicit fresh `--basetemp`, create its exact parent directory
  and verify the basetemp/JUnit targets are unused. JUnit may create that parent
  only after tmp_path setup has already failed. Preserve such setup failures;
  do not silently overwrite an earlier output or count them as scientific runs.
- `git worktree add --no-checkout` can leave a new worktree with only `.git`
  and an empty index; sparse-checkout configuration alone need not populate it.
  Before a cherry-pick or source-bound command, assert actual clean status and
  required files, not just the exit code of `git status`. For an explicitly
  verified new empty worktree only, initialize its index/selected checkout before
  proceeding (for example `git read-tree -mu HEAD`). Never use this to overwrite
  a user's populated checkout. A failed preparation stops dependent commands;
  retain it and use a distinct fresh output for the corrected attempt.
- Read-only report/figure exporters can require outputs outside both scientific
  and reader checkouts. A pytest `tmp_path` under a source-local `--basetemp`
  violates that contract. Use an external `TemporaryDirectory` for successful
  export fixtures and test source-local rejection separately; do not weaken the
  production guard or assume that a directory named temporary is outside source.
- Worktree isolation is not hardware isolation. Do not start independent heavy
  CPU/Docker full-path QA, bulk embeddings or video encoding while real model
  inference is active, unless that concurrent resource profile is explicitly
  declared in the experiment. Use light documentation/read-only work in parallel.
  The experiment's own native CPU/sandbox phases remain part of its protocol.
  Do not pause/kill a scientific job to make room for QA. Shared-resource timing
  is not a dedicated model-speed benchmark, and contention must not be ruled
  out without measurements when diagnosing an inference timeout.
- Before model dispatch, inspect host-wide CPU/inference processes, not only
  this project's command names. A separate in-process MLX model can compete
  for the same unified memory/GPU without appearing as an Ollama runner.
  Record the scope of observations; absence in a filtered process list is not
  proof of an idle machine or an exclusive resource lease. Other projects may
  start later. Never stop or modify their work without authority, and never
  infer that observed competition proves a particular timeout's cause.
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
- The user's 2026-11-06 authorization makes exact-copy equality diagnostic in
  the prospective execution-readiness-v39 scope, not a scientific dispatch veto.
  Require a fresh source/model/backend-bound technical certificate in that
  explicit scope; preserve raw received values, real interpreter/static checks,
  tool coverage and cold replay. Legacy literal-control certificates keep their
  original criteria and failed status; never relabel or reuse a failed one.
- Check semantic nonconsecutive read loops and retained observed values; do
  not infer planning progress from a finished session or an unchanged parent.
- Report cumulative author/probe totals only from a complete chronological
  journal prefix or its final sealed summary, reconciling both when available.
  A few displayed recent steps are a subset, not a cumulative count. Label
  partial observations explicitly and correct reporting errors without changing raw.
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
- New optional designer modes need a scripted full-path check through the
  calibration worker, cold certificate's actual public return type, production
  role factory, next feedback-bearing prompt and cold replay. Do not replace
  the certificate API with a richer mock dictionary and infer compatibility.
  Calibration can declare an execution mode without executing its components;
  proposal-only configuration guards must not prevent that calibration.
- The outer bounded `execute` and its public `replay` are distinct from the
  role factory and inner staged replay. Optional modes/budgets must traverse
  all of them in a scripted successful terminal test before real dispatch.
  Cold guards reconstruct the complete declared bank/source/executor/budget
  contract; do not duplicate a historical numeric allowance in a second layer.
- `native_numeric_designer.save` seals its input and reserves top-level
  `content_sha256` for the journal itself. Do not reseal a public API's already
  sealed return value without removing that checksum first; verify the saved
  result equals the original. Name a paper's content hash separately. Exercise
  the actual observer/audit return type through runner retention and cold read,
  not just a fake unsealed dictionary.
