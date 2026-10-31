# Decision 0021: Integrate the whole research vision at miniature scale before scaling

Date: 2026-10-31

Status: accepted

## Decision

The next primary milestone is **Miniature Whole-System Design Lab v0**. Before
increasing seed counts, candidate budgets, world size, or optimizer
replications, the project will connect one small end-to-end slice of every
major research idea:

1. objective abstraction;
2. whole-system mechanism graphs;
3. structural black-box optimization;
4. a differentiable surrogate or relaxation over the same design object;
5. simulator-backed outer evaluation;
6. canonical replay and an interactive game view of the search and resulting
   worlds.

The slice may use a small population, one or two simulated years, one or two
development seeds, and a small proposal budget. Its purpose is integration and
concept discovery, not statistical confirmation.

## Why breadth comes before scale

The completed v1.1 experiment has already established that a real Qwen3-8B
simulation can participate in an auditable objective-conditioned ask/tell
loop. Repeating that fixed-topology experiment with more seeds would improve
precision, but it would not test several central claims of the project:

- that the scientific system can be represented beyond eight parameters;
- that mechanism structure can be searched;
- that differentiable approximations can propose discrete institutions;
- that the same evidence can be understood and manipulated through a game;
- that all of these views share one objective and provenance boundary.

Small-scale integration exposes architectural mistakes before expensive runs.
Scale, optimizer comparison, and statistical confirmation remain necessary,
but follow the integrated vertical slice.

## Shared miniature contract

The miniature must use one set of shared objects rather than independent demos:

```text
ObjectiveSpec
    -> LossSpec + held-out metric specification
    -> structural SystemSpec search space
    -> black-box and differentiable proposal paths
    -> compact model-backed simulator execution
    -> canonical events, loss observations, and provenance
    -> game replay / branch comparison / system inspector
```

The differentiable path may optimize a learned or analytic relaxation, but its
projected candidate must re-enter the same discrete `SystemSpec` validator and
the same outer simulator boundary as a black-box proposal.

## Minimum feature coverage

The v0 slice should include:

- at least three mechanism families, including evaluation plus two of
  publication, funding, government, or communication;
- at least one node-presence or implementation substitution;
- at least one connection or scheduling/latency mutation;
- at least one result-dependent black-box proposal;
- at least one differentiable proposal followed by deterministic projection;
- outer evaluation of both proposal paths under the same declared loss;
- replayable researcher, artifact, evaluation, resource, and policy or
  communication events;
- a game view that shows objective, proposal lineage, graph differences,
  simulation activity, and observed loss without inventing scientific facts.

## Completion gate

The milestone is complete when a single command or documented workflow can:

1. load a versioned objective and miniature structural grammar;
2. generate at least one black-box and one differentiable candidate;
3. validate and execute those candidates with the model-backed simulator;
4. return valid observations through the common optimization boundary;
5. freeze compact comparison artifacts;
6. open the same campaign in the game/replay interface;
7. reproduce the run from pinned code, model, seeds, and manifests.

No claim of optimizer superiority, statistical stability, or real-world policy
quality is required for this gate.

## Deferred scale-up

After v0 integration, the project may enlarge one axis at a time:

- more seeds for uncertainty;
- more optimizer seeds for path stability;
- larger candidate budgets for search efficiency;
- random/Sobol/Bayesian/evolutionary comparisons;
- larger populations and longer horizons;
- broader mechanism grammars and environment shifts.

This decision supersedes the scheduling priority in Decision 0020 that placed
optimizer replication first. It does not change Decision 0020's scientific
claim boundary or alter any frozen v1.1 artifact.

## Attachment boundary

The user identified the attached document `A Critical Reflection on Automated
Science.pdf` as an accidental attachment. It is excluded from the research
record and is not used as evidence for this decision.
