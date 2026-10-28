# Metric-conditioned experimental figures

This directory is the legacy standalone graphics boundary. The manuscript now
uses the atomic report slice under `paper/generated/metric-conditioned/`.
Standalone regeneration here still expects all three experimental PDFs or none:

- `metric-conditioned-cross-evaluation.pdf`
- `metric-conditioned-objective-trajectories.pdf`
- `metric-conditioned-tradeoff-rank-generalization.pdf`

The graphics CLI rejects synthetic fixtures at this destination. Test previews
belong under `tmp/`, carry an in-figure synthetic warning, and must never be
copied here.
