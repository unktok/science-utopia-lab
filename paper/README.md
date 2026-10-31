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

The paper reports the first result-dependent engineering campaign, the complete
Metric-Conditioned Optimization Study v1.1 including its guarded held-out slice,
and separate small native-world integration/source/wiring/conditional-gradient
probes. It does not claim a validated science-policy objective, successful useful
LLM institutional invention, optimizer superiority or full native-world autograd.
The parameter study remains fixed-topology; later native edits are executable
but development-only. Update only alongside the cited compact results and hashes.

The native fitting graphic is reproducible without model calls:

```bash
.venv/bin/python -m scripts.figures.native_design_evidence
```

The current native-foundry image is an actual browser capture of the read-only
English game interface. Its control-room art is schematic, not scientific state.

## Metric-conditioned result boundary

`metric_conditioned_results.tex` is a guarded insertion point for the
preregistered three-arm study. It includes results only when the generated
LaTeX fragment and all three PDFs are atomically present under
`generated/metric-conditioned/`; otherwise the manuscript states that the
study is incomplete. The one-command analysis and reporting boundary is
recorded in
`research/decisions/0010-metric-conditioned-automatic-paper-slice.md`.

Never copy a synthetic preview into the paper directory. The graphics CLI
requires an explicit synthetic classification, places a warning inside every
synthetic image, and rejects that classification at the generated paper
destination.
