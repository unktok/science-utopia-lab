# Objective-conditioned institution paper

The current short working draft is [submission.tex](submission.tex), following
[the claim-centered outline](submission-outline.md) and
[publication research plan](../research/publication/plan.md).
It centers the scientific question, executable design space, matched comparison,
mechanistic analysis and limitations, not the chronological debugging history.

The old [main.tex](main.tex), its figures and historical shareable PDF are
preserved. The previous long README is retained verbatim in the
[historical manuscript ledger](historical-manuscript.md). Its old experiment
counts and running-looking statements are historical, not current status.

## Evidence and scope

The first same-source feedback comparison uses frozen2e375c2, fixed8B
researchers, the already approved local35B designer, two objectives, two
proposal policies, and two generations. It is a development pilot, not held-out
confirmation or a complete conference study. See [current status](../research/STATUS.md)
and the [prospective protocol](../research/protocols/campaigns/native-feedback-comparison-v1-a1.md).
At this entry's first revision the run is still executing; result numbers are
not filled from partial progress or test fixtures.

The result table is generated from the source-bound audit summary rather than
transcribed. Nulls, all candidates, exact ties and cross-objective selection
remain in the JSON; rendering rounds numbers only for display. The plotting
module emits a full dashboard and a separate print-sized path panel. Original-
source audits must run from the matching frozen checkout, not a later main.

## Build without fetching dependencies

From the repository root, with the existing Tectonic cache:

```bash
mkdir -p tmp/pdfs/current output/pdf
cd paper
/opt/homebrew/bin/tectonic --only-cached --untrusted --keep-logs \
  --keep-intermediates --outdir ../tmp/pdfs/current submission.tex
cp ../tmp/pdfs/current/submission.pdf \
  ../output/pdf/science-utopia-lab-objective-design-draft.pdf
```

Render every final PDF page with Poppler and visually inspect it before sharing.
The final PDF location is `output/pdf/science-utopia-lab-objective-design-draft.pdf`;
build/render intermediates remain ignored under `tmp/pdfs/`.

The bundled NeurIPS2025 style is a working layout, not compliance with an
unverified future conference's rules. No authorship, submission, acceptance,
optimizer-superiority or real scientific-policy claim follows from the format.
