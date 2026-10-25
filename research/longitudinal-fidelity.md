# Longitudinal participation fidelity

## Question

The one-year smoke fidelity cannot distinguish systems on the primary
participation-continuity objective: all five v1 baseline seeds and the v2
acceptance run ended with every initial researcher active. Before spending
model calls on candidate systems, this calibration asks whether the simulator
can produce a non-degenerate participation measurement at small population.

This is a measurement study, not an institutional comparison. The objective
and baseline system remain fixed; only observation duration changes.

## Mechanism-derived duration

The balanced population initializes five researchers with 50 resource units
and five with 150. Active projects incur 10 units of annual research cost. The
legacy exit rule deactivates an author at or below 10 units after the funding
cycle. In the absence of awards, a lower-band researcher therefore reaches the
exit boundary only at the end of year 4. A two- or three-year pilot cannot test
the intended attrition mechanism.

The pre-registered `longitudinal` fidelity consequently uses:

- 4 simulated years;
- 2 institutions × 5 researchers = 10 researchers;
- the balanced two-band population and one conference;
- the unchanged baseline institutional design and Metric Constitution 1.1;
- Qwen3-8B through the local Ollama endpoint.

The small population isolates duration from scale. The existing 60-person,
five-year confirmatory fidelity is not used for calibration.

## Versioned suitability gate

Study `participation-fidelity-v1` freezes policy
`participation-longitudinal-suitability` version `1.0.0`. A completed pilot
passes only if:

| Check | Pre-registered requirement |
|---|---:|
| Observed years | at least 4 |
| Initial researchers | at least 10 |
| Low-resource slice support | at least 5 |
| Distinct annual active counts | at least 2 |
| Final aggregate active fraction | strictly between 0 and 1 |
| Final low-resource active fraction | strictly between 0 and 1 |

The interior requirements reject both ceiling and floor saturation. Passing
means the fidelity can expose participation variation in one baseline
realization; it does not estimate a design effect or prove adequate statistical
power. Failure has disposition `recalibrate_fidelity`: it cannot be compensated
by favorable objective values and the policy must receive a new version before
changing duration or thresholds.

Funding reliability policy 1.0.0 and native integrity remain independent hard
admissibility checks. The pilot is baseline-only (`sampler.count=0` plus
`include_baseline=true`) and plans the five exploration seeds for provenance,
but only the prospectively selected stress seed 113 is authorized initially.

## Decision sequence

1. Freeze implementation, study revision, policy hash, and clean source commit.
2. Plan five baseline runs at `longitudinal` fidelity.
3. Execute seed 113 only.
4. Generate the harness report without changing thresholds.
5. If all integrity and reliability checks pass and participation suitability
   passes, retain this fidelity for baseline replication. Otherwise record the
   failure and create a new versioned calibration proposal.
