# Conditional plain function-JSON designer history

Implement a separate explicit `plain-function-history-v40` profile off V39's
9eb1172 notes/source branch. The running D29 V39 campaign, old certificates,
raw outputs, main worktree and backend are untouched. V40 dispatch remains
conditional on original V39 closure/audits if still needed.

Only source-constructed completed assistant wrappers change: plain JSON keeps
the same name/arguments and all literal values. Parsed rejected actions keep
their exact errors/receipts/charged steps; missing/unknown malformed actions
retain existing behavior. Literal tool tags inside strings are preserved, not
sanitized. Profile-specific trusted wording removes the Hermes-history
permission. Tool advertisement/roles, raw response channel, decoder, model,
scientists, world/losses and finite budgets remain unchanged.

The operator request/pilot/runtime plans, certificate, generator settings,
transport conversation schema and independent reporter bind the explicit
profile. Legacy defaults omit new fields and retain their original history.
The new V40 driver and calibration `--conversation-profile` option select this
profile; model text cannot select it. New/legacy certificates are incompatible.

Scripted engineering evidence using the approved absolute venv Python with
CUDA empty, PYTHONHASHSEED42 and HuggingFace/Transformers offline settings:

- Initial new scope:13 pass/one optional diagnostic skipped,5.56s.
- Existing tools/contract/V39/rejected-history/role compatibility:149 pass,35.37s.
- Expanded new/staged/reporting scope:111 pass/one optional diagnostic skipped,
  three explicit native-world/Docker cases deselected,70.43s.
- Both legacy and new profile full scripted role-aware failure audits:2 pass,
  31.55s; zero actual native worlds or backend calls.
- Separate opt-in read-only V39 archive diagnostic:1 pass,2.05s; snapshot has
  24 started frames,23 recorded wires and13 assistant-history frames. Default
  reconstructed messages match recorded V39 requests; plain history preserves
  observations/receipts/arguments and original file bytes. This is not a real
  profile inference test, a repaired historical result or a token-capacity claim.

These are development checks; committed-source focused confirmation and full
source-bound software verification are distinct. No actual V40 calibration,
inference, certificate, backend setting change, native experiment, candidate
implementation or demonstrated EOF fix is claimed. Failed raw generated text
and token counts remain unknown. Literal tool-tag data may still trigger a
backend parser; this presentation-only intervention does not eliminate that risk.

## Optional six-POST diagnostic prepared separately

Add a dedicated fixed-three-frame paired harness, conditional on actual V39
closure and two matching original-D29 full terminal audits. It reconstructs the
original legacy wires before pairing, holds a read-only shared writer lock,
requires explicit operator run authorization, and pins source/runtime, provider,
model/digest and API-reported backend identity. Original source proof hashes and
all raw inventory hashes must match. Version identity is not proof of upstream
binary equivalence. The plan fixes six alternating-profile POSTs, original seeds,
8192/T.6/40960,10/900 timeouts,14 maximum metadata GETs and zero retries/worlds.

Save per-call intent before dispatch and raw transport, completion/parse/schema
classifications, reported costs/unknowns after it. Schema checks never invoke the
action interpreter or compile/execute returned code. Incomplete/EOF replies are
separate charged replicates; interrupted intents cannot resume/redispatch. The
new output directory cannot overwrite original evidence. Original file/audit
hashes are checked again at completion. No automatic eight-world continuation.

Initial mocked harness scope:16 pass/5.24s. Tests supply scripted sessions and
source/audit fixtures, reject unfinished/mismatched/tampered original evidence,
verify exact seed/options and pre-POST journals, and distinguish EOF, timeout,
partial, schema-invalid, foreign-model and interrupted outcomes with unknown
costs preserved. The final mocked scope, including the read-only writer-lock
guard, passes17/4.92s. Full committed-source software verification remains a
separate gate. No actual backend/model/Docker calls are made or claimed.

## Separate reasoning-only output-starvation probe

Offline original V39 inspection finds six length terminations, all8192 output
tokens with thinking but empty answer content; input5034..22859, not evidence
that context overflow alone explains them. Prepare a separate two-POST true/false
diagnostic on the original efficiencyG0 planner frame. Do not change production
decoding, budgets, scientists, losses or original outcomes. New script only;
all existing runtime/helper bytes still equal the broad-tested450c17f source.

Development mocked probes pass13/1.74s; committed53a03e0 combined diagnostic
checks pass30/3.89s. The first zero-network actual-archive plan reconstruction
correctly stops: the new diagnostic incorrectly assumed the original planner's
host schema was PLAN_ACTION_SCHEMA. Actual V39 uses ACTION_SCHEMA for host
validation even when its trusted prompt asks for a plan. Payload/messages/seed
and raw wire otherwise reconstruct exactly. Correct the diagnostic to retain
the ORIGINAL full host schema and record the extra plan-only classification
separately. This is a new diagnostic implementation error, not a historical V39
experiment defect; no actual POST has occurred. Preserve this first outcome.

## Full verification exposes a real executor cleanup defect

Frozen450c17f full check68678 exits1:1496 pass/one optional skip/one failure,
788.46s, JUnit0e57fd9803ef2d742d824ce1c79342f721b3ca9b5d2f491b2b111cadc6323033.
The native code+protocol+wiring test's saved technical failure is a10-second
`docker rm -f` TimeoutExpired for its exact generated container. This is an
infrastructure cleanup failure, not model inference or a native numerical loss.
The old finally also skips local kill/reap/pipe closure if daemon removal raises.
Do not call this broad run passed or overwrite its JUnit. No actual probes yet.

New prospective cleanup uses existing foreground `run --rm` automatic removal
on client exit0, without another daemon rm. Keep forced exact-name cleanup for
live/nonzero clients,15s execution and10s removal bounds, all sandbox flags and
the same immutable image. Nested finally releases local client resources even
when daemon cleanup fails or is interrupted; errors remain failures, not retries
or scientific success. See [Docker's removal contract](https://docs.docker.com/reference/cli/docker/container/run/#clean-up---rm).
Mocked lifecycle tests plus real isolated-code security/timeout/output-flood
checks and the exact failed native integration case pass28/7.68s. These are
development checks, not the new committed broad gate. No Docker daemon changes,
unrelated-container deletion or real designer/scientist calls occur.

The reasoning probe is motivated by the actual archived8192-token thinking-only
failures. [Qwen's official model card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)
describes parameter-controlled nonthinking mode; [Ollama's API](https://docs.ollama.com/api/chat)
defines the think flag. Neither proves this local converted model/backend
honors it. Measure the two declared local probes after the combined committed
software gate; do not silently change production decoding based on docs alone.
