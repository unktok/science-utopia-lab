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
