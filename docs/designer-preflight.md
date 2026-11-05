# Real-backend designer readiness

The automatic institution designer now fails closed before production search
unless the operator supplies a current interface calibration certificate.
This checks literal editing/transport, not whether a proposed institution is
novel, fair, scientifically good, or better under the loss. No such policy is
silently added to optimization.

## What it checks

Eight exact JSON operand types, followed (for staged authoring) by a continuous
source-free plan → inspect → literal source splice → reinspection → static validate → finish
session against the real original-world parent. These are instructed interface
controls, not autonomous invention. They use the production loopback wire and
host interpreter, but an explicitly separate calibration task/conversation.
Ordinary autonomous planning requires separate evidence.

Every control must pass. An incomplete/unknown/wrong reply stops that calibration
with no retry, refund, replacement, baseline fallback or source repair. Evidence
includes exact POST UTF-8 bytes, original HTTP text, literal JSON values/types,
static interpreter receipts and source/model/backend bindings. A pass flag alone
does not satisfy the verifier.

## Run and verify

Use an approved uv-managed Python and a clean commit-pinned experiment checkout.
`<request.json>` is the actual original-parent **authoring** request, optionally
wrapped under `request` as in archived generation bindings; it is not a browser
search request. `<operator-config.json>` contains `provider_binding` with pinned
model digest and sandbox image identity. Neither path is browser-selected.

```sh
<python> scripts/check_designer_contract.py run \
  --provider-config <operator-config.json> --request <request.json> \
  --output <fresh-evidence-directory> --protocol staged-v15

<python> scripts/check_designer_contract.py verify \
  --provider-config <operator-config.json> --protocol staged-v15 \
  --certificate <evidence-directory>/certificate.json
```

Staged: at most14 generation POSTs; one-shot: at most8. These are real inference
costs, not zero-cost validation. Declare their budget before running. No native
world or generated source is executed by calibration. Use a new output directory
for every source/revision; retain failures. Do not keep retrying until one passes.

The current staged source uses the same fixed local Qwen3-8B in two caller-owned
roles: thinking planner at temperature0.6 and non-thinking literal editor at0.2.
Both use top-p0.95, top-k20, min-p0,32768 context and8192 output tokens.
Thirteen editor controls and one planner control use their actual role settings;
strict equality of decoded action JSON remains required. Separate`message.thinking`is
retained in the raw response but is never
parsed as an action or used to repair missing final content. Backend evaluation
token totals are recorded without inventing a thinking/final split. The legacy
one-shot wire remains non-thinking, temperature0.2 and2048 output tokens.
Older non-thinking certificates do not authorize this runtime.
The planner control must have a nonempty separate reasoning field; editor
fields cannot substitute for that evidence. Literal editor controls must not
emit nonempty reasoning fields. No extra probe is added. This does not establish
that the reasoning is correct or that the designer can invent an institution.
V24 a3 used backend`format:"json"`after preserved a1 syntax/a2 LF failures.
V25 used Qwen's Hermes function-call notation.
The same seven functions and their schemas are included in the trusted SYSTEM
message. One complete final `<tool_call>{"name":...,"arguments":...}</tool_call>`
envelope becomes the exact same host action; no prose/fence/prefix/source repair
or reasoning extraction is allowed. Multiple calls fail as a whole, not as
silently discarded extra work. Do not normalize strings or coerce JSON values.

V25 sent neither top-level`tools`nor`format`. Ollama0.33.3's typed tool schema
does not retain property references, and its native argument-map JSON path has
a large-integer round-trip risk. Inline schemas and keep signatures, actions
and receipts as strings. This uses the learned Hermes syntax without changing
the shared backend/model or relying on its native tool argument conversion.
Full original messages and raw HTTP bodies remain archived; cold replay and
the independent auditor bind the declared Hermes channel to its exact source.
The same14 exact decoded actions AND role-specific reasoning evidence must pass
before production, including real LF and9007199254740993. Older certificates
cannot authorize this revision. The legacy one-shot wire remains JSON mode.

V26 requests backend `format:"json"` with exactly one final function object
`{"name":...,"arguments":{...}}`. Completed assistant history remains Hermes
text, but new responses must not have XML tags. No top-level `tools` or native
argument-map conversion is used. All fourteen exact actions and role checks
are unchanged and must pass again at the new source. Malformed or truncated
known HTTP200 messages are invalid responses, not unknown network failures;
the same completion decoder verifies live replies and cold replay. No failed
reply is repaired or retried. Free authoring additionally receives its own
previous plan, literal implementation facts and measured results as data, not
as policy instructions or proof of institutional improvement.

V27 keeps the same response channel and exact controls, but changes production
editor context. A literal workbench shows current nodes, source, root fields
and complete root addresses, with explicit bounded-body omission descriptors.
Already observed values can be edited without a mandatory extra read. The
first planner stays source-free; editor tool signatures put edit/splice first
without removing any legal tool or operand. Saved/cold reconstruction uses
canonical entry order. This is current-parent information, not a host-authored
candidate, source repair or scientific merit gate. A fresh V27 source-bound
actual certificate remains required; V26's pass does not authorize it.

V27 a2 additionally excludes repeated full previous-candidate bodies from
model-facing observations, with explicit candidate-body/original-observation
hashes. Every other observation field is preserved. Exact original evidence
remains archived and current draft bodies remain available to editors. This
restores the planner's source exclusion and avoids duplicating a whole old
system in its own feedback; it does not discard failed trials or measurements.

Pass `--designer-preflight <certificate.json>` to:

- `scripts/run_native_staged_search_v15.py`
- `scripts/run_native_autonomous_search_v14.py`
- `scripts/serve_native_lab.py` whenever `--search-config` is enabled, including
  the separate `--search-worker-once` process.

Python production helpers also require `preflight_certificate=...`. Both the
factory and every production author POST verify it; a successful startup does
not authorize later calls after expiry/change. Direct model/generator classes
are low-level test/calibration/explicit custom integration APIs, not a production
certificate bypass. Production helpers always use normal author conversation
mode, not the instructed calibration mode.

## Renewal and limitations

Certificates expire after24h. Changes to any `utopia/**/*.py`, model digest,
Ollama API version, sandbox image, or staged/one-shot protocol require explicit
recalibration. Tests/docs-only changes do not alter the runtime fingerprint.
Also recalibrate after any operator-known backend rebuild/update even if its
reported version did not change: API version is not binary attestation.

The certificate is trusted local operator evidence, not a signature against a
malicious operator fabricating HTTP transcripts. Keep it in ignored output
storage. Never edit timestamps, hashes, control lists or pass flags to reuse a
failed/stale certificate. Renew with a prospective finite budget and fresh files.

See the [V16 prospective verification and corrections](../research/protocols/campaigns/designer-contract-repair-v16.md)
and [work log](../research/logbook/2026-11-04-designer-contract-repair-v16.md).
