# Production structural optimization v1

## Research role

This slice closes the first black-box loop in which the candidate is a
structurally variable **production mechanism graph**, rather than a flat
parameter vector or a toy-only graph. The same optimizer-neutral boundary now
performs:

```text
ask SystemSpec
  -> decode canonical structural selection
  -> execute production adapters
  -> summarize result
  -> compute an explicit scalar loss
  -> tell Observation
```

The implementation proves technical integration only. Its engineering loss is
not a proposed science-policy objective, its deterministic workload is not a
held-out evaluation split, and no promotion policy is applied.

## Production structural grammar

`production-structural-science-system-v1` expands to 64 valid `SystemSpec`
candidates. Every behaviorally selected institution is backed by an existing
production adapter:

| Slot | Structural choices | Production boundary |
|---|---|---|
| evaluation policy | rate evaluation or governance-tagged fixed slots | `Conference.make_acceptance_decisions` |
| funding | absent or compact ranked funding | `expand_compact_result` through the funding adapter |
| publication | absent or paper-tracker publication | `PaperTracker.add_or_update_paper` |
| review input | zero- or one-period latency | typed review-batch connection |
| funding input | absent, zero-, or one-period latency when funding exists | typed funding-panel connection |
| publication flow | absent, zero-, or one-period latency when publication exists | typed decision connection |

The evaluation family change is deliberate. The `evaluation-rate` option is
described as `EVALUATION`; the fixed-capacity option is described as
`GOVERNANCE` because it installs a persistent institutional capacity rule.
Both delegate decisions to the production conference method, while different
parameters and checkpointed `fixed_slots` produce different behavior. This is
not a claim that a general government mechanism has been implemented.

Funding and publication ports are optional at the graph boundary so a present
node can be disconnected as a legal intermediate structural candidate. In
that state the production adapter executes an empty transition. The optimizer
can therefore add a node and add its edge in separate, always-valid one-slot
steps rather than proposing a dangling edge or invalid intermediate graph.

The only non-production behavior node is
`experiment.structural-production-workload-v1`. It supplies deterministic
review batches and compact funding panels so structural effects are tested
without model-serving noise. It is experiment infrastructure, not a candidate
institution and has a single required grammar option.

## Mutation record semantics

The generic structural space now distinguishes the actual mutation dimension:

- `node-presence`: add or remove an optional mechanism node;
- `family`: exchange a present option across mechanism families;
- `implementation`: exchange implementation id or version within a family;
- `configuration`: exchange an option while retaining family and implementation;
- `edge-presence`: add or remove a typed connection;
- `latency`: change the latency of a present typed connection.

The earlier `topology` label for a latency-only edge option was too broad. Edge
slot validation fixes source, target, ports, and channel, so a non-presence
edge-option change is specifically a latency mutation. The toy grammar tests
were updated to preserve coverage of their actual family and latency changes.

The production grammar exposes legal one-step neighbors of kinds
`node-presence`, `family`, `edge-presence`, and `latency`. Implementation and
configuration remain supported by the generic grammar but this production v1
does not invent a second adapter merely to exercise those labels.

## Execution, summary, and loss boundaries

`execute_production_structural_candidate(...)` decodes and validates the
canonical candidate, registers the production mechanisms, runs the generic
checkpointable graph runner, and returns separate objects:

- the complete `SystemSpec` and fingerprint;
- the canonical graph run, events, trace, and checkpoint;
- a compact `ProductionStructuralSummary` of accepted/rejected decisions,
  publication records, funding awards, total awarded resources, blocked
  invocations, and graph size.

`observe_production_structural_suggestion(...)` accepts the existing black-box
`Suggestion`, calls an injected loss function, and returns the existing
`Observation`. Metadata binds the observation to system, event-stream, and
checkpoint fingerprints plus the summary used by the loss.

`engineering_demonstration_loss(...)` is the default only for tests. It combines
blocked invocations, graph size, accepted decisions, publication records, and
awarded resources into a finite scalar. Its sole purpose is to prove that
different simulator results cross the loss/tell boundary and affect adaptive
search. A real campaign must replace it with a preregistered `LossSpec` and
separate untouched held-out metrics.

## Structural effects proved

The test workload alternates two- and three-paper review batches. Over four
periods:

- instantaneous rate evaluation accepts six papers;
- one-period-delayed fixed-slot governance accepts three;
- an enabled instantaneous funding path makes four awards, while an absent
  funding node makes none;
- instantaneous publication records ten decisions, while one-period
  publication latency records seven within the same horizon.

These candidates have distinct complete-system fingerprints, event streams,
summaries, and engineering losses. Thus structural choices are not metadata
only: they alter production mechanism execution and the scalar observation
returned to the optimizer.

## Checkpoint identity and deterministic resume

A production candidate is executed both uninterrupted for four periods and as
two periods, strict-JSON checkpoint round-trip, then two resumed periods. The
concatenated events and final checkpoint are identical to uninterrupted
execution.

Changing only the evaluation policy family changes the complete
`SystemSpec.fingerprint`. Resuming that changed structure from the original
checkpoint is rejected before execution. Optimizer observations and runtime
continuations therefore share the same structural identity boundary; state
cannot silently cross between candidate science systems.

## Test evidence

`tests/optimization/test_production_structural.py` verifies:

- all 64 candidates execute through production adapters and have unique
  fingerprints;
- legal production neighbors cover node, family, edge, and latency mutation;
- selected structural differences change evaluation, publication, funding,
  and engineering-loss results;
- five structurally different initial suggestions complete one shared
  ask/execute/loss/tell round and an adaptive follow-up;
- observation metadata matches the canonical candidate fingerprint;
- same-structure checkpoint resume is deterministic;
- changed-structure checkpoint reuse is rejected.

## Deliberate limits

- The workload is deterministic and model-free. No claim is made about the
  robustness of a winner under stochastic agents or local-LLM inference.
- The grammar is finite and hand-declared. It does not yet synthesize new port
  schemas or arbitrary mechanism programs.
- A governance family option currently means a persistent conference capacity
  rule, not a general state or government actor.
- Disconnected optional nodes are valid intermediate candidates and contribute
  only empty state transitions until their edge is added.
- No production optimization campaign should use the demonstration loss. The
  next campaign needs a frozen grammar, objective, development seeds, budget,
  technical-validity rules, and untouched held-out split.
