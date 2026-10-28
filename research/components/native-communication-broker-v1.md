# Native prospective communication broker v1

## Research role

The generic mechanism graph already executes broadcast and digest knowledge
brokers. This slice makes those production implementations selectable in a
new native ScienceUtopia campaign rather than only in an in-memory graph
fixture.

The feature is default-off. With `--communication-broker-mode off`, no broker
object, checkpoint state, native event, receiver record, or communication CLI
binding is produced. Citation selection, citation counts, citation graphs,
RAG state, review, funding, and agent decisions retain their existing paths.

This is an engineering vertical slice. Receiving a message does not yet alter
a researcher's beliefs, projects, resources, or scientific output, and message
counts are not treated as scientific quality.

## Explicit mechanism namespace

The prospective path is separate from legacy citation communication:

```text
legacy.publication
        |
        v
native.communication.accepted-output-source
        |
        v
native.communication.knowledge-broker
  production broadcast or digest implementation
        |  SystemSpec edge latency
        v
native.communication.researcher-receiver
```

Native canonical event types are likewise distinct:

- `native.communication.source_observed`;
- `native.communication.message_emitted`;
- `native.communication.message_received`.

They never use a citation event type or modify a citation tracker. The native
adapter calls the existing production `knowledge_broadcast` or
`knowledge_digest` handler rather than maintaining a second broker algorithm.
It supplies the generic `scienceutopia.knowledge-item.v1` delivery contract and
persists the handler's `scienceutopia.knowledge-diffusion-state.v1` state. The
resulting messages use `scienceutopia.knowledge-message.v1`, while native event
envelopes use `scienceutopia.event.v1`.

## SystemSpec and sealed plan

`native_communication_system_spec(...)` adds an exact three-node overlay to a
legacy executable `SystemSpec`. The overlay includes `knowledge-item` and
`knowledge-message` artifact types, typed connections, schedules, invariants,
and one complete-system fingerprint.

Two broker implementations are supported:

- `production.communication.knowledge-broadcast-v1`, one message per newly
  accepted output;
- `production.communication.knowledge-digest-v1`, one deterministic message
  when the configured buffer threshold is reached.

The SystemSpec-to-simulator compiler revision is now `1.1.0`. It strips the
validated overlay only while compiling the unchanged legacy core, then maps
the overlay exactly to:

```text
--communication-broker-mode
--communication-digest-size
--communication-latency
--communication-receiver-role
--communication-system-fingerprint
```

The complete overlay remains embedded in the sealed plan. Mode, digest size,
latency, receiver role, and source SystemSpec fingerprint therefore affect the
plan identity. Ports, implementation, parameters, edge latency, schedules,
artifact declarations, or overlay metadata that differ from the exact native
contract fail compilation rather than being ignored.

The production argument parser requires a lowercase 64-character SystemSpec
fingerprint whenever the broker is enabled. Dry-run plan validation parses the
same native configuration without creating directories or running a model.

## Native execution and latency

At the completed-year boundary, after funding and independently of citation
generation, the simulator supplies that year's accepted outputs to
`NativeCommunicationBroker` in stable paper-id order.

For each previously unseen accepted output, the source creates a typed
knowledge item and a canonical source event. Broadcast emits immediately for
each item. Digest retains typed items and their source event ids across years
until its threshold is met, then emits the complete deterministic buffer.

Every message is queued for:

```text
due year = emitted year + SystemSpec latency
```

Latency zero delivers at the same year boundary. Positive latency remains in
the checkpoint queue and is delivered in a later year. A receipt records the
declared and observed latency, receiver id/role, message sequence, knowledge
ids, and complete SystemSpec fingerprint.

## Causal lineage

There are two explicit causal links:

1. the message event cites every native source event used to build its
   knowledge items;
2. the receiver event cites exactly the canonical message event it consumed.

Restore and conversion reject a missing source, future source, changed event
identity, different system fingerprint, stale delivery, duplicate output,
replayed message, or unreconciled latency. Paper ids remain evidence artifact
ids and author ids remain canonical actors; no synthetic citation is created.

## Checkpoint and canonical conversion

The native checkpoint contains:

- exact config and config fingerprint;
- last completed year;
- processed output and source event ids;
- digest buffer with source lineage;
- emitted/received message ids and monotonic sequence cursor;
- pending delayed deliveries;
- the complete typed canonical event history.

The state is included in both native and portable simulator checkpoints.
Portable scientific contracts include the native configuration only when the
feature is enabled, preserving the default-off contract shape.

`utopia.replay.converter` recognizes the optional state, reconstructs and
validates it, and merges the native events into the ordinary canonical stream.
Event ids remain stable because canonical sequence is excluded from event
identity; their final sequence is assigned with the rest of the run.

## Deterministic evidence

`tests/communication/test_native_broker.py` uses only synthetic development
seeds and small in-memory accepted outputs. It demonstrates:

- default-off produces no native config or plan flags;
- broadcast and digest SystemSpecs compile through sealed plans to the native
  production argument parser;
- one-year delivery latency preserves source → message → receiver lineage;
- digest buffering and pending delivery survive JSON checkpoint/resume with
  byte-equivalent events and checkpoint fingerprint;
- the native adapter persists the real production diffusion-state schema and
  marks emitted events with the selected production implementation id;
- the actual `Simulation` year hook invokes the mechanism and leaves the off
  path untouched;
- changed SystemSpec latency or checkpoint fingerprint fails closed;
- checkpoint conversion produces typed canonical native events whose cited
  sources precede their receivers.

No active v1.1 campaign, running experiment worktree, raw campaign output, or
held-out seed is read, changed, registered, or executed. No loss, metric,
scientific ranking, or promotion policy is introduced.

## Deliberate limits

- The source observes accepted-output metadata; it does not yet expose other
  knowledge sources or revisions.
- v1 has one receiver node. Multi-receiver fan-out remains available in the
  generic graph but needs a native execution mapping.
- Digest emits the whole buffer once the threshold is reached, matching the
  generic production fixture rather than enforcing fixed-size chunks.
- Receiver state is an auditable archive only. Later research must explicitly
  model attention, trust, forgetting, distortion, access, or behavioral
  response before claiming a substantive diffusion effect.
