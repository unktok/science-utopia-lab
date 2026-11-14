# Common64k diagnostic: only one declared payload-field change per arm

This prospectively supersedes the undispatched40k diagnostic; do not edit its
plan/source/results or label offline counts backend observations. Keep the same
byte-largest two-own-history SCRIPTED frame selection and original matching
audits as v1. Change only options.num_ctx from40960 to65536 in each payload.
Messages, tools, authored strings, seed, format, think=False, output8192,
sampling and no-truncation/no-shift remain literal. Canonical serialization
may reorder object keys; parsed dictionaries differ at exactly that field.
Record original wire/input hashes and the explicit changed-field map.

Reason: digest-verified used-model tokenizer/template analysis gives37296 and
44320 inputs, totals45488/52512 with reserved output, beyond40k but within64k.
Those are local template counts, not backend counts or a guarantee of support.
The existing local alias is already64k; no weight/model/scientist/world/loss,
proposal/seed/population or output-budget scale-up occurs. Larger context can
increase runtime/memory; report actual costs rather than assuming speed.

All v1 finite/safety boundaries remain: one empty load plus two chat POSTs
maximum,10/900s per chat,2100s whole owned worker, no retry or action execution,
unknown completion stops, fresh two-observation250%/38GiB/no-unclassified-model
resource profile, no independent heavy QA during real inference, no other
project modified. Exact source/runtime/backend and original frames are bound.
Capacity observations derive context/output limits from the actual transmitted
payload, so old40k data cannot be relabeled64k. No production certificate,
scientific advantage, scientific dispatch authorization or publication readiness
is emitted. A new source-bound native/cold software proof and real execution
readiness remain necessary before the scientific comparison.
