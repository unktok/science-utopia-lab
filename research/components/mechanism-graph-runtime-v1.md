# Mechanism graph runtime v1 — deterministic executable slice

## Research role

This runtime is the first executable step from optimizing parameters inside one
fixed simulator toward optimizing the **science system itself**. A mechanism is
selected by an implementation id and version; its family is descriptive
metadata, not a dispatch branch. Consequently publication, funding, research,
governance, communication, a custom future family, or no mechanism at all use
the same runner contract.

The slice establishes technical execution capability only. It does not claim
that the example systems are scientifically good, ethically acceptable, or
policy ready, and it does not add a new optimization objective or held-out
evaluation metric.

## Runtime boundary

The implementation lives in `utopia/system/runtime.py` and has four parts:

1. `MechanismRegistry` maps `(implementation, version)` to a callable. A
   design can exchange or remove a mechanism without adding a family-specific
   `if` branch to the runner.
2. `MechanismContext` presents typed input values, the full mechanism spec,
   schedule position, trigger, system fingerprint, and immutable-by-contract
   initial state.
3. `MechanismResult` returns values on declared output ports and requests for
   canonical events.
4. `DeterministicGraphRunner` validates the complete `SystemSpec`, resolves
   every implementation, executes schedules, delivers edges, and constructs
   canonical `EventEnvelope` records.

Implementations are ordinary callables and may be local, model-backed, or
adapters to another simulator. The current examples are intentionally LLM-free.

## Deterministic semantics

For one `run(...)` call:

- periods increase monotonically;
- matching schedules are ordered by `(phase, mechanism_id)`;
- values on each input retain output and connection insertion order;
- a required input with no available value blocks that invocation without
  consuming queued values;
- a successful invocation consumes all currently available values on its input
  ports;
- latency is measured in periods: a value emitted in period `t` is available
  from period `t + latency`;
- zero-latency delivery reaches a later phase in the same period; if its target
  has already run, the queued value remains available next period;
- only schedules whose trigger equals the requested trigger execute;
- unscheduled nodes are valid passive structural nodes, but still require a
  registered implementation for an executable graph.

Handlers do not select channel or artifact types at runtime. Those types come
from the validated source and target `PortSpec` declarations. The runner also
rejects unknown output ports, missing required outputs, non-`MechanismValue`
outputs, and non-strict-JSON payloads.

## Evidence and causal provenance

Each `MechanismEvent` becomes a normal `scienceutopia.event.v1` envelope. The
runner reserves and supplies these provenance fields:

```json
{
  "system_id": "funding-to-research-runtime",
  "system_fingerprint": "<sha256>",
  "mechanism_id": "research-program",
  "mechanism_family": "research",
  "implementation": "example.research.resource-triggered-v1",
  "implementation_version": 1,
  "period": 1,
  "trigger": "annual",
  "input_event_ids": ["<upstream canonical event ids>"]
}
```

Output values inherit the canonical event ids produced by their invocation.
Downstream events therefore carry the upstream lineage in `input_event_ids`.
This makes a decision traceable to the mechanism version, complete system
fingerprint, and resource effect that supplied its inputs. The resulting event
tuple can be hashed, reference-validated, replayed, or projected into the game
viewer using the existing replay boundary.

## Two executable examples

`utopia/system/examples.py` supplies example implementations, rather than
special cases in the runner.

### Publication-only

One publication mechanism directly registers an author, submits an artifact,
and records a `paper.decided` event with `decision = published`. There is no
evaluation mechanism or edge. The existing replay projector reconstructs the
published artifact from the emitted canonical events.

```text
[direct publication]
  agent.registered
  paper.submitted
  paper.decided  {evaluation_mechanism: null}
```

### Funding to research

A funding mechanism emits a typed `RESOURCE / resource-allocation` value and a
replayable `resource.changed` ledger event. A one-period-latency edge carries
the allocation to a research mechanism. The first research invocation is
blocked; the next consumes the grant and emits `mechanism.decision`. That
decision's provenance contains the funding invocation's canonical event ids.

```text
period 0 phase 0  [funding] --resource, latency=1--> queued
period 0 phase 1  [research]                          blocked
period 1 phase 0  [funding] --resource, latency=1--> queued
period 1 phase 1  [research] <--- period-0 resource  executed
```

## Contract evidence

`tests/system/test_graph_runtime.py` covers:

- deterministic publication-only execution without evaluation;
- replay and reference validation of emitted canonical events;
- one-period blocking and delivery;
- zero-latency delivery to a later phase;
- causal event lineage from a resource effect to a downstream decision;
- implementation replacement, unregistration, and node removal without runner
  changes;
- runtime output-contract rejection;
- trigger selection.

Existing `tests/system/test_system_spec.py` continues to prove that the strict
legacy compiler produces the unchanged CLI contract and rejects topology
mutation. The generic runtime is additive; it does not weaken that compiler.

## Deliberate v1 limits

- The runner is single-process and synchronous. Mechanism callables may wrap
  async or remote work later, but ordering must remain explicit.
- Port queues are in memory and are not checkpointed yet.
- Initial state is exposed to handlers, but mutable mechanism state and state
  transition events need a separate versioned contract.
- Structural optimizers are not implemented here. They can propose complete
  `SystemSpec` graphs only after executable implementation ids and validity
  constraints are defined for their search space.
- This slice has example implementations, not production adapters for every
  legacy mechanism.

The next runtime increment should add checkpointable queue/state snapshots and
production adapters for at least two alternative implementations of the same
mechanism role. Only then should topology mutation be attached to a black-box
optimizer campaign.
