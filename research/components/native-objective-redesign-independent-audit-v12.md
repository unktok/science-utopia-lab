# Independent objective-conditioned open-redesign audit v12

`scripts/analyze_native_objective_redesign_v12.py` is a read-only consumer of
the v12 six-attempt, two-objective development campaign. It starts no simulator,
model, generated source or container. This document describes implemented
contracts and synthetic tests; it is not an actual experiment result.

## Boundary and independent reconstruction

- Require the exact existing throughput and net-reviewed-utility `LossSpec`
  payloads, original five-researcher/two-year/seed42 native binding, three
  generations of one draw per objective and the source-pinned external-author
  instructions. There is no fairness, quality, novelty or promotion veto.
- Replay each durable adaptive campaign without saving it. This independently
  checks own-arm history, current parent, strategy/draw/update identities and
  exact request-to-external-manifest provenance. A future or another arm's
  observation cannot enter a saved authoring request.
- Reuse the native checkpoint/source/protocol/wire/code/context validators from
  v7 and structural source-set comparisons from v8. Reextract original accepted
  decisions, integer-parsed peer-score sums and actual review records from the
  native checkpoint; do not trust the optimizer's reported loss alone.
- Cross-score **every completed development checkpoint** under both exact
  losses. These are same-world development diagnostics, not held-out evaluation
  metrics or new independent replications. Missing other-objective metrics
  produce a null cross-score with the original evaluation reason.
- Retain every technical/generation failure with null losses, every exact best
  observation tie, current observations and running incumbents. No replacement,
  filtering, fabricated initial-system loss or arbitrary winner substitution.
- Verify physical response journals and wire counts separately from logical
  completed worlds; partial directories remain explicit, including failures
  before a response journal is initialized. Raw file hashes are checked before
  and after audit. Output inside immutable raw evidence is prohibited.

## Open design and actual execution are separate facts

Every row includes the full candidate `SystemSpec`, exact own-incumbent parent
fingerprint and literal changes against both that parent and the initial world:
nodes, directed ports/wires/channel/latency, source body multisets, protocols,
configuration, schedules, initial state and process delegate/guard/repetition
contracts. Same-body node renaming is separately identified. Comments, labels
and changed source text do not establish a semantically new or useful algorithm.

`contracts` exposes complete declared source/ABI/process data. Actual execution
is separately bound to native `generated.code_executed` events, source/image/
context/result receipts, committed memory chains, activity-process receipts and
actual researcher-input matches. Nothing in the audit executes new institution
code or infers a beneficial effect merely because a wire/source body exists.

Hash encodings are explicit: new
`contracts.executable_sources[id].source_sha256` is raw UTF-8 source-text SHA256;
`source_value_sha256` is the canonical-JSON string digest. Historical v7
`physical_proof.code_proof.sources[].source_sha256` and v8 source-body lineage
use the latter encoding. They must not be compared as though both were raw text.

## Result and UI contract

The report schema is
`scienceutopia.native-objective-redesign-independent-audit.v12`.
`objective_order` fixes throughput then utility, `loss_specs` is a map of full
definitions, and `arms` is an object keyed by the exact objective IDs. Each arm
has `observations`, `incumbents`, `selection`, request-bound authoring proofs
and full replayed records. Row `cross_scores` is a map using the same IDs;
`own_loss` and compatibility alias `loss` are identical.

`physical_native_worlds` means **completed audited worlds**, not attempts.
`physical_world_directory_count`, `physical_cache_count` and
`partial_physical_run_proofs` separately account for attempted/partial work.
Completed technical-invalid worlds are not assigned a numerical penalty.
The final `content_sha256` binds the entire report. `audit` binds the raw
inventory, exact replay-critical source blobs and no-execution guarantees.

`scripts/figures/native_objective_redesign_v12.py` checks this report and the
full canonical losses again, rederives cross-scores and parent lineage, and
draws separate own-loss/current/incumbent paths, same-checkpoint objective
profiles and literal source/node/wire/process changes. It never labels these
as held-out benefits or optimizer superiority. Synthetic figures require an
explicit flag, a conspicuous watermark and temporary output storage.

## Run after the raw writer exits

```sh
.venv/bin/python scripts/analyze_native_objective_redesign_v12.py \
  --run /absolute/immutable/raw \
  --expected-source FULL_ACTUAL_SOURCE_COMMIT \
  --output research/results/native-objective-redesign-v12-a1.json
.venv/bin/python scripts/figures/native_objective_redesign_v12.py \
  --audit research/results/native-objective-redesign-v12-a1.json \
  --expected-source FULL_ACTUAL_SOURCE_COMMIT \
  --output paper/figures/native-objective-redesign-v12-a1
```

Repeat the audit to a different output file, compare bytes, and verify the raw
inventory remains unchanged. `--allow-incomplete` records truthful unfinished
evidence; it does not turn it into a completed experiment. An improvement or
useful institutional invention is not a software acceptance condition.
