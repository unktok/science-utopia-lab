# Metric-conditioned experimental figures

`optimization-stage.{pdf,png}` is the frozen development-only progress figure.
It is reproducibly generated from the tracked compact result by:

```bash
PYTHONPATH=. .venv/bin/python \
  -m scripts.figures.metric_conditioned_optimization_snapshot
```

The figure refuses a consumed held-out split and visibly labels its evidence
boundary. It is separate from the final held-out graphics boundary.

The remaining files in this directory are the legacy standalone final-result
boundary. The manuscript now uses the atomic final report slice under
`paper/generated/metric-conditioned/`.
Standalone regeneration here still expects all three experimental PDFs or none:

- `metric-conditioned-cross-evaluation.pdf`
- `metric-conditioned-objective-trajectories.pdf`
- `metric-conditioned-tradeoff-rank-generalization.pdf`

The graphics CLI rejects synthetic fixtures at this destination. Test previews
belong under `tmp/`, carry an in-figure synthetic warning, and must never be
copied here.
