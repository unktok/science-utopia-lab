# Measurement-complete v1 baseline: five-seed result

## Identity

- Date: 2026-10-25
- Status: complete
- Purpose: establish the seed variance and protected-slice measurement behavior of the baseline system before comparing institutional designs
- Study / revision: `evaluation-v1` / `1cc1b68161`
- Design: baseline (`dce5399cf6d0b`)
- Fidelity / seed role: smoke / exploration
- Seeds: 101, 103, 107, 109, 113
- Backend / model: Ollama / `qwen3:8b`
- Metric Constitution: `science-utopia-example` `1.1.0-draft.1`
- Metric Constitution SHA-256: `c9ce39717fb6ff9a665479c3a6cc6a3ee38c553fb86039a253addb70332662d1`
- Evaluator: `harness-metric-evaluator` `1.1.0`
- Evaluator implementation SHA-256: `98ae6a8e44ca2c20d4b0d31a95c0b8f22de31a3bf73260afeb36aa2f20510702`
- Scientific configuration SHA-256: `7e9ee9fb61f9773444baccc13da86a5a3a03785505206a60345b1eeb3a980a23`

Seed 101 was produced from source commit `9cf9f3b590703908fef20012344e53915224da2f`.
Seeds 103, 107, 109, and 113 were produced from
`b09d405a8dbce9dc09981055256391b9bf430fab`; the intervening commit changed
research documentation only. All five runs have the same scientific
configuration hash, evaluator version and implementation hash, and
constitution hash.

## Completion and objective results

All five runs completed on their first harness attempt. Every native integrity
check and funding conservation check passed, all required aggregate and
low-resource-slice metrics were measured, and every run was classified
`feasible` with zero measurement gaps.

| Seed | Wall time (s) | Active: all / low | Review burden: all / low | Low − all | Topic entropy (nats) |
|---:|---:|---:|---:|---:|---:|
| 101 | 1587.75 | 1.0 / 1.0 | 0.6 / 1.2 | +0.6 | 2.025326 |
| 103 | 1604.50 | 1.0 / 1.0 | 0.9 / 1.0 | +0.1 | 1.886697 |
| 107 | 1624.39 | 1.0 / 1.0 | 1.5 / 1.0 | −0.5 | 1.695743 |
| 109 | 1299.29 | 1.0 / 1.0 | 0.3 / 0.0 | −0.3 | 2.163956 |
| 113 | 2025.76 | 1.0 / 1.0 | 0.6 / 0.6 | 0.0 | 2.163956 |

The design-level summaries are:

| Metric | Mean | Median | Observed range | Sample SD |
|---|---:|---:|---:|---:|
| Active researcher fraction, all | 1.000 | 1.000 | 1.000–1.000 | 0.000 |
| Active researcher fraction, low-resource slice | 1.000 | 1.000 | 1.000–1.000 | 0.000 |
| Review burden, all | 0.780 | 0.600 | 0.300–1.500 | 0.455 |
| Review burden, low-resource slice | 0.760 | 1.000 | 0.000–1.200 | 0.477 |
| Low-resource minus aggregate burden | −0.020 | 0.000 | −0.500–0.600 | 0.421 |
| Topic entropy | 1.987 | 2.025 | 1.696–2.164 | 0.199 |

A nonparametric 95% seed-bootstrap interval for mean participation is
necessarily `[1.0, 1.0]` for both the aggregate and protected slice because
every possible resample contains only observed values equal to one. This is a
ceiling-saturated smoke result, not strong evidence that the system preserves
participation over meaningful time horizons. The one-year fidelity cannot
identify attrition effects and should not be used for that substantive claim.

The low-resource review-burden difference changes sign across seeds. Seed 101
concentrated every review in the lower band, while seed 109 assigned none
there. The near-zero mean difference therefore does not show equal burden; it
averages over large and directionally unstable allocations. Per-seed and slice
distributions must remain visible in all design comparisons.

The report now marks the baseline `authorized_for_ranking=true`: the design has
five feasible runs, no unknown constraint or capability state, and satisfies
the declared minimum replication count. This is only a procedural eligibility
gate. No other v1 design has completed runs, so no institutional ranking or
optimality claim is available.

## Activity diagnostics

Across the five runs, the simulator produced 13 papers, 39 review actions and 6
accepted papers. Per run, papers ranged from 1 to 5 and reviews from 3 to 15.
Final active researchers were 10 in every run. These are activity diagnostics,
not scientific-value objectives.

The total wall time was 8,141.69 seconds (2 hours 15 minutes 42 seconds), with a
median of 1,604.50 seconds and an observed range of 1,299.29–2,025.76 seconds.

## Funding-pipeline reliability

The five conservation traces reconcile exactly:

```text
132 targets
  = 126 validated + 6 terminal drops
  = 121 submitted + 5 declined_by_agent + 6 terminal drops
  = 121 evaluated
  = 121 decided
  -> 15 funded
  = 15 allocations recorded
  = 15 allocations applied
```

- Generation attempts: 260
- Semantic-invalid attempts: 134 (51.5% of generation attempts)
- Request-error attempts: 0
- Terminal drops: 6 (4.5% of targets)
- Seed 113: 47 semantic-invalid attempts out of 74, and 3 drops out of 30 targets

There is no silent attrition or transport failure, but the semantic-invalid
rate is too high to treat as harmless runtime noise. The recurring failure is
invalid paper-index selection, especially when few papers are available. It
can alter which applications enter evaluation, consume substantial compute,
and become entangled with design effects. Before cross-design comparison, add
an engineering reliability gate and repair or constrain this interface in a
new versioned campaign. Do not change the frozen evaluator or artifacts of
revision `1cc1b68161`. The repair and gate are tracked in repository issue #7.

## Evidence hashes

- Study snapshot: `8e8fe7a5455e9057ae313ad70c08de5522d94480f9bfa64250030507ff537af5`
- Registry report: `d95914ea33b81208fe6f5870ed831d6b99f4c12a2599cf7aca6eda01f61be213`
- Objective evaluation, seed 101: `8d84a5b41cefa6d90a8b1e734a28367d9489fd1654dda4672c52dbab7360f554`
- Objective evaluation, seed 103: `04801c76932a119787e3dfcdec1cff1f4d908b7e2221f824fc11917044c121ec`
- Objective evaluation, seed 107: `dc5da7442b33dabfe6cd0e18e1d820c22164b13dcda1989e581eb13af6e0f075`
- Objective evaluation, seed 109: `73b56752337fc1ab055bf0f62284ed2c5464ee110c2411dbdc99bfad43429767`
- Objective evaluation, seed 113: `adf19562cb64114d087f37e15261c5ed887659e8f0dd86c30ff6587a7d492515`

## Validation

- Optimization suite: 26 passed.
- Offline full suite: 596 passed, 2 skipped, 7 deselected, 7 failed.
- Six failures are the already-recorded prospective-logging tests that patch
  the absent `utopia.experiments.funding_feedback.subprocess` attribute.
- One additional failure is
  `test_initializer_year_zero_resume_keeps_common_choices_and_uses_cached_replies`;
  it reproduces in isolation at the unchanged source revision with
  `refuse_to_replace_different_initial_choices`.

This result change only edits research documentation; it does not modify the
simulator, evaluator, or the failing switching code. The additional upstream
failure is therefore recorded as repository issue #8 rather than
silently folded into this campaign's validation.

## Next gate

Do not infer an optimal science system from this baseline. Before spending the
remaining 20 smoke runs, version and test a funding-proposal reliability fix,
define a quantitative gate for semantic-invalid and terminal-drop rates, and
decide whether the current v1 campaign remains a diagnostic archive or whether
cross-design comparison restarts under a new study revision. In parallel,
introduce a longer-horizon fidelity so participation is not ceiling-saturated.
