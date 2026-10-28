# Communication and knowledge diffusion mechanism v1

## Research role

This slice makes communication an independent mechanism family in the generic
science-system graph. It is not a peer-review notification feature and it does
not require evaluation, publication, funding, or government. The executable
fixture has this shape:

```text
research source
      |
      v
optional communication broker
      |                    |
      v                    v
research consumer     education consumer
```

The source creates typed knowledge items. An optional broker transforms them
into versioned messages. Two consumers with different mechanism families
receive those messages over independently delayed edges. The generic runner
still knows only schedules, typed ports, latency, state, and checkpoints.

This is an engineering fixture. Message count, fan-out, or faster delivery is
not asserted to improve science. No epistemic-quality, welfare, diversity, or
policy objective is introduced here.

## Typed contracts

### Knowledge item

`scienceutopia.knowledge-item.v1` has exactly:

```text
schema_version
knowledge_id
origin_mechanism
created_period
topic
summary
evidence_artifact_ids
```

The broker checks that the declared origin and creation period match the
runner-owned source mechanism and emitted period. The knowledge id must occur
in the delivery artifact ids, and every input requires canonical event
lineage. Reusing a processed knowledge id or an event observed in an earlier
invocation fails closed.

### Knowledge message

`scienceutopia.knowledge-message.v1` has exactly:

```text
schema_version
message_id
message_sequence
sender_id
system_fingerprint
emitted_period
transformation
source_event_ids
knowledge_items
```

Message sequence is positive and monotonic per sender. The envelope contains
one or more unique, fully validated knowledge items and unique source event
ids. It is bound to the complete `SystemSpec` fingerprint rather than only to
the communication node.

The receiving adapter verifies the declared sender, period, system
fingerprint, signal/artifact type, payload artifact ids, and inclusion of all
declared source events in runner-owned delivery lineage. It rejects unknown
fields, unsupported schemas or transformations, invalid identifiers, stale or
replayed sequences, duplicate message ids, duplicate received knowledge ids,
and non-strict JSON. It does not silently coerce or drop malformed messages.

The runtime currently attaches all canonical events from one mechanism
invocation to every output produced by that invocation. Therefore a relay
invocation that emits multiple messages has conservative invocation-level
lineage. Each message separately records the exact upstream source event ids
that its content claims, and the receiver requires those ids to occur in the
runner-owned lineage.

## Implementations and state

Two interchangeable broker implementations share the same ports and message
contract:

- `production.communication.knowledge-broadcast-v1` emits one relay message
  for each new knowledge item;
- `production.communication.knowledge-digest-v1` buffers items and emits one
  multi-item digest after the configured count threshold is reached.

The broker checkpoint state contains its implementation mode, digest size,
processed knowledge ids, observed event ids, emitted message ids, next
sequence, deterministic digest buffer, and last message fingerprint. Restore
validates cursor consistency, buffer schemas, buffer membership, event
membership, and fingerprints.

`production.communication.knowledge-receiver-v1` can be installed on any
mechanism family. Its state retains received message and knowledge ids,
per-sender sequence cursors, and the validated knowledge archive. The fixture
uses one research consumer and one education consumer to demonstrate that
communication is a cross-system mechanism rather than a publication-only
adapter.

The generic graph checkpoint continues to own queued deliveries. Thus both
buffering inside digest and in-flight network latency survive strict-JSON
checkpoint round-trip and deterministic resume.

## Structural design space

`communication-knowledge-diffusion-v1` contains 97 valid `SystemSpec`
candidates:

- broker absent, broadcast, or digest;
- source-to-broker edge absent, instant, or one-period latency;
- each broker-to-consumer edge absent, instant, one-period, or two-period
  latency.

The two consumers are fixed only to keep the effect of the communication
structure comparable. Legal one-step mutations cover `node-presence`,
`implementation`, `edge-presence`, and `latency`. Disconnected intermediate
graphs remain executable: optional input/output ports produce empty stateful
transitions rather than introducing family-specific runner behavior.

All 97 candidates execute through one registry and have distinct complete
system fingerprints. The normal black-box ask/execute/loss/tell boundary can
sample broker absence, both implementations, fan-out, and latency.

## Deterministic evidence

The source emits two knowledge items per period. With instant source delivery,
one-period delivery to both consumers, and four periods:

| Structure | Emitted messages | Receipt events | Received item copies |
|---|---:|---:|---:|
| no broker | 0 | 0 | 0 |
| broadcast | 8 | 12 | 12 |
| digest, threshold 3 | 2 | 2 | 8 |

The counts show distinct executable mechanics, not a ranking. Broadcast sends
items separately; six messages per consumer arrive inside the four-period
horizon. Digest emits four-item batches in periods one and three; only the
period-one digest reaches each consumer before the horizon.

A four-period digest run is byte-equivalent in events and final checkpoint to
two periods, JSON checkpoint round-trip, and two resumed periods. Changing one
consumer edge from one- to two-period latency changes the complete fingerprint
and makes the old checkpoint incompatible.

The fixture loss targets two emitted and two received messages plus small
technical blocked/connection overhead. It is intentionally an integration
coverage signal, not a scientific objective or held-out evaluation metric.

## Deliberate limits

- Knowledge payloads are deterministic fixtures, not truth claims or measured
  discoveries.
- The implementations do not model persuasion, attention, misinformation,
  access inequality, trust, forgetting, or semantic distortion.
- A receiver treats repeated knowledge ids as replay. A future mechanism may
  define explicit revision, contradiction, or multi-source reconciliation.
- Digest threshold is a node parameter in v1; a later design space may expose
  continuous or conditional configuration mutation.
- Real communication research needs separately versioned scientific losses,
  held-out metrics, seeds, and interpretation protocols before optimization
  results can support substantive conclusions.
