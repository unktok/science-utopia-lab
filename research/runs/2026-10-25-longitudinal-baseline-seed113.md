# Longitudinal baseline seed 113 measurement-calibration run

## Identity

- Date: 2026-10-25
- Status: complete; participation-suitability gate passed
- Purpose: test whether a mechanism-derived four-year fidelity avoids the
  one-year participation ceiling before running candidate systems
- Study / revision: `participation-fidelity-v1` / `79ec3468cf`
- Run ID:
  `opt-participation-fidelity-v1-79ec3468cf-longitudinal-exploration-dce5399cf6d0b-s113`
- Design ID: `dce5399cf6d0b` (baseline)
- Seed / role: 113 / exploration
- Source commit: `1d86239964efc7e78ac5a77582412d5ecbfe6fee`
- Model / backend: `qwen3:8b` / Ollama OpenAI-compatible endpoint
- Fidelity: four years, 2 institutions, 10 researchers, 1 conference
- Harness wall time: 9,553.43 seconds

The run completed on its first attempt from a clean source tree. The remaining
four planned baseline seeds were not authorized or run. This is a measurement
calibration, not a system comparison or an estimate of institutional effect.

## Pre-registered suitability decision

Policy `participation-longitudinal-suitability` version `1.0.0`, SHA-256
`aaea214f16c4ce7365634a83c9cd9286be76bb9f95d0854f5f5fbc855bdbdf8a`,
was evaluated without changing its thresholds.

| Check | Requirement | Observation | Result |
|---|---:|---:|---|
| Observed years | at least 4 | 4 | pass |
| Initial researchers | at least 10 | 10 | pass |
| Low-resource support | at least 5 | 5 | pass |
| Distinct annual active counts | at least 2 | 2 | pass |
| Final aggregate active fraction | strictly between 0 and 1 | 0.8 | pass |
| Final low-resource active fraction | strictly between 0 and 1 | 0.6 | pass |

Annual active counts were 10, 10, 10, and 8. At the end of year 4,
`institution_0000_researcher_3` and `institution_0001_researcher_0` both had
5 resource units and exited. Both were members of the fixed low-resource band;
the other three lower-band researchers remained active. The measurement is
therefore non-degenerate both in aggregate and in the protected slice.

The suitability result is `state=pass`, `disposition=eligible`, and
`comparison_eligible=true`. Design-level ranking is still unauthorized because
only 1 of the required 5 repetitions is complete. Passing this gate establishes
that the fidelity can expose participation variation in this realization; it
does not establish power, robustness, or superiority of the baseline.

## Scientific measurements

| Measurement | Aggregate | Low-resource slice |
|---|---:|---:|
| Active-researcher fraction | 0.8 | 0.6 (support 5) |
| Review burden / active researcher-step | 1.9210526316 | 2.1111111111 (support 5) |
| Final topic entropy | 1.8310204811 nats | not slice-defined |

Across four years the run produced 15 papers, 73 review actions, 8 cumulative
acceptances, and 790 final resource units. Native integrity passed in every
year, with no objective measurement gaps. These values are descriptive pilot
outputs and must not be interpreted as a comparison result.

## Funding reliability

All four annual funding traces passed conservation and funding reliability
policy `1.0.0`.

| Year | Targets / validated | Submitted / evaluated / decided | Agent-declined | Funded / recorded / applied | Drops |
|---:|---:|---:|---:|---:|---:|
| 1 | 30 / 30 | 30 / 30 / 30 | 0 | 3 / 3 / 3 | 0 |
| 2 | 28 / 28 | 27 / 27 / 27 | 1 | 3 / 3 / 3 | 0 |
| 3 | 30 / 30 | 29 / 29 / 29 | 1 | 3 / 3 / 3 | 0 |
| 4 | 26 / 26 | 24 / 24 / 24 | 2 | 3 / 3 / 3 | 0 |
| Total | 114 / 114 | 110 / 110 / 110 | 4 | 12 / 12 / 12 | 0 |

All 114 targets validated on their first generation attempt. Semantic-invalid,
sanitized-reference, request-error, and terminal-drop counts were all zero.
The smaller submitted counts in years 2--4 are explicit `submit=false` agent
decisions, not pipeline loss.

## Runtime and cache

The first four-year run built the 2016--2019 retrieval cache on CPU for 103,107
documents. Encoding took 4,323.99 seconds and produced a 158,373,929-byte cache.
The full harness wall time includes this one-time build; subsequent runs with
the same dataset and embedding identity should reuse it. The run recorded 320
LLM prompts, 320 first-attempt successes, zero retries, and zero failures.

## Evidence hashes

- Study snapshot:
  `84018ce106fee482f86a0a1f88771b3333bb7ef5e1ae144f227a1f5712eb6702`
- Registry report generated at `2026-10-25T09:52:54.053073+00:00`:
  `73efad80a3abf27d671ffaba8e53d9fc04d8ea7c387c2ef8cc81a9e04619ffaf`
- Run manifest:
  `4605fb0f207d248028778a8694e574755c85615c7f129c08f1faddbb602047cb`
- Objective evaluation:
  `62db506fc3a0af0bef4a188cba7695b4860965c426613b1c97ff5492d60f0143`
- Funding trace summaries, years 1--4:
  `f2a2118fcf54bc56b14fefc01350ec5a027cb018997595886e6d74ef8bba0ac8`,
  `91dd1ac3258ac0dfb63e86a7e9948f398658998d4d1ec39f30ea2f391c6341f2`,
  `a5fda2c7080bed7920486c6b936fc7c5eb83ad36b68c753882dd062b6aef6e23`,
  `0d816e4f3dc2a06e84e7bb4979c5be84db6a03e49dc30e52f640a51ef7dbe8da`
- Retrieval embedding cache:
  `df41f130a934d2511fa1584df4a553cbc4525a336a83358bb8d6db7462fa6610`

Artifacts are stored below
`outputs/optimization/participation-fidelity-v1/79ec3468cf`; large outputs and
the local cache remain untracked and are represented by this note and hashes.

## Decision

Retain the four-year `longitudinal` fidelity for baseline replication and later
paired institutional comparisons. Complete the four remaining baseline seeds
before ranking, estimate the distribution of aggregate and slice participation,
and only then execute candidate designs on the same seed bundle. The policy is
not recalibrated because all pre-registered conditions passed.
