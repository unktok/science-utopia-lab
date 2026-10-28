# Decision 0010: Publish the completed metric-conditioned study as one atomic paper slice

- Status: accepted implementation boundary
- Date: 2026-10-28
- Applies to: metric-conditioned optimization v1.1 and later compatible studies

## Decision

The completed three-LossSpec comparison is converted into paper evidence by one
fail-closed command. The command reads only sealed experiment artifacts:

- the versioned study manifest;
- all three campaign snapshots, terminal states, and read-only registries;
- the simultaneous winner freeze;
- the sealed common held-out snapshot and registry; and
- the final cross-evaluation report.

It validates the complete provenance and seed chain before writing anything.
Outputs are first written into a temporary sibling directory and then published
with one atomic rename. Existing outputs are never silently overwritten.

## Completion gate

Publication is refused unless all of the following hold:

1. the manifest declares exactly three distinct LossSpecs and `report_only`;
2. each arm used the full suggestion budget and has only terminal suggestions;
3. each frozen winner is one complete suggestion and all three campaign
   revisions match the simultaneous freeze;
4. all campaign snapshots record the same clean, pinned source commit;
5. the held-out snapshot matches the freeze and contains every arm on the five
   preregistered held-out seeds;
6. every optimization and held-out registry row is complete;
7. the cross-objective matrix is exactly 3 by 3, every cell has all five seeds,
   and no cell contains a missing value or missing reason;
8. every declared held-out metric profile is complete; and
9. the report contains rank reversal, paired trade-off, gaming,
   generalization, and secondary-resolution analyses with no report errors.

Thus a partial arm, an unfinished held-out run, a stale freeze, a dirty source
snapshot, or a missing metric cannot become a paper result.

## Statistical and scientific interpretation

The scientific intervention is the optimization `LossSpec`. Simulator,
design space, optimizer, suggestion budget, development seeds, and held-out
seeds remain controlled across arms. The primary objects reported are the
three frozen institutional designs and their behavior under every objective.

For every cross-objective cell, the slice reports the frozen LossSpec aggregate
and an exact nonparametric bootstrap percentile interval. With five held-out
seeds this enumerates all $5^5=3{,}125$ resamples and recomputes the complete
`mean + dispersion_weight * population_sd` aggregate. Scalar held-out metrics
use two-sided 95% Student-*t* intervals across the five common seeds. Pairwise
effects are paired left-minus-right contrasts on common seeds. These are
descriptive uncertainty intervals for the simulated worlds, not population
causal estimates about real science systems.

The generated prose is conditional on the observations. It says that
objectives selected different systems only if frozen design IDs differ, and it
claims a rank reversal only if the best system changes across held-out losses.
Topic entropy and review burden remain narrow contrastive proxies, not
normative recommendations. No universal winner is selected.

## Runtime accounting

Runtime is read from registries in read-only SQLite mode. Logical runs linked
through provenance-safe artifact adoption are counted as logical observations
but not again as physical compute. The report separately records logical,
physical, and adopted optimization counts, held-out runs, failed attempts, per
run runtime summaries, and total physical wall-seconds.

## Outputs

The atomic output directory contains:

- `metric-conditioned-paper-slice.json`: complete machine-readable analysis;
- `metric-conditioned-figure-data.json`: plotted-data boundary;
- cross-objective loss, held-out metric, paired-effect, winner-design, and
  runtime CSV tables;
- a generated Markdown result report;
- a generated LaTeX fragment;
- three publication figures in requested formats; and
- an artifact manifest with SHA-256 and byte size for every generated file.

The working paper includes the fragment only when the fragment and all three
PDFs exist. Synthetic fixtures are watermarked and are prohibited from the
paper output path.

## v1.1 invocation

After the study controller reports a complete held-out report, run from the
repository root, substituting the revisions printed by the controller:

```bash
PYTHONPATH=. ~/.local/bin/python3 -m scripts.reports.metric_conditioned_paper_slice \
  --manifest research/specs/metric-conditioned-optimization-study-v1-1.json \
  --study-root outputs/optimization/metric-conditioned-v1-1/metric-conditioned-optimization-v1-1/<study-revision> \
  --campaign-root metric-conditioned-participation-review-v1-1=outputs/optimization/metric-conditioned-v1-1/metric-conditioned-participation-review-v1-1/<arm-revision> \
  --campaign-root metric-conditioned-topic-diversity-v1-1=outputs/optimization/metric-conditioned-v1-1/metric-conditioned-topic-diversity-v1-1/<arm-revision> \
  --campaign-root metric-conditioned-review-burden-v1-1=outputs/optimization/metric-conditioned-v1-1/metric-conditioned-review-burden-v1-1/<arm-revision> \
  --classification experimental \
  --output-dir paper/generated/metric-conditioned \
  --formats pdf,png
```

The command does not execute simulations, mutate registries, refreeze winners,
or choose a policy. It only validates and reports already sealed evidence.
