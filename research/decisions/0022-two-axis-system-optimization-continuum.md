# Decision 0022: Separate design freedom from search method

Date: 2026-10-31

Status: accepted

## Decision

Science-system optimization is represented by two independent axes:

1. **design freedom** — what the optimizer is permitted to change; and
2. **search method** — how the next candidate is proposed.

Parameter optimization, mechanism substitution, and graph-structure
optimization are nested design spaces. Grid search, gradient-free black-box
search, differentiable-surrogate search, and hybrid search are methods that
can in principle operate at several of those freedom levels. Consequently,
"structural" and "differentiable" are not competing labels at the same level:
the former describes the object being changed and the latter describes one
way to search it.

## Executable levels

The first common relaxation exposes three nested levels over one
whole-system template:

| Level | Mutable variables |
|---|---|
| parameters | normalized continuous mechanism parameters |
| mechanism configuration | parameters plus implementation choices |
| graph structure | parameters, implementations, node presence, edge presence |

An open-ended system level is recorded as a frontier but is deliberately not
made executable. It would require a typed graph/program generator rather than
pretending that a fixed template is open-ended.

Schedules and latency remain fixed in the current relaxation even though the
separate discrete structural grammar already varies latency. Closing that
representation gap is a next step.

## Common boundary

Every executable coordinate follows:

```text
design-freedom view + search method
            -> relaxed proposal
            -> deterministic discrete projection
            -> valid SystemSpec fingerprint
            -> opaque outer evaluator
            -> finite loss observation or technical failure
            -> search-method-specific update
```

The outer evaluator receives only a projected `SystemSpec`, declared
`LossSpec`, and scenarios. It does not receive gradients. The simulator must
therefore remain interchangeable and may stay non-differentiable.

## Hybrid interpretation

Hybrid optimization means that a surrogate gradient proposes a location in
the relaxed design space and a result-dependent black-box method continues
from that location. Surrogate score and simulator loss remain separate. A
gradient proposal is never accepted as simulator evidence until its discrete
projection crosses the ordinary outer-evaluation boundary.

## Initial implementation

`utopia.optimization.continuum` implements:

- the two axes and their machine-readable coordinate;
- nested mutable-variable masks over `DifferentiableSystemSpace`;
- deterministic gradient-free sampling and mutation of the same raw vector;
- shared discrete projection and outer-evaluation records;
- result-dependent black-box episodes;
- freedom-masked differentiable episodes;
- gradient-initialized black-box hybrid episodes;
- a capability map that makes implemented and future cells visible.

The initial probe uses the existing analytic surrogate and synthetic opaque
outer evaluator. It proves API composition only. It does not complete the
Miniature Whole-System Design Lab because no model-backed system execution is
yet connected.

## Consequences

- Future optimizer comparisons must hold design freedom fixed.
- Future freedom comparisons must state the search method and budget.
- A claim that gradients help requires equal-budget outer evaluations against
  a black-box baseline, not merely lower surrogate loss.
- A claim that broader structural freedom helps requires accounting for the
  larger search space and projection failures.
- Game and paper views should display both coordinates, proposal lineage,
  projection, and outer loss rather than one ambiguous "optimizer" label.

