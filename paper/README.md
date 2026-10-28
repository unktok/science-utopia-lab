# Working paper

This directory contains the source for the preliminary NeurIPS-style technical
report. It is a working draft, not a conference submission or acceptance claim.
The repository vendors the official `neurips_2025.sty` because the NeurIPS 2026
style bundle was not available when this draft was created.

## Build

From the repository root:

```bash
cd paper
/opt/homebrew/bin/tectonic --keep-logs --keep-intermediates \
  --outdir ../tmp/pdfs main.tex
cp ../tmp/pdfs/main.pdf ../output/pdf/science-utopia-lab-working-paper.pdf
```

The final shareable artifact is
`output/pdf/science-utopia-lab-working-paper.pdf`. Intermediate files stay under
`tmp/pdfs/` and are ignored by Git.

## Evidence boundary

The paper reports the first completed result-dependent engineering campaign. It
does not claim a validated science-policy objective, a held-out result, or a
structurally optimized institution. Update the paper only alongside the cited
protocols, compact results, and artifact manifests.

## Metric-conditioned result boundary

`metric_conditioned_results.tex` is a guarded insertion point for the
preregistered three-arm study. It includes results only when all three PDFs are
present under `figures/metric-conditioned/`; otherwise the manuscript states
that the study is incomplete. The reproducible command and chart semantics are
recorded in
`research/decisions/0009-metric-conditioned-results-graphics-pipeline.md`.

Never copy a synthetic preview into the paper directory. The graphics CLI
requires an explicit synthetic classification, places a warning inside every
synthetic image, and rejects that classification at the paper destination.
