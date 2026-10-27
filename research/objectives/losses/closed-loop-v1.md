# Closed-loop optimization contract v1

Status: working specification

## Separation of roles

The project uses the supervised-learning distinction the user specified:

| Science Utopia | ML analogy | Used during search? |
|---|---|---:|
| `LossSpec` | training loss | yes |
| optimization split | training/validation data used by the search | yes |
| `EvaluationMetricSpec` | held-out accuracy, calibration, robustness | no |
| technical validity | failed/corrupt training or evaluation job | only to accept an observation |
| optional `DecisionPolicy` | deployment/promotion rule | after evaluation only |

Metrics may share underlying observables with a loss, but their roles and data
splits must be explicit. Once an evaluation metric is used to tune or select a
candidate, it is no longer held-out for that campaign.

## Required objects

### LossSpec

```text
id, version
direction: minimize | maximize
inputs: simulator observables
per-run formula
across-seed aggregation
uncertainty/risk treatment
optimization seed split
```

The optimizer sees only the value defined here, plus constraints explicitly
listed in the same campaign. No protected-slice veto is implied.

### ValiditySpec

Determines whether a simulation produced a usable observation: complete run,
valid event schema, resource accounting, required measurements, and declared
producer configuration. It does not judge whether the simulated institution is
good.

### EvaluationMetricSpec

Defines measurements applied after a candidate is frozen on untouched seeds or
stress scenarios. Metrics report effect size, uncertainty, slices, resource
cost, and failure modes. They do not update the same optimizer campaign.

### DecisionPolicy

Optional mapping from held-out evidence to a promotion decision. Floors, vetoes,
or worst-case rules exist only when explicitly selected and versioned. The
default is `report_only`.

## Closed-loop flow

```text
optimization seeds
θ_t → simulator → valid observation → loss L(θ_t)
 ↑                                      ↓
 └──────────── optimizer.observe/suggest ┘

freeze candidate θ*

held-out seeds / stress scenarios
θ* → simulator → evaluation metrics → evidence report
                                  → optional decision policy
```

## Current implementation gap

The simulator, design validation, seeded harness, random/Sobol candidate
generation, and measurements exist. The missing pieces are an executable
`LossSpec`, an optimizer state/interface, and a campaign controller that returns
observations to the optimizer until its budget is exhausted.
