# Decision 0009: Generate study figures from a sealed machine-readable summary

- Status: graphics component retained; direct manuscript publication superseded
  by Decision 0010
- Date: 2026-10-28
- Scope: scientific graphics and NeurIPS working-paper insertion boundary

## Decision

Metric-conditioned result figures have a two-stage evidence boundary:

1. normalize the sealed cross-evaluation report plus the three completed arm
   campaign states into
   `scienceutopia.metric-conditioned-figure-data.v1`; and
2. render every publication figure from that compact JSON alone.

The compact summary is the plotted-data record. It retains the source report
hash, study identity and revision, arm trajectories, all nine cross-evaluated
losses, held-out metric summaries, rank reversal, paired trade-offs, gaming
flags, generalization gaps, and secondary-resolution labels. Rendering does not
read simulator output or recompute scientific metrics.

## Figures and semantics

The pipeline creates exactly three named figures:

1. `metric-conditioned-cross-evaluation`: frozen systems by held-out loss.
   Because the three losses have different units, annotations show raw loss
   (and, when supplied by the full report slice, its uncertainty interval)
   while color shows rank *within each loss column*. Lower loss is better.
2. `metric-conditioned-objective-trajectories`: one panel per arm with raw
   development observations, the incumbent trace, and the frozen winner.
   Panels have separate objective units; their vertical values must not be
   compared across arms.
3. `metric-conditioned-tradeoff-rank-generalization`: the held-out activity vs
   review-burden trade-off with population-SD error bars, loss-rank reversal,
   and held-out-minus-development generalization gap.

These figures answer which systems different objectives produce. They do not
identify a universally or normatively best science system. In particular,
topic entropy and review burden are narrow proxy arms used to expose objective
dependence, not policy recommendations.

## Experimental invocation

For the completed study, use Decision 0010's automatic paper-slice command so
the completion, uncertainty, runtime, and provenance gates run together. The
lower-level invocation below remains useful for standalone figure regeneration.

After all three arm campaigns are complete, the winners are frozen, and the
common held-out report exists, run from the repository root (replace revision
placeholders with the directories recorded by the study status command):

```bash
PYTHONPATH=. ~/.local/bin/python3 -m scripts.figures.metric_conditioned_results \
  --input outputs/optimization/metric-conditioned-v1/metric-conditioned-optimization-v1/<study-revision>/held-out-evaluation/cross-evaluation.json \
  --campaign-state metric-conditioned-participation-review-v1=outputs/optimization/metric-conditioned-v1/metric-conditioned-participation-review-v1/<participation-review-revision>/campaign-state.json \
  --campaign-state metric-conditioned-topic-diversity-v1=outputs/optimization/metric-conditioned-v1/metric-conditioned-topic-diversity-v1/<topic-diversity-revision>/campaign-state.json \
  --campaign-state metric-conditioned-review-burden-v1=outputs/optimization/metric-conditioned-v1/metric-conditioned-review-burden-v1/<review-burden-revision>/campaign-state.json \
  --classification experimental \
  --summary-output research/results/metric-conditioned-optimization-v1.figure-data.json \
  --out-dir paper/figures/metric-conditioned \
  --formats pdf,png
```

The input report and campaign states remain immutable experimental artifacts.
The compact JSON and PDFs are reviewable paper inputs. Reviewers should check
the recorded source hash and the arm/study revisions before accepting them.

## Synthetic-fixture safeguards

`tests/fixtures/metric-conditioned-figure-data.synthetic-test.json` exists only
to exercise layout before the long experiment finishes. It is explicitly
classified `synthetic_test_fixture`. Synthetic rendering requires the explicit
`--classification synthetic-test` flag, every synthetic image carries a red
in-figure warning, and the CLI refuses to write a synthetic image under
`paper/figures/metric-conditioned/`.

The paper includes the study figures only when all three experimental PDFs are
present. Until then it renders a result-boundary notice. A synthetic preview,
partial arm, preliminary profile, or missing-value placeholder is never a
paper result.

## Consequences

- A changed figure can be traced to a changed compact summary or rendering
  code; metric computation is outside the renderer.
- Raw losses are not falsely compared through a shared color scale.
- Objective trajectories are not falsely treated as commensurate.
- Real results can replace the guarded empty boundary without editing paper
  prose or plotting code.
- Any future change to plotted fields requires a new summary schema version.
