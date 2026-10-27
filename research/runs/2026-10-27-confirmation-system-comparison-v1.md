# Confirmation system comparison v1

Date: 2026-10-27

Decision: **`not_confirmed`**

## Question and frozen design

The experiment tested whether increasing annual fixed university funding capacity
from 30% to 50% reproduced the participation-continuity pattern observed during
exploration. The candidate, objectives, capability floor, protected slice,
analysis, and confirmation seeds 401, 409, 419, 421, and 431 were frozen before
execution in [`confirmation-comparison-v1.md`](../confirmation-comparison-v1.md).

Both campaigns used source commit `9c23a36755c96faa216000422006ca729bbfd2a1`,
Qwen3-8B through the local Ollama backend, the same four-year longitudinal
fidelity, dataset revision, ordered documents, evaluator, and scientific
configuration. The paired audit found the funding-capacity fraction to be the
only design difference.

## Technical result

- baseline: 5/5 complete, all on attempt 1
- candidate: 5/5 complete, all on attempt 1
- integrity and funding reliability: pass for all 10 runs
- technical inadmissibility: none
- LLM calls: 3,758 prompts, 21 recovered retries, 0 terminal failures
- combined wall time: 61,153 seconds (16.99 hours)

The confirmation comparison is therefore technically complete and authorized
for the preregistered confirmatory interpretation. It is not authorized as a
universal ranking or real-world policy claim.

## Frozen gate result

Capability outcomes were:

| Design | pass | fail | unknown |
|---|---:|---:|---:|
| baseline | 4 | 1 | 0 |
| candidate | 5 | 0 | 0 |

The candidate converted baseline seed 401 from capability fail to pass. The
remaining four pairs were pass-to-pass, with no pass-to-fail transition.

However, seed 431 showed a protected-slice reversal: low-resource participation
fell from 0.8 under baseline to 0.6 under candidate. The candidate remained above
the absolute capability floor of 0.5, but the separately preregistered gate
forbade any negative paired low-resource participation delta. Consequently:

- zero candidate capability failures: pass
- zero candidate capability unknowns: pass
- no baseline-pass to candidate-fail transition: pass
- no negative protected-slice participation pair: **fail**
- nonnegative mean aggregate participation delta: pass

The frozen decision is therefore **`not_confirmed`**. The positive average does
not compensate for the protected-slice harm observed in one world.

## Paired evidence retained

All deltas are candidate minus baseline.

| Measure | Mean delta | Descriptive 95% paired-bootstrap interval | Pair signs |
|---|---:|---:|---:|
| aggregate participation | +0.060 | [-0.040, +0.180] | 2 positive / 2 zero / 1 negative |
| low-resource participation | +0.120 | [-0.080, +0.360] | 2 / 2 / 1 |
| aggregate review burden | -0.0178 | [-0.0979, +0.0853] | lower in 3/5 |
| low-resource review burden | -0.1457 | [-0.2039, -0.0595] | lower in 4/5 |
| topic entropy | +0.0113 | [-0.0899, +0.1188] | 2 positive / 1 zero / 2 negative |

The candidate added exactly 8 funding awards and 160 grant-income units in every
world. Even if all noncompensable gates had passed, this would have been a
resource trade-off rather than dominance.

## Interpretation

The exploration-stage average improvement was not robust to the untouched
confirmation worlds under the frozen distributional rule. More funding capacity
can rescue a severe participation failure, as in seed 401, but does not guarantee
weakly better participation for every protected slice, as seed 431 demonstrates.

This is evidence against confirming this single fixed policy at this fidelity.
It does not show that funding is ineffective, identify an optimal capacity, or
estimate a real-world treatment effect. The next optimization campaign must be a
new, prospectively specified search rather than a retrospective relaxation of
this gate or removal of seed 431.

## Artifacts

- machine-readable comparison:
  `research/results/confirmation-system-comparison-v1.json`
- generated table:
  `research/runs/2026-10-27-confirmation-system-comparison-v1.generated.md`
- baseline campaign:
  `outputs/optimization/longitudinal-confirmation-baseline-v1/ccbfa178be`
- candidate campaign:
  `outputs/optimization/funding-slots-confirmation-v1/4dc44bb161`

