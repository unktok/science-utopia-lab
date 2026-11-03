# Actual staged-search v15 a2: terminal Foundry captures

Both arms were captured **sequentially, GET only, after the actual experiment
writer exited 0**. Each arm contains five reviewed English desktop/mobile
PNGs, the exact unmodified progress response and the original browser receipt.
No image is retouched and no activity is interpolated. Session/authentication
responses and the operator configuration are not published. Recursive
credential-key and credential-string checks found no matches in the responses.

## Separate runtime and display source pins

- Actual experiment and backend:
  `51d9cbbd49054cdb89c24ea5bc192ff9b63e9155`.
- Report-child UI and capture harness:
  `2fd6aea82fdf792d0b70824f5f4208e2b8447419`.
- The original backend's `make_server` serves the separately built UI through
  the included provenance wrapper. The wrapper starts **no worker**. Original
  source-matching captures remain outside Git, not rewritten or relabelled.
- Each original QA receipt records actual decoded served-asset hashes, exact
  request/plan/runtime identity, UI Git identity and capture-harness hash.

The UI-only revision fixes responsive selection visibility: FINISH stays
inside the internally scrollable list after desktop/mobile resize without
scrolling the document or changing the selected receipt. Every actual capture
asserts selected-row visibility; all ten images were visually reviewed.
The separate SCRIPTED Chrome test repeatedly switches 1600↔390 px and checks
that FINISH selection and inspector identity survive. It is not native data.

## Read the evidence precisely

Each arm records two native observations and 32 designer tool steps.
Throughput losses are `[-1,-1]`; reviewed-production losses are `[8,8]`.
Both generations explicitly retain their exact parent. This is not invented
code, a newly discovered institution, objective improvement or held-out evidence.

The saved-progress UI is **not an independent audit**. That warning remains
visible even though a separate scientific report audits the experiment.
Known cache rows in screenshots are not relabelled as audited physical reply
counts. The two objective axes/scales are different.

## Verification and cleanup

Both captures exited 0, with no browser errors, failed HTTP or document-width
overflow. All actual requests were local GETs: no validation/consent/queue
POST, model dispatch or adoption was performed. The manifest hashes exact
captures, unmodified responses, receipts and backend/UI provenance wrapper.

The actual writer had already exited 0. After capture, owned preview child
77828 exited -15 following TERM and port4596 had no listener. The earlier
source-matching preview child57886 and its launchd label were already stopped.
The supervisor's shell status241 represents child -15, not an experiment
failure. Capture, experiment and preview-shutdown receipts stay distinct.

These finite QA artifacts do not alter historical v12/v13/v14 exports or a1
captures. No inference, preview or test process from this track remains active.
