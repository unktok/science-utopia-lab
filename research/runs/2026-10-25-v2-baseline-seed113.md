# v2 baseline seed 113 end-to-end acceptance run

## Identity

- Date: 2026-10-25
- Status: complete; engineering acceptance gate passed
- Purpose: validate the repaired funding interface and comparison-admissibility
  gate inside a complete simulator run before any candidate design is run
- Study / revision: `evaluation-v2` / `54e12434e7`
- Run ID:
  `opt-evaluation-v2-54e12434e7-smoke-exploration-dce5399cf6d0b-s113`
- Design ID: `dce5399cf6d0b` (baseline)
- Seed / role: 113 / exploration
- Source commit: `c428a7a3438bb502bad209ecbbd0a3a970fd827e`
- Model / backend: `qwen3:8b` / Ollama OpenAI-compatible endpoint
- Fidelity: one year, 2 institutions, 10 researchers, 1 conference
- Wall time: 793.91 seconds

Seed 113 was selected prospectively because it was the strongest v1 funding
stress case: 47 of 74 generation attempts were semantically invalid and 8 of
10 researchers had no past papers. The remaining 24 v2 runs stayed planned.

## Acceptance result

The run completed on its first harness attempt. Native integrity and funding
trace integrity both passed, the objective evaluator reported no measurement
gaps, and the run was `feasible`. Funding reliability policy
`funding-pipeline-reliability` version `1.0.0` returned `state=pass`,
`disposition=eligible`, and `comparison_eligible=true`.

| Funding stage or diagnostic | Count |
|---|---:|
| Targets | 30 |
| Validated | 30 |
| Submitted | 30 |
| Evaluated | 30 |
| Decided | 30 |
| Funded | 3 |
| Allocations recorded / applied | 3 / 3 |
| Generation attempts | 30 |
| Semantic-invalid attempts | 0 |
| Sanitized-reference attempts | 0 |
| Request-error attempts | 0 |
| Terminal drops | 0 |

All four reliability rates were therefore zero. The trace is
`scienceutopia.funding_application_trace.v2`, reports `passed=true`, and has no
conservation failures. Unlike the earlier ten-target probe, this run includes
proposal evaluation, funding decisions, and resource application, so it closes
the full pipeline.

## Scientific measurements

| Measurement | Aggregate | Low-resource slice |
|---|---:|---:|
| Active-researcher fraction | 1.0 | 1.0 (support 5) |
| Review burden / active researcher-step | 0.6 | 0.6 (support 5) |
| Topic entropy | 2.1639556569 nats | not slice-defined |

The run produced 2 papers, 6 reviews, and 1 acceptance. The participation
capability and hard integrity constraint passed. These values are one
realization and are not evidence that the baseline is better than another
system. Design-level `authorized_for_ranking` remains false because v2 has only
1 of the required 5 baseline repetitions.

## Evidence hashes

- Study snapshot:
  `d52c1ad6315dfffe5dfe0cb26fc46804797c2aaa77986739ce8682bbac213009`
- Registry report generated at `2026-10-25T07:01:17.596640+00:00`:
  `aece7331ed67c760f5702e657b1641f5eaf84c86b21315aec20d19e7f2b02d52`
- Run manifest:
  `15afc357ca40a15472dadd60238faf86e6a0497e5fb80d997857a25c9abdd7e4`
- Objective evaluation:
  `f3efd265434878fa56e5e0796101d30f9c478bd7fd86020572df767cc170d41a`
- Funding trace JSONL:
  `217b1a38243adf57032307226fc261a5e2c5a53e4bfd07a866aa8b51081e76f8`
- Funding trace summary:
  `f2a2118fcf54bc56b14fefc01350ec5a027cb018997595886e6d74ef8bba0ac8`

Artifacts are stored below
`outputs/optimization/evaluation-v2/54e12434e7`; large outputs remain local and
are represented in version control by this note and their content hashes.

## Decision

The funding-interface acceptance gate is satisfied. Candidate execution is no
longer blocked by issue #7. This does not authorize a cross-design ranking: the
one-year participation metric is still ceiling-saturated, and the v2 baseline
still lacks four repetitions. The next methodological gate is to define a
longer-horizon fidelity that makes participation continuity informative, then
pilot it on the baseline before spending the candidate-run budget.
