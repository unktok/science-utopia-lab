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

The current staged source requests reasoning on the same fixed local Qwen3-8B:
temperature0.6, top-p0.95, top-k20, min-p0,32768 context and8192 output tokens.
The14 controls use those same settings; strict equality of final JSON remains
required. Separate`message.thinking`is retained in the raw response but is never
parsed as an action or used to repair missing final content. Backend evaluation
token totals are recorded without inventing a thinking/final split. The legacy
one-shot wire remains non-thinking, temperature0.2 and2048 output tokens.
Older non-thinking certificates do not authorize this runtime.
At least one of the same14 staged responses must have a nonempty separate
reasoning field to evidence the requested mode; no extra probe is added. Exact
final controls without any such field fail readiness. This does not establish
that the reasoning is correct or that the designer can invent an institution.
The staged request omits backend`format`up front so native reasoning is not
constrained by a JSON grammar. Final content is still required to be one exact
JSON action, parsed and schema-checked without removing fences/tags or repairing
source. This is not an error-triggered format fallback. The one-shot request
continues to use backend`format:"json"`.

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
