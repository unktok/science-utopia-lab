# V40 a1: conditional plain function-JSON completed history

This is a prospective presentation-only revision, conditional on V39's actual
finite campaign closure and original-source audits, and only if a continuation
is still needed. No V39 experiment, certificate, raw reply or failed outcome is
rewritten or reused. This document does not authorize immediate dispatch.

Select the explicit source-owned `plain-function-history-v40` designer profile
through the V40 driver and matching calibration CLI option. The legacy default
remains `hermes-function-history-v26`. Bind the selected profile in the operator
request/designer, pilot and runtime plans, calibration plan/certificate,
generation settings, conversation schema and actual transport. Unknown profiles,
cross-profile certificates and mismatched reconstructed requests reject.

For this new profile, represent each reconstructable preceding parsed assistant
action as plain `{"name":...,"arguments":...}` JSON instead of adding Hermes
tags. This includes parsed actions rejected by the host: keep their exact values,
rejected receipts, errors and charged steps. Existing handling of genuinely
malformed or absent actions is unchanged. Keep every argument type, large integer,
Unicode code point, line feed, quote and backslash; no repair, filtering, execution
or reclassification follows from history serialization. Replace the source-owned
Hermes-history permission sentence only in this profile. Tool roles/receipts,
schema advertisements, response decoder and raw original archives stay intact.
Literal `<tool_call>` or `</tool_call>` text inside authored strings remains
unchanged. Only source-constructed outer wrappers change; no regex sanitization
is allowed. Such literal tags may retain a backend parser risk, which this
presentation-only revision does not claim to eliminate.

The trigger is V39 backend HTTP500/EOF on history-bearing turns. Local pinned
model configuration selects the qwen3.5 renderer/parser. Matching logs identify
Qwen tool parsing failures; upstream v0.33.3 parses tool-call bodies as function
XML. Across the first two generations through G1 step6, five of seven Hermes
history frames fail while seven frames without assistant history return replies.
Two Hermes frames succeed. Emitted failed text is unavailable, and the installed
backend is `0.33.3+dirty`: the observed association and plausible parser mechanism
do not prove Hermes history caused these failures or that V40 fixes them.

Keep the existing local35B designer, Qwen3-8B scientists, backend, original world,
losses, eight finite slots/four generations per objective, role loads, timeouts,
context/output budgets and all permissions unchanged. Copy equality stays
diagnostic under `execution-readiness-v39`. No candidate template, hidden retry,
output salvage, backend setting change, policy handcoding or new merit veto.

Before any conditional dispatch: commit; complete source-bound software checks;
freeze a separate clean source; run fresh finite technical controls with the
new profile and independent cold replay. Historical certificates retain their
original identities/criteria. Regress the actual archived failing and succeeding
frames as a separate read-only diagnostic, preserving their raw bytes. Software
tests or copy controls alone are not real transport or free-design evidence.

## Optional targeted paired real-backend diagnostic

On2026-11-06, after the V39 closure/status report, the user instructs us to
thoroughly fix the remaining errors. Proceed with this finite local diagnostic
after its declared original-audit and committed software gates. No external
service/spending, backend change or automatic scientific pilot is introduced.

`scripts/diagnose_native_json_history_v40.py` is a separate diagnostic option,
not an automatic scientific continuation. It must not run until V39's original
writer exits, both original-D29 full terminal audits match, and the operator
explicitly authorizes this option after committed-source software checks.
Require `--raw`, two separate `--audit` files, `--writer-ended`, the exact
`--provider-config`, a fresh `--output`, and
`--run-authorized-paired-diagnostic`. The read-only shared original writer lock
prevents running alongside a writer. Audits must bind all unchanged raw bytes,
the original source proof manifest, original analyzer bytes, eight consumed slots,
and terminal budget/queue state. Compact projections do not satisfy this gate.

Only these three actual throughput frames are allowed, at the fixed V39 search
and generation paths recorded in the script:

- A: G0 `343aa017…1531`, step01, original HTTP500/EOF.
- B: G1 `94929068…537c`, step03, original HTTP500/EOF.
- C: G0 `343aa017…1531`, step03, original successful `write_file`.

Predeclare exactly A-legacy, B-plain, C-legacy, A-plain, B-legacy, C-plain:
six separately charged replicates, three per profile, globally alternating.
Each pair reuses the identical original prompt, task, binding-derived seed,
model/digest and provider; reconstruct the original legacy payload and exact
UTF-8 wire/hash before building either replicate. The sole intended input
difference is the explicit conversation profile. Pin current clean diagnostic
source/runtime and the original API-reported backend identity; version reports
do not prove that an installed dirty binary equals upstream source.

The finite maximum is6 POSTs and14 metadata GETs, with original connect10/read900
seconds,8192 output tokens,T.6,context40960 and no retries, role-load POSTs or
scientist/native worlds. Save a hashed plan, each exact wire/intent before its
POST, and each original HTTP body, incomplete envelope/error, parsed action
when available, reported costs and unknowns afterward. HTTP completion, strict
function parsing, schema validity and provider identity are separate outcomes.
An interrupted intent is charged and cannot be resumed in that output directory.

Never apply, compile, execute or adopt any returned action; this diagnostic does
not call the interpreter or supply a policy candidate. Preserve original files,
audits, failed outcomes and unknown costs. Raw responses may contain arbitrary
code or literal tool tags and remain data. A small paired diagnostic cannot
prove a universal fix or scientific benefit, is not a readiness certificate,
and does not authorize a new eight-world campaign. Any later scientific pilot
still needs its separately declared fresh technical readiness and source gates.
