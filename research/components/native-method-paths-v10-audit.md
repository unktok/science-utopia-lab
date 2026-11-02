# Independent v10 method-path audit and figure

`scripts/analyze_native_method_paths_v10.py` is a read-only, fail-closed audit
for the bounded actual-Qwen v10 method comparison. It does not start a native
world, model, container or saved response operator. It independently binds the
experiment source, fixed LossSpec, schedule and shared v9 receipt; remeasures
every completed checkpoint and hard loss; rejoins raw review identities,
SQL/wire/completion/common-prefix/Year-1-clock receipts; reconstructs every
scheduled response operator and durable ask/tell decision; and verifies the raw
inventory before and after analysis.

The report keeps optimization loss, technical validity, held-out metrics and
promotion policy separate. Both arms are charged the same three historical
observations and at most three fresh native attempts. Repeated coordinates,
no-ops, worse outcomes, earliest ties and null technical failures remain in the
path. A single common-prefix-coupled development path does not establish
optimizer superiority, optimality, held-out generalization or causal policy
value.

`scripts/figures/native_method_paths_v10.py` consumes only a complete,
content-hash-bound audit. It plots current/proposed coordinates, observed fixed
loss and earliest-tie incumbent paths, including the shared center and shared
historical best. PNG/SVG output is deterministic and explicitly labelled as
development evidence rather than held-out or optimality evidence. Figure
generation performs zero model calls and zero native forwards.

Synthetic fixtures in
`tests/reports/test_native_method_paths_v10_audit.py` are contract tests only;
they are not actual-Qwen results.
