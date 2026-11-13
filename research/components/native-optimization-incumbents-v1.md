# Best-known optimization and generated-proposal readouts

The [analysis rule](../publication/optimization-incumbent-vs-generated-output-v1.md)
is now implemented as a separate read-only projection, not a modification of
the original selection files, objectives or ongoing experiments.

[The reader](../../scripts/reports/native_optimization_incumbents_v1.py)
accepts two distinct identical closed report exports for the planning,
parent-presentation or numeric studies. It preserves the eight common
references and reconstructs each three-slot chronological history. Standard
own-only selection IDs, exact losses, all tied IDs and completed counts must
match the original report. Numeric warm starts must match the declared common
minimum; its six reused prior-free slots are not counted as new histories.

At zero consumed own slots, K is the best measured common reference and O is
unavailable. After each consumed slot, K is the best completed common/own
loss, and O is the best completed own loss. Failed slots remain in the path,
without a numerical penalty or reference substitution. Tie handling is
reference-first then own chronology; all tied identities remain explicit.
Store the final incumbent's provenance, signed own-versus-reference change,
the original selection, a CSV path and a two-panel figure. Exact overlapping
values are not jittered; QA fixtures receive an explicit plot watermark.

The source and two input hashes are bound in an immutable five-file export.
This consumes already closed report projections; it is not a fresh raw audit,
new simulation, global optimum, independent optimizer replication, scientific
truth claim or evidence that a developer reference was autonomously invented.
Existing cost reports remain necessary: zero own slots does not mean the
common eight-reference bank cost zero, and numeric uses its disclosed reused bank.

[The finite continuation](../../scripts/finish_native_optimization_incumbents_v1.py)
can wait for the exact presentation-score producer or numeric coordinator to
close and exit, require its original matching complete output bundles, and
run the projection twice without inference. It checks original source/type/
receipt bindings, preserves stopped producers and never retries or restarts
science. The original producer's own-only selection is not rewritten.

The first27 interface/readout/continuation tests pass3.81s, including worse
own proposals, strict own improvement, exact reference/own ties, all-failed
own pools, malformed rows, wrong warm starts and stopped/changed producers.
Actual closed-data CLI projection and future waiting processes are separate
verification steps, not inferred from these unit tests.
