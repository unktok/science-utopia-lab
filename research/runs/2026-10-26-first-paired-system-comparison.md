# First five-seed longitudinal system comparison

## Question and frozen intervention

In the four-year, 10-researcher ScienceUtopia fidelity, does increasing annual
fixed university funding capacity from 30% to 50% of the initial population
preserve participation, and what trade-offs accompany it? This is a controlled
simulator comparison, not a real-world science-policy estimate.

The candidate `dd6ee5effe4b1` and all analysis rules were fixed before the
remaining baseline outcomes were observed. Funding capacity is the only design
change. Seeds are 101, 103, 107, 109, and 113; no outcome-selected replacement
is permitted.

## Execution and provenance

| Item | Baseline | Candidate |
|---|---|---|
| Study | `longitudinal-comparison-baseline-v1` | `first-candidate-funding-slots-v2` |
| Revision | `fb38800d92` | `5e2b4d9e2f` |
| Design | `dce5399cf6d0b` | `dd6ee5effe4b1` |
| Completed | 5 / 5 | 5 / 5 |
| Failed harness attempts | 0 | 0 |
| Source commit | `c9667d722e40935e5c963bab2037885bf72d8b34` | same |
| Worktree at run start | clean | clean |

The paired analysis verifies, for every seed, equal fidelity, seed, model,
dataset identity, ordered-document hash, retrieval and metric embeddings,
resolved configuration, Python/package versions, source-file hashes,
Constitution, and evaluator producer. It also checks that execution arguments
and design JSON differ only in `funding_budget_slots_frac` (0.3 versus 0.5).

All 10 runs passed four native integrity reports, four funding-trace
conservation reports, funding reliability policy 1.0.0, and complete aggregate
plus fixed low-resource-slice measurement. All ran on Qwen3-8B through local
Ollama.

## Admissibility result

The candidate is feasible in all five worlds. Baseline seed 107 is
`infeasible`, despite being technically sound, because its low-resource active
fraction is 0.4 and the frozen capability floor is 0.5. Aggregate participation
in that world is 0.7.

This is not a reason to remove the seed or lower the threshold. Under the
preregistered decision rule, one infeasible run makes the **formal comparison
incomplete**. The result below is therefore a complete diagnostic paired vector,
not an authorized ranking or promotion decision.

## Paired objective vector

All deltas are candidate minus baseline. Intervals are deterministic
seed-20261025 percentile intervals from 10,000 paired resamples. With only five
pairs they describe simulator-seed uncertainty; they are not hypothesis tests.

| Metric | Baseline mean | Candidate mean | Mean delta | Median delta | Sample SD | Range | 95% interval | + / 0 / − |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| aggregate participation | 0.800 | 0.880 | +0.080 | +0.100 | 0.045 | 0.000–0.100 | 0.040–0.100 | 4 / 1 / 0 |
| low-resource participation | 0.600 | 0.760 | +0.160 | +0.200 | 0.089 | 0.000–0.200 | 0.080–0.200 | 4 / 1 / 0 |
| aggregate review burden | 2.351 | 2.229 | −0.122 | −0.136 | 0.096 | −0.212–0.000 | −0.197–−0.047 | 0 / 1 / 4 |
| low-resource review burden | 2.674 | 2.466 | −0.208 | −0.161 | 0.182 | −0.430–0.000 | −0.349–−0.067 | 0 / 1 / 4 |
| topic entropy | 1.779 | 1.766 | −0.012 | 0.000 | 0.215 | −0.217–+0.328 | −0.165–+0.162 | 1 / 2 / 2 |

Participation improved in four worlds and was unchanged in seed 113. Review
burden per active researcher-step fell in the same four worlds and was unchanged
in seed 113. Topic entropy is mixed and cannot support a monotonic winner claim.

## Seed-level participation

| Seed | Aggregate baseline → candidate | Low-resource baseline → candidate | Eligibility baseline / candidate |
|---:|---:|---:|---|
| 101 | 0.8 → 0.9 | 0.6 → 0.8 | feasible / feasible |
| 103 | 0.9 → 1.0 | 0.8 → 1.0 | feasible / feasible |
| 107 | 0.7 → 0.8 | 0.4 → 0.6 | infeasible / feasible |
| 109 | 0.8 → 0.9 | 0.6 → 0.8 | feasible / feasible |
| 113 | 0.8 → 0.8 | 0.6 → 0.6 | feasible / feasible |

The protected slice does not conceal aggregate harm: its paired change is
nonnegative in all five worlds and twice the aggregate change in the four
changing worlds. This observation does not override the formal admissibility
rule.

## Resource and activity shadows

| Shadow diagnostic | Baseline mean | Candidate mean | Mean paired delta |
|---|---:|---:|---:|
| total grant income | 240 | 400 | +160 |
| applied funding allocations | 12 | 20 | +8 |
| final total resources | 783 | 941 | +158 |
| submitted funding applications | 103.4 | 102.6 | −0.8 |
| papers | 18.0 | 17.6 | −0.4 |
| reviews | 88.2 | 86.0 | −2.2 |
| acceptances | 9.8 | 9.6 | −0.2 |
| wall time, seconds | 5,067.8 | 5,303.1 | +235.3 |

The intervention adds exactly two awards per year, hence eight awards and 160
grant units per world. Final resources rise by 145–165 units in every pair.
The participation gains are therefore not cost-free and the candidate is not
Pareto-dominant under the frozen rule.

## Interpretation

Within these five simulator worlds, broader fixed funding capacity is associated
with greater participation continuity and lower review burden per surviving
researcher-step. The strongest effect is in the initially low-resource group.
One world is unchanged, and topic breadth does not move consistently.

The defensible statement is: **the candidate exhibits a promising
resource-for-continuity trade-off that merits a new, explicitly designed
confirmation stage; this campaign does not authorize ranking it as the better
system.** A confirmation protocol must decide prospectively how capability
violations enter system comparison; it must not reinterpret seed 107 after the
fact.

## Evidence

- Machine report:
  [`../results/first-paired-system-comparison-v1.json`](../results/first-paired-system-comparison-v1.json)
- Generated compact rendering:
  [`2026-10-26-first-paired-system-comparison.generated.md`](2026-10-26-first-paired-system-comparison.generated.md)
- Baseline registry report SHA-256:
  `8ce8796859de39ed7388b3ef3939365c7c82efaffbf3d2d1db4697211fec3f88`
- Candidate registry report SHA-256:
  `c13e0feb2821ea41230fff2bcd4ab375bf3f0d596f77c9e41e32f456f8af9134`
- Paired report SHA-256 before this documentation commit:
  `f6a1f7f69033e861c53b215f5a197636f203824348e7ec4221a6d262391363bc`

Reproduction command:

```bash
.venv/bin/python -m utopia.optimization.paired_comparison \
  --baseline-root outputs/optimization/longitudinal-comparison-baseline-v1/fb38800d92 \
  --candidate-root outputs/optimization/first-candidate-funding-slots-v2/5e2b4d9e2f \
  --json-output research/results/first-paired-system-comparison-v1.json \
  --markdown-output research/runs/2026-10-26-first-paired-system-comparison.generated.md
```
