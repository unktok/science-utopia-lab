# Inspecting closed pre scale institutions in the Foundry

The pre-scale observatory shows recorded progress and losses. After the whole
O/E study closes and its original-source audit succeeds, a separate read-only
export connects each development arm to the existing English Institution Foundry.
It exposes the exact code, typed ports, wiring, schedules, committed researcher
frames and technical failures. It starts no experiment and makes no selection.

Actual closed-study export is still pending the running evaluation and full
audits. [Verification](../results/pre-scale-foundry-verification-v1.json) separates
software checks, one actual completed-cell extraction and synthetic browser QA.

## Source and data boundaries

[The exporter](../../scripts/export_pre_scale_design_evidence.py) requires the
original62388a7 source and db2df5c5 plan, a normal study closure, the frozen
selection, a full original-source audit and its unchanged raw-file inventory.
It reuses the all-slot report joins and checks each annual checkpoint hash,
SystemSpec and event prefix before reading frames. No source, simulator,
container or model is executed. These are integrity joins, not authenticated
third-party attestations or another independent scientific audit.

Each of eight arm files contains the initial reference and submitted G0/G1
policies, using that arm's declared loss. A generation failure remains an
unsubmitted slot rather than acquiring a fabricated policy. A year-zero runtime
failure has no researcher frames; a completed trajectory must have all four
committed years. Candidate changes are compared with their actual request
parent, not guessed from list order. Full original source strings are retained.

The browser accepts only eight explicit same-origin files and verifies the
envelope and SystemSpec hashes, source, plan, arm, development seed and horizon.
It rejects an unrelated soft-fit history because this study performs no such
fit. The selected channel hides file replacement and the design workbench and
does not initialize queue/search APIs. A missing or modified file fails closed;
the older default study is never substituted.

## Export after both full audits agree

From the repository root, using the existing approved Python environment:

```sh
.venv/bin/python -m scripts.export_pre_scale_design_evidence \
  --run /absolute/path/to/frozen/pre-scale-search-v1-a1 \
  --audit /absolute/path/to/matching/O-E-audit-1.json \
  --output game-ui-v2/public/data/pre-scale-foundry-v1
```

The output directory must be new and outside the raw run. The eight JSON files
and manifest retain their file hashes and original audit identity. Once exported,
open `/native.html?pre-scale-arm=efficiency%3Aparameters` on the local UI server.
The closed observatory also supplies all eight links. File availability does
not imply a live process, better science or reliable generalization.

To verify an actual export with the existing local Chrome/Playwright setup:

```sh
cd game-ui-v2
node scripts/check-pre-scale-foundry.mjs \
  --arm=efficiency:parameters \
  --envelope=/absolute/path/to/pre-scale-foundry-v1/efficiency--parameters.json \
  --manifest=/absolute/path/to/pre-scale-foundry-v1/manifest.json \
  --playwright-module=/absolute/path/to/existing/playwright/index.mjs \
  --output=/absolute/path/to/fresh/actual-browser-verification
```

`--synthetic=true` instead exercises a conspicuously labelled UI fixture without
creating actual public study files. It is not an actual-data verification or a
paper figure. The browser check records zero writes/queue calls, literal code,
node/wire/frame joins, failure text, missing-file and tamper behavior.

Long full-page mobile screenshots repeated the top of the page in one local
capture despite a single header/deck in the DOM. The cause remains unproven.
The capture check now saves three actual390×844 viewports after confirmed
scrolling, rather than distributing the unreliable composite. Synthetic images
have a visible QA annotation. Earlier images and reports remain preserved.
