# Structural System Space v1

Status: executable vertical slice

## Purpose

This track proves that the black-box optimizer can change the structure of a
whole science system rather than only eight numeric and categorical parameters
inside the legacy fixed topology.

The optimizer boundary is unchanged:

```text
ask -> complete SystemSpec -> opaque execution -> scalar LossSpec -> tell
```

`utopia.optimization.structural_space.StructuralSystemSpace` implements the
existing `SearchSpace` protocol. The optimizer sees canonical `SystemSpec`
JSON and a scalar loss. It does not inspect the graph runner, event stream, or
mechanism implementations and requires no gradients.

## Typed structural grammar

A `StructuralGrammar` declares a finite, auditable design language:

- `NodeSlot`: one semantic position in the graph;
- `NodeOption`: one complete typed `MechanismSpec` and its schedule;
- `EdgeSlot`: one potential typed relation between node ports;
- `EdgeOption`: one legal connection variant, such as latency;
- `StructuralSelection`: selected implementation or absence for every slot.

Node slots may be optional, so mutations can add or remove mechanisms. Multiple
options in a node slot exchange implementations without changing optimizer
code. Edge slots may be optional and may expose connection variants, so
mutations can add or remove an edge or change topology attributes.

The v1 implementation enumerates a finite grammar. This is intentional: it
makes legality, reproducibility, and budget size explicit before adding an
open-ended graph generator or learned proposal model.

## Legality and canonical binding

Candidate generation is grammar-first:

1. enumerate slot selections;
2. expand each selection to a complete `SystemSpec`;
3. apply the ordinary whole-system graph validator;
4. retain only technically valid graphs.

The selected slot values are stored under
`metadata.structural_encoding`. Candidate loading parses that selection,
rebuilds the graph from the grammar, and requires byte-equivalent canonical
JSON. A candidate cannot change parameters, ports, implementation IDs, edges,
or schedules while retaining a stale selection record.

`SystemSpec.fingerprint` remains the candidate identity. Consequently node
presence, implementation choice, edge presence, and edge latency all affect the
fingerprint and optimizer duplicate detection. Serialization round-trips
without changing it.

## One-step mutation operators

The adapter exposes only valid one-slot neighbors. Each mutation is recorded as
one of:

- `node-presence`: add or remove an optional mechanism;
- `family`: exchange a present node across descriptive mechanism families;
- `implementation`: exchange the implementation of a present node;
- `configuration`: exchange a present option while retaining family and implementation;
- `edge-presence`: add or remove an optional connection;
- `latency`: change a present connection's delivery latency.

If removing a node would leave an edge dangling, that mutation is not a legal
one-step neighbor. The optimizer may first remove the edge and remove the node
in a later step. This keeps every proposed intermediate candidate executable.

## Executable toy grammar

`toy_structural_grammar()` provides a production-independent proof with 39
valid systems:

| Slot | Choices |
|---|---|
| publication | direct, curated, or community-governed; required; the third option changes the descriptive family from publication to governance |
| funding | absent, fixed grant, or matching grant |
| research | absent, resource-triggered, or autonomous |
| resource edge | absent, zero-latency, or one-period latency when endpoints are compatible |

All implementations run through the generic `MechanismRegistry` and
`DeterministicGraphRunner`. They are intentionally simple and LLM-free. The
test loop computes a disposable engineering loss from their event stream, calls
`tell`, and verifies that the next suggestion is a result-dependent structural
mutation of the best observation.

That disposable loss is not a research objective and the emitted events are
not a held-out evaluation suite. It exists only to prove the closed technical
loop while preserving the separation between optimization loss, technical
validity, held-out metrics, and optional promotion policy.

## Demonstrated properties

`tests/optimization/test_structural_space.py` verifies:

- all 39 graphs are valid, executable, and have distinct fingerprints;
- absence/presence, multiple implementation families, and edge variants occur;
- illegal dangling or port-incompatible edges are excluded and rejected;
- canonical round-trip and rebuild detect candidate tampering;
- legal neighbors cover node presence, family, implementation, edge presence,
  and latency mutation kinds;
- sampling and mutation are deterministic;
- the existing `AdaptiveRandomSearch` completes ask/execute/loss/tell and state
  restoration with structural candidates.

## Production boundary and next step

This slice does not claim that the legacy production simulator can execute
arbitrary topologies. The current production compiler remains deliberately
strict and accepts only its fixed topology. The generic graph runner executes
the toy mechanisms through the same typed contracts that production adapters
must implement.

The next production step is to expose at least two real mechanism roles through
the registry, including checkpointed state and resource/decision provenance,
then define a versioned finite structural grammar over those adapters. A
model-backed structural campaign should start only after its `LossSpec`, seed
split, grammar revision, and maximum proposal budget are frozen.
