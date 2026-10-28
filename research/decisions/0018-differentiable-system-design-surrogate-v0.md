# ADR-0018: Differentiate a surrogate, then validate a projected whole system

- Status: accepted for prospective synthetic proof
- Date: 2026-10-28

## Context

The program aims to optimize science systems with more freedom than the
parameters of one peer-review implementation. A whole-system `SystemSpec`
contains discontinuous choices: whether a mechanism exists, which
implementation it uses, which typed edges connect it, and continuous
parameters. The LLM-backed simulator is also a black box.

Treating that simulator as differentiable would be false. Restricting all
future work to enumeration would leave gradient-based system design
unexplored.

## Decision

Adopt a two-loop prospective interface:

1. bind a surrogate exactly to a future LossSpec compiled from an ObjectiveSpec;
2. continuously relax mechanism presence and edges with sigmoid, categorical
   implementations with softmax, and parameters on normalized intervals;
3. optimize only the surrogate in an inner gradient loop;
4. deterministically project proposals to ordinary, valid `SystemSpec` graphs;
5. evaluate only projected systems through a separate black-box outer boundary;
6. report uncertainty, relaxation/projection gap, surrogate/black-box gap,
   projection instability, provenance, and Goodhart flags.

The v0 reference implementation is analytic and synthetic. It spans research,
evaluation, publication, funding, governance, and communication mechanisms so
the abstraction is not reduced to peer review.

## Consequences

- Gradient flow can be tested without pretending the simulator is
  differentiable.
- The ordinary `SystemSpec` validator remains the executable structural
  boundary.
- Objective policy provenance is retained through compilation and LossSpec
  hashes.
- Projection discontinuities and surrogate mismatch become recorded results,
  not hidden implementation details.
- A real campaign still needs learned-surrogate data governance, calibration,
  simulator-backed outer validation, stopping rules, and its own preregistration.
- No active campaign asset or held-out evaluation split is an input to v0.

## Rejected alternatives

- **Backpropagate through the current simulator:** there is no valid gradient
  path through model sampling and the existing event simulation.
- **Optimize relaxed vectors without projection:** those vectors are not
  deployable science systems and can contain dangling graph structure.
- **Use the surrogate score as final evidence:** this hides approximation error
  and invites Goodhart failure.
- **Limit the design object to review parameters:** that contradicts the
  whole-system research goal.

## Evidence

- [`../optimizers/methods/differentiable-system-design-surrogate-v0.md`](../optimizers/methods/differentiable-system-design-surrogate-v0.md)
- `research/specs/differentiable-system-design-v0.schema.json`
- `research/specs/differentiable-system-design-report-v0.schema.json`
- `tests/optimization/test_differentiable_system.py`
