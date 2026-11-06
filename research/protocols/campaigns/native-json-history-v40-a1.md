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
