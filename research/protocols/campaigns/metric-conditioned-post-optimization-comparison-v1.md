# Metric-conditioned post-optimization comparison v1

Status: ready for use after the v1.1 optimization completion package and
before any held-out execution.

## Purpose

Produce the compact 3 frozen winners × 3 LossSpecs comparison that answers
which institutional system each optimization objective selected and what
development-world trade-offs separate those systems.

This is a projection of the sealed optimization-completion evidence. It does
not run the simulator, re-open campaign registries, select another candidate,
or estimate held-out generalization.

## Required input

- The generated
  `metric-conditioned-optimization-completion.json` from the Decision 0012
  package.
- The exact three winner fingerprints printed by the simultaneous freeze.

The completion report has already recomputed all candidates under every
LossSpec from development evaluations. The focused builder verifies the winner
fingerprints, matrix equality, common seed set, mean, and population SD before
publishing any result.

## Invocation

```bash
PYTHONPATH=. ~/.local/bin/python3 \
  -m scripts.reports.metric_conditioned_post_optimization_comparison \
  --completion-report <completion-package>/metric-conditioned-optimization-completion.json \
  --winner-fingerprint metric-conditioned-participation-review-v1-1=<sha256> \
  --winner-fingerprint metric-conditioned-topic-diversity-v1-1=<sha256> \
  --winner-fingerprint metric-conditioned-review-burden-v1-1=<sha256> \
  --output-dir research/results/generated/metric-conditioned-post-optimization-v1-1/<study-revision>
```

There is intentionally no option for a held-out seed, registry, snapshot,
evaluator, or output. Do not substitute an intermediate campaign snapshot for
the completed Decision 0012 report.

## Atomic output package

- `post-optimization-comparison.json`: versioned machine-readable report;
- `cross-objective-matrix.csv`: nine winner/loss cells with uncertainty and
  rank;
- `pareto-tradeoffs.csv`: three winner pairs × three objective deltas;
- `seed-uncertainty.csv`: all 27 development seed/loss observations and
  executed/adopted provenance;
- `runtime-provenance.csv`: global and per-arm run modes, attempt statuses,
  wall time, source commit, and winner-freeze hash;
- `post-optimization-comparison.tex`: paper table with conditional Pareto marks;
- `figures/post-optimization-comparison.svg`: dependency-free paper figure;
- `post-optimization-comparison.md`: guarded human summary; and
- `artifact-manifest.json`: content hashes and sizes.

The output directory is published by atomic rename and is never overwritten.
Synthetic fixture output includes a visible `SYNTHETIC TEST ONLY` watermark and
cannot be written into `paper/generated/metric-conditioned`.

## Reading the result

All losses are minimized. Matrix shading and ranks are computed separately
within each LossSpec because the raw loss units differ. A pair is a trade-off
when each system is better under at least one declared objective. A system is
conditionally Pareto-dominated only when another frozen system is no worse on
all three losses and strictly better on at least one.

The three-seed intervals and dispersion describe optimization-world
sensitivity. They are not confidence intervals for real science and not
held-out generalization intervals. Non-complete physical attempts remain in
the runtime/failure summary even though all logical runs must be complete.

## Next boundary

Archive and review this package. Only then follow the preregistered study
controller for the separately sealed common held-out evaluation. Use Decision
0010, not this package, for generalization gaps and final manuscript claims.
