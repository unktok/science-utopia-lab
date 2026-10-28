# Heterogeneous production mechanism graph v1

## Research role

This slice demonstrates that `SystemSpec` is a design object for a whole
science system, not a wrapper around one peer-review parameter. Three different
production mechanism families execute in one family-agnostic graph:

```text
review batch -> conference evaluation -> publication record

funding panel -------------------------> ranked funding
```

Evaluation, publication, and funding are ordinary `MechanismSpec` nodes chosen
by implementation id and connected through typed ports. None is mandatory in
the runtime. A structural optimizer may replace an implementation, change its
parameters, reconnect it, or remove its node subject to the normal graph
validator and executable implementation registry.

This is technical-validity evidence. It does not select an optimization loss,
add a policy constraint, consume held-out evaluation data, or assert that the
demonstration topology is a desirable science policy.

## Production boundaries

### Conference evaluation

`production.evaluation.conference-acceptance-v1` delegates ranking and
accept/reject decisions to the existing production
`Conference.make_acceptance_decisions` method. Its typed contract is:

```text
input  review_batches  ARTIFACT / review-batch
output decisions       DECISION / paper-decision
```

The adapter supplies frozen papers and reviews, the configured acceptance
rate, `rate` or `fixed_slots` mode, and an optional deterministic tiebreak
seed. It checkpoints processed batch ids, cumulative decision counts, and the
production `fixed_slots` value per conference. A fresh `Conference` object is
used for each typed batch, with its native fixed-slot state restored before the
production method runs.

The legacy class adds wall-clock decision timestamps and prints an operator
summary. Neither is semantic graph state: stdout is captured and timestamps
are excluded at the adapter boundary. Scores, ordering, status, and the native
fixed-slot transition remain production behavior. The adapter emits
`evaluation.paper_decided` rather than the replay projector's reserved
`paper.decided` event because this slice does not claim that upstream canonical
`agent.registered` and `paper.submitted` events exist. The typed decision value
contains the complete downstream paper metadata.

### Publication record

`production.publication.paper-tracker-v1` delegates persistence semantics to
the existing production `PaperTracker.add_or_update_paper` method. Its typed
contract is:

```text
input  decisions  DECISION / paper-decision
output records    ARTIFACT / publication-record
```

For each first-round decision the adapter performs the same production
pending-submission then final-decision transitions. The native serialized
paper archive, accumulated review history, processed decision ids, and status
counts become mechanism state. The tracker is constructed with a neutral path
but no filesystem writer is invoked; the generic checkpoint remains
transportable strict JSON.

### Ranked funding

The existing `production.funding.compact-ranked-allocation-v1` adapter remains
unchanged. It delegates complete-permutation validation to the production
compact funding protocol and checkpoints processed panels, recipient balances,
and total awards.

`register_production_mechanisms(...)` registers all three adapters in the same
ordinary `MechanismRegistry`. The runner has no branch for evaluation,
publication, funding, or their composition.

## Composition and checkpoint proof

`tests/system/test_heterogeneous_production_graph.py` executes a four-node
graph containing a deterministic input fixture plus the three production
nodes. Each input edge has one-period latency, and the evaluation-to-publication
edge adds another period. The checkpoint cut is deliberately taken while four
heterogeneous deliveries are pending:

- the next review batch;
- the next funding panel;
- two paper decisions awaiting publication recording.

The test compares one uninterrupted four-period run with a two-period run,
strict-JSON checkpoint round-trip, and two-period resume. It requires exact
equality of concatenated canonical event dictionaries, execution trace, and
final checkpoint.

The final checkpoint independently contains:

- evaluation batches, decision counts, and one fixed acceptance slot;
- publication archive records and review histories;
- funding panels, recipient balances, and cumulative awards;
- all still-latent typed deliveries and their causal lineage/order.

A second test varies review-batch size from two to three papers. The first
production decision freezes one slot, and the next batch still accepts one
paper, proving that native state—not a stateless reimplementation—crosses
invocations and checkpoint boundaries.

## What “exchangeable” means in this slice

Mechanism identity is not encoded in the runner or graph family. A compatible
alternative is selected by changing `MechanismSpec.implementation` and
registering its callable under the same typed port role. The resulting complete
`SystemSpec` receives a different canonical fingerprint, so checkpoints and
observations cannot be silently reused across the changed science system.

Port compatibility and graph topology remain validator concerns. Behavioral
equivalence is not assumed: exchanging a mechanism intentionally creates a
different candidate system for black-box evaluation or optimization.

## Deliberate limits

- Review generation and compact funding inference are upstream typed inputs in
  this deterministic slice; model calls are not checkpointed mid-request.
- The publication adapter covers first-round pending-to-decision transitions.
  Resubmission across conferences is supported by the native tracker but not
  yet exposed by this v1 port schema.
- Canonical replay declarations for researchers and submissions should be a
  separate population/research adapter, rather than fabricated by evaluation.
- The demonstration input node is a deterministic test fixture, not a
  production research-generation mechanism.
- The next whole-system slice should add a production research or governance
  node and an optimizer-facing grammar whose alternatives declare compatible
  port roles explicitly.
