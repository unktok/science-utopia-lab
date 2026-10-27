# SystemSpec graph v1 — executable abstraction track

## Purpose

This track makes the **whole science system** the design object. Evaluation is
one optional mechanism family alongside research, publication, funding,
governance, communication, collaboration, employment, education, and future
custom families. The graph validator requires none of these families.

The v1 implementation is a migration boundary, not yet a general graph
executor. It can describe arbitrary typed graphs and can compile one restricted
graph—the existing fixed simulator topology—back to the current CLI without
changing its behavior.

## Implemented contract

`utopia.system.SystemSpec` contains:

- agent and artifact type declarations;
- typed mechanism instances with input/output ports and parameters;
- directed connections with channel type and optional temporal latency;
- schedules, initial state, invariants, and metadata;
- canonical JSON and a content fingerprint over the complete graph.

The machine-readable interchange schema is
[`../specs/system-spec-v1.schema.json`](../specs/system-spec-v1.schema.json).
The Python validator additionally checks graph semantics that plain JSON Schema
cannot express conveniently: unique IDs, existing endpoints, input/output
direction, channel and artifact compatibility, required inputs, schedules,
non-negative latency, and strict-JSON parameter values.

Structural validity is only technical validity. It does not certify a system's
scientific value, ethical acceptability, or policy suitability.

## Legacy fixed-topology adapter

The current eight-variable candidate now has an explicit lifting path:

```text
legacy candidate + design space
  -> legacy_candidate_to_system_spec(...)
  -> complete restricted SystemSpec + fingerprint
  -> compile_legacy_system(..., years=N)
  -> existing CLI arguments
```

The generated graph includes population, research, evaluation, publication,
communication, and funding mechanisms. Governance is absent because the legacy
simulator has no independent governance mechanism; its absence is intentional
and proves that a family is not mandatory. The funding-to-research feedback
edge has one-period latency.

Compilation is deliberately strict. The legacy compiler rejects added,
removed, or substituted nodes instead of pretending the current monolithic
simulator can execute a topology it does not support. A future general executor
will use an implementation registry rather than weakening this check.

## Minimal use

```python
from utopia.optimization.design_space import load_candidate, load_space
from utopia.system import compile_legacy_system, legacy_candidate_to_system_spec

space = load_space("research/specs/design-space-v0.json")
candidate = load_candidate("research/specs/example-design-v0.json")
system = legacy_candidate_to_system_spec(space, candidate)
plan = compile_legacy_system(system, years=4)

print(system.fingerprint)
print(plan.cli_args)
```

## Tests and demonstrated properties

`tests/system/test_system_spec.py` demonstrates that:

- an empty system and a publication-only system are structurally valid;
- evaluation and governance are not required;
- incompatible edges and unconnected required ports are rejected;
- serialization round-trips and fingerprints cover mechanism changes;
- the legacy adapter emits exactly the same CLI contract as the previous
  direct candidate-to-CLI path;
- the restricted compiler refuses unsupported topology changes.

## Next executable slice

The next track should add a mechanism implementation registry and graph runner
with canonical event output. The first replacement/removal experiment should
exercise a mechanism through that generic runner, with contract tests for
decision provenance and resource effects. Publication, funding, and governance
need first-class runtime adapters before structural optimization claims are
made.
