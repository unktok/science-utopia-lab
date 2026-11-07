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
The finite run and original-source audit are complete. All eight candidates,
including four execution failures, are retained in the [audited result note](../research/results/native-feedback-comparison-v1-a1.md).
The selected initial all-accept proposal improves the declared proxies; no
second-generation gain, feedback superiority or scientific-quality gain is established.

The subsequent eight-rule baseline pilot is complete and twice source-audited:
all8 worlds complete, with original/hand-written controls and no designer calls.
Its print-sized three-objective figure and actual costs now appear in the draft.
The [design-freedom study](../research/protocols/campaigns/native-design-freedom-v2.md)
is described separately as a prospective protocol, not completed results.
The updated11-page PDF was built offline; all pages were rendered again.
The first ten match the previously inspected page PNGs byte-for-byte, and
the new eleventh page was visually inspected;
see [build/QA receipt](submission-build-v2.json). This remains a working draft,
not a completed or submitted conference study.

Appendix B now separates the exact fixed-record acceptance relaxation from a
dynamic institutional-policy optimum. It reports the read-only S1 analysis and
the remaining resource/reproduction limitations; it does not add V2 partial
outcomes or a hidden candidate filter. The build receipt preserves the harmless
UTF-8 engine/inputenc notice and records no layout or undefined-reference warning.

Appendix C reports measured S1 scientist tokens and post-dispatch hardware/
backend observations, with caching and unmeasured-cost limits. It separates
proxy/deployment risks, sandbox limits, release review and AI-assistance disclosure
from optimization constraints. V2 partial outcomes are still not manuscript data.

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
