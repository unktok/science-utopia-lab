# Native Qwen response-gradient audit v9

`scripts/analyze_native_qwen_response_v9.py` is the read-only terminal auditor
for the six-world v9 development pilot. It must be run only after the sole
writer has exited. It never starts a model, native world, generated source, or
container, and rejects an actively `in-progress` prefix even when
`--allow-incomplete` is supplied.

The auditor independently binds the pinned source, fixed hard LossSpec,
institutional graph, world/model/corpus/seed identity, six-slot order, and raw
inventory. For each completed world it remeasures the portable checkpoint,
replays the fixed tensor loss, rejoins every SQL response to its wire request
and prospective review-task identity, verifies the owner-asserted completion
receipt, and reconstructs the control proof. All input files are inventoried
before and after the audit; a byte change invalidates the report.

The current scientific and comparator modules must be byte-identical to those
at `--expected-source`; adding the auditor later is allowed, reinterpreting an
old run with a newer helper is not. An amended a2 run additionally requires
`--expected-amendment native-qwen-response-gradient-v9-a2`. Its separate
prospective document hash, three preserved a1 worlds, and nine-world combined
engineering ceiling must match the frozen plan exactly.

For a complete run, the operator is refit from exactly the three declared
calibration endpoints. Its state must equal the durable saved operator, and its
backward result and gradient candidate must reproduce the frozen proposal. The
two unused coordinates, finite path check, decomposition, and candidate native
reevaluation are then reconstructed. An unfavorable or tied candidate remains
in the report. The proposal receipt binds current content and declares zero
unused outcomes, but does not authenticate its historical creation time.

A terminal stopped attempt can be audited with `--allow-incomplete`. Only the
completed legal prefix is remeasured, the failure retains null loss, and no
counterfactual confidence or missing outcome is derived. A live prefix without
a preserved terminal failure is rejected.

Every durable SQLite response journal is counted, including a cooperatively
stopped world with no endpoint loss. Reports separate replies attached to
completed checkpoints from fresh physical replies spent in partial null-loss
worlds. Thus an interrupted forward call is never erased from the engineering
budget or converted into an optimization outcome.

Cross-world control comparison is a separate diagnostic from the terminal
failure ledger. In particular, a cooperative `PortableStop` is not relabelled
as a comparator failure. If independently sampled Qwen worlds already differ
in their pre-intervention response sequence or scientific observation, the
auditor reports that this prefix cannot identify a controlled response fit. It
does not call that drift negative fidelity, optimization failure, or a
scientific/institutional outcome.

After terminal writer exit, use the approved project environment:

```bash
.venv/bin/python scripts/analyze_native_qwen_response_v9.py \
  --run /absolute/path/to/raw/output \
  --expected-source <40-character-source-commit> \
  --output research/results/native-qwen-response-gradient-v9-a1.json \
  --markdown research/results/native-qwen-response-gradient-v9-a1.md
```

The report keeps four layers separate: the optimization loss, technical
validity, held-out metrics, and promotion policy. V9 measures only the first two.
Unused coordinates are development fidelity checks, not held-out seeds. The
fitted numeric response map is not an exact Qwen/text/native-world Jacobian, and
observed review or loss changes do not establish scientific value or causal
institutional benefit.

## A3 common-prefix audit

An a3 audit requires
`--expected-amendment native-qwen-response-gradient-v9-a3`. The analyzer
reconstructs the prepared manifest from the separately preserved a1 anchor and
verifies its checkpoint, initialized world, event stream, SQL, wire, code
contexts, model/corpus/seed, and full raw hashes without copying or rewriting
them. Every target prefix row must match the anchor payload/year/seed/response
and exact origin locator, while using a distinct normal target-cache identity.
The first non-replayed row must be the declared Year2 `PaperReview` boundary;
no later replay is allowed. Each durable execution receipt and the current
control comparator must independently agree with the anchor.

A3 response counts have three non-interchangeable meanings. `response_count`
is the full logical target-cache count, `replayed_response_count` is the shared
historical prefix, and `fresh_physical_reply_count` is only newly generated
Qwen replies. Report-level `physical_reply_count` equals fresh replies, never
logical replies. The unique anchor-origin calls are counted once in
`response_coupling`; they are not six independent worlds or six new calls.
Prior a1/a2 cost remains 228 actual replies and is reported separately from the
new a3 fresh-call total.

The final a3 analyzer also independently reads the anchor AND target Year1
checkpoints. All semantic conference/paper/reviewer identities, complete review
records, original `review_time` values and non-clock hashes must match the
declared coupling. Before/after receipt hashes are reconstructed from target
non-clock content and the recorded times. This checks internal evidence
consistency, not independent authentication of historical before timestamps or
wall-clock chronology. The source-bound implementation keeps global/transport
clocks and Year2 review clocks live.

A completed audit may evaluate the already frozen representation at61 fixed
coordinates for `response_operator_analysis.represented_landscape`. This is a
posthoc model-only visualization, not additional native measurements, training,
temperature selection or candidate search. It records the exact representation
hash and zero additional native/model calls. Figures consume only the compact
independent report, never execute raw generated source or rerun the simulator.

The actual a3 report, including the failed unused fidelity check and exact
no-op proposal, is [recorded here](../results/native-qwen-response-v9-a3.md).
Runtime, reporting, raw inventory and rendered-paper verification remain
[separately source-bound](../results/native-qwen-response-v9-verification.json).
