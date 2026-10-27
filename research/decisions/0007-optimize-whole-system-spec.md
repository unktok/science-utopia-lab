# ADR 0007: Make the whole science system the design object

Date: 2026-10-27
Status: accepted

## Context

Peer review and research evaluation were discussed as concrete examples of a
replaceable institution. Work on an Evaluation System API risked making that
example appear to be the project's central abstraction.

## Decision

The canonical design object is a whole-system `SystemSpec`: a typed graph of
agents, artifacts, mechanisms, connections, schedules, initial state, and
invariants. Evaluation, publication, funding, governance, communication, and
other mechanism families are optional constituents of that graph.

The Evaluation System API is a vertical slice used to learn how to specify,
swap, audit, and test one mechanism family. It is neither required in every
system nor privileged as the main optimization target.

The first closed-loop optimizer may operate on the existing fixed-topology
parameter vector to prove the loop. Its interface and records must treat that
vector as one restricted encoding of `SystemSpec`, so later work can optimize
mechanism selection and graph structure without redefining the research goal.

## Consequences

- Roadmaps and status reports describe evaluation work as a vertical slice.
- System abstraction requires a `SystemSpec` schema, validator, legacy compiler,
  and executable graph runtime.
- Structural optimization changes mechanisms and connections, not merely the
  parameters of a peer-review implementation.
- Differentiable research may relax any learnable mechanism or the composed
  system; it is not limited to a differentiable reviewer.
