# Differentiable System Design surrogate v0

Status: prospective synthetic proof only. This method is not part of the active
metric-conditioned campaign and has not optimized a real simulator output.

## Research question

Can a future `ObjectiveSpec`-conditioned loss guide gradient-based design of a
whole science system even when the actual simulator is a black box and the
system contains discrete mechanisms and graph structure?

v0 answers only the engineering question: a continuous relaxation can carry a
gradient through mixed system variables, be projected to a valid `SystemSpec`,
and be checked at a separate black-box boundary. It does not claim that the
simulator itself is differentiable or that the synthetic optimum is a policy
recommendation.

## Two-loop boundary

```text
ObjectiveSpec --validated compiler--> future LossSpec (hash-bound)
                                             |
                                             v
 mixed SystemSpec template --relax--> surrogate loss
     presence / implementation / edges / parameters
                                             |
                                  analytic gradient + uncertainty
                                             |
                                             v
                                  relaxed candidate vector
                                             |
                    threshold / argmax / rounding / dangling-edge removal
                                             |
                                             v
                                  valid projected SystemSpec
                                             |
                                             v
                           separate black-box outer evaluator
                                             |
                surrogate gap / projection gap / uncertainty / Goodhart audit
```

The inner loop may propose candidates cheaply. Only projected, schema-valid
systems cross the outer evaluator. A later learned-surrogate campaign must add
new black-box observations, recalibrate uncertainty, and decide whether to
continue or stop; v0 deliberately does not implement that real-data loop.

## Whole-system variables

The synthetic fixture spans six mechanism families rather than treating peer
review as the system:

| Family | Structural choice in the fixture |
|---|---|
| research | laboratory mechanism and exploration parameter |
| evaluation | optional mechanism, open or committee implementation |
| publication | repository or journal implementation and access delay |
| funding | optional public or matching mechanism and allocation share |
| governance | optional mission or polycentric implementation |
| communication | optional broadcast or digest implementation |

The graph also relaxes six typed edges among those mechanisms. This is a small
synthetic template, but the API is defined in terms of generic mechanism slots,
ports, typed edges, and parameters.

## Relaxation and gradient

For a binary mechanism or edge logit `z`, v0 uses
`p = sigmoid(z / temperature)`. A categorical implementation group uses
softmax. Continuous parameters are normalized to `[0, 1]`. The surrogate
returns a loss gradient with respect to all relaxed features; the system space
applies the sigmoid and softmax Jacobians to obtain the gradient with respect
to raw design variables.

Projected gradient descent clips the total gradient norm and bounds logits and
normalized parameters. The test suite checks the analytic pullback against a
central finite difference for a continuous parameter, binary mechanism,
categorical implementation, and graph edge.

## Projection contract

Projection is deterministic:

1. presence probabilities are thresholded;
2. each present categorical mechanism selects one argmax implementation;
3. continuous parameters are denormalized and rounded at their declared
   precision;
4. an edge is removed if either endpoint mechanism is absent, even when the
   edge itself crosses its threshold;
5. the resulting `SystemSpec` must pass the ordinary system validator.

Projection decisions and fingerprints are recorded. Discrete boundary
sensitivity is measured by perturbing logits around the final point. Continuous
rounding sensitivity is not conflated with discrete boundary instability.

## Synthetic proof result

The deterministic fixture ran 80 gradient updates. These numbers characterize
the test surface only:

| Quantity | Initial | Optimized |
|---|---:|---:|
| relaxed surrogate loss | 1.5306 | 0.0708 |
| projected black-box loss | 1.2296 | -0.0800 |

The final projection retained all six mechanism families and six edges. Its
projected surrogate loss was `-0.1500`; the relaxed-to-projected gap was
`0.2208`, the projected surrogate-to-black-box absolute gap was `0.0700`, and
reported relaxed-point uncertainty was `0.0462`. No configured audit threshold
was crossed and the epsilon-0.02 discrete perturbation found no boundary-
sensitive logit. These are regression expectations, not empirical findings.

## Audits and failure conditions

The report keeps distinct:

- surrogate uncertainty at relaxed and projected designs;
- relaxation-to-projection gap;
- projected surrogate-to-black-box gap;
- discrete projection instability;
- a surrogate improvement paired with black-box regression;
- exact ObjectiveSpec compilation and LossSpec identity hashes.

Objective compilation mismatch, LossSpec mismatch, incomplete surrogate
feature coverage, unresolved graph endpoints, channel mismatch, non-finite raw
vectors, and invalid projected systems all fail closed.

## Promotion boundary and limitations

- The only fixture is synthetic and uses an analytic quadratic surface.
- The outer evaluator is intentionally non-differentiable but is also
  synthetic; no LLM simulator output is read.
- Uncertainty is a distance heuristic, not calibrated predictive uncertainty.
- A gradient optimum in the relaxation need not be a good discrete system;
  that is why both projection gap and outer validation are mandatory.
- A surrogate can be Goodharted even when its training loss and gradients look
  correct. Shadow diagnostics and black-box validation remain necessary.
- The fixture ObjectiveSpec and LossSpec are synthetic compiler fixtures. No
  existing or active LossSpec, held-out seed, registry, or raw output is used.
- Promotion requires a new preregistration, training/validation split,
  calibrated surrogate protocol, simulator-backed outer evaluator, and explicit
  policy/governance review.

## Reproduce the proof

```bash
.venv/bin/python -m pytest -q tests/optimization/test_differentiable_system.py
```

Schemas and fixture:

- `research/specs/differentiable-system-design-v0.schema.json`
- `research/specs/differentiable-system-design-report-v0.schema.json`
- `tests/fixtures/differentiable-system-design/design.synthetic-test.json`
