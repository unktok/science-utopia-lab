# Metric-conditioned held-out release v1

Status: implementation-ready; no active held-out value was inspected while
developing or testing this release path.

## Purpose

Turn the completed Metric-Conditioned Optimization Study v1.1 held-out split
into one auditable cross-evaluation and NeurIPS working-paper slice without
allowing a partial run, stale report, synthetic fixture, or post-hoc policy
rule to become a scientific result.

This release path preserves four distinct objects:

1. `LossSpec`: the development-world quantity that changed across optimization
   arms and directly drove `optimizer.tell`;
2. technical validity: whether a simulator execution is an admissible
   observation, never a numeric loss penalty;
3. held-out metrics: common untouched measurements used to characterize the
   three already-frozen systems; and
4. optional promotion policy: absent in v1.1 (`report_only`) and never inferred
   from a protected slice or gaming diagnostic.

## Pre-value readiness gate

Run this from a clean development or integration worktree:

```bash
PYTHONPATH=. .venv/bin/python \
  -m scripts.reports.metric_conditioned_heldout_release check \
  --study-root <metric-conditioned-v1.1-study-root>
```

The check opens only `winner-freeze.json`, the sealed held-out snapshot, and
the result-blind `scienceutopia.held-out-progress.v1` projection from the
read-only registry. It deliberately does **not** open `cross-evaluation.json`
or any raw simulator output. The canonical progress gate opens
`ready_for_report` when every row is terminal, so the commit-pinned controller
can faithfully report technical failures. The stricter publication gate opens
only when all 15 rows are complete. Terminal technical failures do not receive
fabricated losses and keep the paper release closed.

## Commit-pinned report generation

After `ready_for_report: true`, run `report-evaluation` using the experiment's
commit-pinned controller worktree. This is the only step that reads raw
held-out output and writes `cross-evaluation.json`:

```bash
PYTHONPATH=. .venv/bin/python scripts/run_metric_conditioned_study.py \
  --study research/specs/metric-conditioned-optimization-study-v1-1.json \
  report-evaluation
```

Do not run this command from a newer development checkout against the active
registry. The dedicated experiment worktree remains the authority for turning
its raw outputs into the versioned report.

## Atomic validation and paper publication

From the reviewed integration revision, publish the final slice:

```bash
PYTHONPATH=. .venv/bin/python \
  -m scripts.reports.metric_conditioned_heldout_release publish \
  --manifest research/specs/metric-conditioned-optimization-study-v1-1.json \
  --study-root <study-root> \
  --campaign-root metric-conditioned-participation-review-v1-1=<arm-root> \
  --campaign-root metric-conditioned-topic-diversity-v1-1=<arm-root> \
  --campaign-root metric-conditioned-review-burden-v1-1=<arm-root> \
  --classification experimental \
  --output-dir paper/generated/metric-conditioned \
  --formats pdf,png
```

The publisher rechecks the readiness gate before reading report values. It
then verifies the sealed revision/freeze chain, frozen designs, controlled
study fields, exact 3-by-3 loss matrix, five common seeds per cell, complete
metric profiles, scalar and structured summaries, all common-run evaluations,
and an exact recomputation of preregistered rank-reversal, trade-off, gaming,
generalization, and resolution analyses. Registries are opened read-only.

Publication is staged in a temporary sibling directory and installed by one
atomic rename. Existing output is never overwritten. The working paper's
guarded LaTeX boundary activates only when the generated fragment and all
three final PDFs are present together.

## Outputs and interpretation boundary

The package contains the cross-objective loss table, metric table, paired
effects, winner designs, runtime accounting, rank reversal/trade-off/gaming/
generalization figures, generated Markdown, generated LaTeX, compact plotted
data, and a hash manifest. The methods flow figure in
`paper/metric_conditioned_methods_flow.tex` is result-independent.

These artifacts compare objective-conditioned simulated institutions. They do
not select a universal winner, add a promotion veto, or support a real-world
science-policy optimum claim.
