# Method observatory

`method-observatory.html` is a read-only, English NOCTILUCA view of the **actual,
completed v10** method paths. It is linked from `objective-structure.html`, which
continues to show the historical v8 structural/code experiment. Neither page
starts inference, submits designs, or claims jobs are running. The pixel/vector
city is labelled schematic art, not simulation state.

## Regenerate and verify

From `game-ui-v2`:

```sh
node scripts/export-method-paths-v10.mjs
npm run build
npm test
node scripts/verify-method-observatory-browser.mjs
```

The exporter reads only `research/results/native-method-paths-v10-a1.json`.
The payload is a compact projection, **not an unchanged copy** of the audit.
The receipt binds payload bytes and original audit bytes/content/source commit.
Tests join every coordinate, actual loss, endpoint receipt and backward record
back to the original tracked audit. No raw cache is edited or needed by the
browser. No timestamps or machine-local raw paths are introduced into exports.

Browser verification uses the repository's headless Chrome/CDP approach (no
Playwright dependency is installed). It verifies static GET data, receipt
verification and render, six actual station controls, separate black-box versus
represented-gradient details, no console/network errors, no non-GET/external
requests and no horizontal overflow. Captures and a hash-bound QA receipt are
under `screenshots/method-observatory-v10-qa/`.

## Reusable contract and scope

`src/methodObservatoryContract.ts` defines
`scienceutopia.method-observatory.v1`. The envelope carries:

- campaign identity, terminal status and explicit actual/fixture classification;
- immutable source audit path, file hash, content hash and experiment commit;
- one fixed optimization objective and coordinate labels;
- methods with `none`, `represented-pathwise`, `score-function` or `mixed`
  gradient kinds, distinct current/draw states and historical/final incumbents;
- actual endpoint losses, optional backward information at its own coordinate,
  exact native checkpoint/completion/system identities and physical costs;
- limitations and explicit no-live-job / no-superiority claims.

The contract can be adapted to future exported campaigns. **This delivered
page is intentionally the actual v10 presentation**, with a one-dimensional
coordinate chart, v10-specific interpretation and two method labels. A v11
adapter must supply new immutable evidence and update the corresponding copy;
the page does not invent v11 outputs or relabel scripted fixtures as Qwen.

Important distinctions in this view:

- V10 is one review-charter scalar, not the broader free code/graph design space
  illustrated by v8 and being developed for subsequent common-pipeline work.
- The gradient signal is from a learned reviewer-response representation plus
  parse/selection relaxations. It is not an exact native-world or LLM derivative.
- Its soft loss is evaluated **before the proposal at the preceding coordinate**;
  it must not be read as the predicted loss at the newly evaluated candidate.
- Both arms improve on their initial center but neither beats the historical
  incumbent. Equal fresh-world budgets do not mean equal oracle information.
- Full-world differentiability is not required: black-box, score-function and
  optional represented gradients are tools for the same institution-design goal.
