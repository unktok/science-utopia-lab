# Simulator-backed workload bridge v1

## Research role

The earlier whole-system graph slices used deterministic in-memory sources to
isolate graph mechanics. This slice admits an existing ScienceUtopia simulator
run as a typed workload without rerunning or modifying that campaign.

The bridge is not an optimizer objective and it does not rank system designs.
It is an evidence boundary between two execution layers:

```text
frozen native simulator run
  manifest + checkpoint + ledgers + integrity report
                         |
                         v
verified canonical source events + campaign fingerprint
                         |
                         v
SystemSpec bridge -> typed, delayed graph edges -> arbitrary mechanism families
```

The native files are opened read-only. Paths are used only during admission;
the admitted bundle contains relocatable hashes and canonical events, not a
mutable pointer into the experiment worktree.

## Native campaign admission

`load_verified_simulator_campaign` accepts three explicit roots: the source
manifest, campaign artifact root, and project root. Admission fails unless:

- the source manifest has the exact completed v1 schema;
- source commit, campaign id/revision, selected suggestion, run id, and seed
  agree with the completed campaign result;
- the native run manifest is complete, clean, and bound to the same commit and
  run;
- every declared file stays below its root and matches its lowercase SHA-256;
- every integrity row passed without failures;
- checkpoint and resource ledgers convert to a non-empty, contiguous stream of
  identity-valid `scienceutopia.event.v1` envelopes;
- canonical actor/artifact references validate.

The resulting `scienceutopia.simulator-campaign-bundle.v1` fingerprint binds:

- campaign, run, seed, protocol, and source commit;
- the source-manifest SHA-256;
- all admitted native file hashes;
- the complete canonical event-stream hash.

Changing even a non-event source-manifest field changes the campaign
fingerprint. Changing checkpoint bytes without updating the pinned manifest is
rejected before conversion.

## Typed graph contract

`production.workload.simulator-campaign-bridge-v1` is registered with one
already verified campaign bundle. Its `MechanismSpec` must repeat the campaign
fingerprint and event-stream hash exactly. These parameters are part of the
complete `SystemSpec` fingerprint.

The source stream is emitted in bounded ingestion batches. Graph periods are
ingestion ticks, not replacements for the source event's original year and
phase. Each `scienceutopia.simulator-event-batch.v1` contains exactly:

```text
schema_version
batch_id
batch_sequence
sender_id
campaign_id
campaign_revision
run_id
source_commit
campaign_fingerprint
source_event_stream_hash
target_system_fingerprint
graph_emitted_period
source_start_index
source_end_index
source_event_ids
source_events
```

The parser recreates every source `EventEnvelope`, verifies its canonical id
and contiguous source sequence, and requires the explicit source-event id list
to match the payload exactly. The batch is also bound to the target
`SystemSpec` fingerprint, so it cannot be replayed into a structurally
different graph.

## Two provenance namespaces

The bridge deliberately keeps external simulator evidence separate from graph
causality:

- `source_event_ids` are immutable identities from the admitted simulator run;
- runner-owned `input_event_ids` refer to the graph-local
  `simulator.workload_batch_emitted` event.

External ids are data inside the batch and bridge event. They are not injected
as if they were event ids created by the graph runner. Downstream graph events
therefore retain valid local causal lineage while still exposing the exact
native evidence set.

## Five-family composition

`simulator_bridge_system_spec` creates one executable proof graph. The same
typed output fans out, with independently configurable latency, to nodes whose
families are:

- evaluation;
- publication;
- funding;
- governance;
- communication.

The v1 consumer implementation is a strict generic observation adapter. It
does not pretend that a canonical event batch is already a conference review
batch, funding panel, policy, or knowledge message. A family-specific semantic
adapter can replace it behind the same typed port in a later slice.

Each receiver verifies graph fingerprint, campaign fingerprint, event-stream
hash, sender, graph emission period, artifact identity, graph-local lineage,
monotonic batch sequence, contiguous source range, and absence of replay. Its
checkpoint records batch ids, source event ids, source cursor, and event-type
counts.

## Checkpoint and resume

The bridge state records:

- campaign and event-stream bindings;
- batch size;
- next source index and batch sequence;
- emitted batch and source-event ids;
- completion and last-batch fingerprint.

The generic graph checkpoint additionally retains delayed deliveries. A split
run therefore resumes both source ingestion and downstream fan-out without
reading or mutating the native simulator files again. State restore checks the
source prefix, batch-count arithmetic, cursor, completion flag, and
fingerprint invariants.

Tests prove byte equality of concatenated events and the final checkpoint for
an uninterrupted run versus JSON checkpoint round-trip and resume. Changing a
single downstream latency changes the full system fingerprint and rejects the
old checkpoint.

## Read-only real-campaign evidence

The completed seed-521 engineering campaign was admitted directly from the
frozen v1.1 experiment artifacts without writing to them:

| Identity | Value |
|---|---|
| source commit | `0b733df425405f5e2eeb953cff2a7288f13f5af9` |
| source manifest SHA-256 | `74e7fcb285c8680994a1bd55703939a5ff666503cb31e275aeea5ba55669ca38` |
| source event-stream SHA-256 | `ba0bb641d99888246b349bcce153340beff7ab21a5a0c1ed0052c7f31a6ba540` |
| campaign bundle fingerprint | `9970ed676f7addbfd30d9aa44f04fe8c856c0bb18a5f20f169b04be5582489e9` |
| canonical source events | 71 |

With batch size 16 and the default five-family latency map, the graph emitted
five bridge events and 25 receiver events. All five receiver checkpoints ended
at source index 71 with identical event-type totals. This is integration
evidence only, not evidence that any consumer family or graph is scientifically
better.

## Deliberate limits

- The source is a completed one-year engineering campaign, not a held-out
  scientific evaluation and not the currently running metric-conditioned v1.1
  campaign.
- Admission currently supports the completed campaign-source manifest and
  checkpoint/ledger converter contract already used by the verified replay
  adapter.
- The graph replays immutable observations; it does not branch the native
  simulator midway or feed interventions back into that completed world.
- Family nodes in this proof consume generic event batches. Domain-specific
  transforms into review batches, funding panels, policies, and knowledge
  messages remain separate future mechanism implementations.
- No loss, metric, promotion rule, or scientific preference is added.
