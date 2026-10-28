# Metric-conditioned optimization completion analysis v1

Status: implementation runbook; development-only analysis after the v1.1
winner freeze and before `plan-evaluation`.

## Purpose

Generate the first complete comparison of which institutional system each of
the three frozen optimization objectives selected, while mechanically proving
that the held-out split remains unused. The report is diagnostic development
evidence, not the final held-out study result.

## Preconditions

- All three v1.1 arms have five `observed_complete` suggestions.
- Each suggestion has exactly the common three development seeds.
- The study controller has atomically frozen one winner per arm.
- `held-out-evaluation/runs.sqlite3`, `snapshot.json`, and
  `cross-evaluation.json` are absent.
- The source snapshots are clean and share the experiment commit.

Do not run `plan-evaluation` before this package is generated. If held-out
planning has started, this development-only command intentionally refuses and
the final Decision 0010 pipeline becomes the applicable analysis path.

## Invocation

Run from the repository root after replacing every revision placeholder with
the values printed by the study controller:

```bash
PYTHONPATH=. ~/.local/bin/python3 -m scripts.reports.metric_conditioned_optimization_completion \
  --manifest research/specs/metric-conditioned-optimization-study-v1-1.json \
  --study-root outputs/optimization/metric-conditioned-v1-1/metric-conditioned-optimization-v1-1/<study-revision> \
  --campaign-root metric-conditioned-participation-review-v1-1=outputs/optimization/metric-conditioned-v1-1/metric-conditioned-participation-review-v1-1/<arm-revision> \
  --campaign-root metric-conditioned-topic-diversity-v1-1=outputs/optimization/metric-conditioned-v1-1/metric-conditioned-topic-diversity-v1-1/<arm-revision> \
  --campaign-root metric-conditioned-review-burden-v1-1=outputs/optimization/metric-conditioned-v1-1/metric-conditioned-review-burden-v1-1/<arm-revision> \
  --classification experimental \
  --output-dir research/results/generated/metric-conditioned-optimization-completion-v1-1/<study-revision> \
  --formats pdf,png
```

The command refuses to overwrite an existing output directory. Preserve the
printed paths and `artifact-manifest.json` with the study log. It does not
modify any campaign or study artifact.

## Package contract

- `metric-conditioned-optimization-completion.json`: versioned complete report;
- `development-candidates.csv`: 15 candidates and objective-specific selection
  loss/dispersion/provenance;
- `development-cross-objective.csv`: 3 frozen systems by 3 LossSpecs;
- `frozen-winner-systems.csv`: selected design parameters per arm;
- `metric-conditioned-optimization-completion.md`: guarded generated summary;
- `figures/metric-conditioned-optimization-completion.{pdf,png}`: paper-ready
  progress figure with development-only banner; and
- `artifact-manifest.json`: SHA-256 and byte size for every generated input to
  the package manifest.

The figure shows each arm's five-candidate trajectory, development-seed mean
and population dispersion, frozen winner, the 3-by-3 cross-objective ranks,
and executed/adopted logical-run accounting. Raw values from different
LossSpecs are never placed on one shared quantitative axis.

## Next boundary

After reviewing this immutable completion package, follow the preregistered
study controller to plan and run the five common held-out seeds. Generate the
final manuscript evidence only through Decision 0010's atomic paper slice.
