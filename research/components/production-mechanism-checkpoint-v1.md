# Production mechanism checkpoint v1

## Research role

This increment crosses two previously separate boundaries:

1. a mechanism used by production Science Utopia experiments executes as an
   ordinary node in a typed `SystemSpec` graph; and
2. an interrupted graph run can continue from a strict-JSON checkpoint with
   the same events, trace, queued deliveries, and final mechanism state as an
   uninterrupted run.

The runtime remains mechanism-family agnostic. Funding is the first production
adapter because it supplies a compact, deterministic vertical slice, not
because funding or any other family is required in a science system. The same
state and checkpoint boundary applies to publication, governance, research,
communication, custom mechanisms, or graphs that omit those families.

This is technical-validity evidence. It does not define an optimization loss,
a held-out metric, a promotion constraint, or a science-policy preference.

## Generic state transition boundary

Every invocation now receives `MechanismContext.state`, a strict-JSON mapping
owned by that mechanism. `MechanismResult.next_state` has two distinct cases:

- `None`: preserve the prior state;
- a mapping, including `{}`: replace the prior state after the result passes
  port, event, and strict-JSON validation.

Initial per-node state may be declared under
`SystemSpec.initial_state.mechanism_states`. The runtime clones state before
giving it to a handler, so in-place mutation of the context cannot mutate the
authoritative snapshot. There is no funding-specific branch in the runner.

## Checkpoint contract

`scienceutopia.graph-checkpoint.v1` records exactly the continuation state:

```text
SystemSpec identity: system_id + complete system fingerprint
execution cursor:    trigger + next period + next event sequence
delivery cursor:     next delivery order
mechanism state:     mapping from mechanism id to strict-JSON state
port queues:          typed values, target ports, availability, lineage, order
```

The checkpoint is round-trippable through `GraphCheckpoint.to_dict()` and
`GraphCheckpoint.from_dict()`, and has a canonical SHA-256 fingerprint. Resume
rejects a different system id, a changed complete `SystemSpec`, a different
trigger, an inconsistent requested start period, unknown state owners, and
deliveries whose target port no longer exists.

Event sequence continues from the checkpoint cursor. Therefore the canonical
event dictionaries from `first_run.events + resumed_run.events` equal the
event dictionaries from one uninterrupted run. Delivery order also continues
across the boundary, including values that are still latent when the first run
stops.

The snapshot is transport-neutral rather than path-owning: experiment tooling
can store the returned dictionary using its existing atomic artifact writer,
database, or job checkpoint store. Runtime code does not silently write into a
run directory.

## Production compact-funding adapter

`production.funding.compact-ranked-allocation-v1` connects the generic
mechanism API to `utopia.funding.compact.expand_compact_result`, the strict
ranking validator/expander used by prospective production funding
experiments. The adapter deliberately calls that function rather than copying
its protocol. Consequently missing indices, duplicate indices, type coercion,
or a changed order are rejected by the production implementation.

The typed node contract is:

```text
input  panels       ARTIFACT / funding-panel
output allocations RESOURCE / resource-allocation
```

An upstream mechanism supplies a panel id, frozen application metadata, and
the already-elicited `ranked_application_ids`. The adapter applies declared
`award_slots` and `award_amount`, emits `funding.awarded` events and typed
allocation values, and checkpoints:

- processed panel ids (exactly-once guard);
- cumulative recipient balances;
- total amount awarded.

Model inference is intentionally outside this adapter. It can later be an
upstream local-model, remote-model, recorded-response, or policy mechanism
without changing the funding node or generic runner. This separation also
makes deterministic resume evidence independent of model serving.

## End-to-end evidence

`tests/system/test_production_mechanism_checkpoint.py` builds a two-node graph:

```text
scripted panel source --funding-panel, latency=1--> production compact funding
```

The test runs four periods uninterrupted, then repeats them as two periods,
JSON serialization/deserialization of the checkpoint, and two resumed periods.
It proves equality of the concatenated canonical events, concatenated execution
trace, and final checkpoint. The split occurs with one latent panel in the
queue, so equality covers queue restoration rather than state alone. It also
checks the production ordering result, accumulated funding state, exact
`SystemSpec` binding, resume cursor binding, and production rejection of a
duplicate-index ranking.

## Deliberate limits and next adapter boundary

- A checkpoint represents the boundary between completed invocations. It does
  not yet suspend a model request in the middle of one handler call.
- The runtime is still synchronous and single-process.
- The first production adapter begins after compact ranking inference and ends
  at allocation events/values. It does not claim to checkpoint the full legacy
  simulator object graph.
- Atomic storage policy belongs to experiment orchestration; the core snapshot
  is a strict-JSON value with a fingerprint.
- The next production adapter should wrap a mechanism from another family and
  preserve its own native checkpoint/audit state behind the same generic
  boundary. That will test composition of heterogeneous production mechanisms,
  not only multiple implementations of funding.
