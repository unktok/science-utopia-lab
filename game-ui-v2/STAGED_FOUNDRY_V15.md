# Staged Institution Foundry V15

The existing English cyberpunk `native.html` now has an **Institution Forge**
chronicle, not another standalone dashboard. Original pixel-city assets and
historical V12–V14 exports, receipts and screenshots are unchanged. Six original
pixel instrument glyphs identify inspect, edit, splice, configure, validate and
finish. The glyph rail is a tool vocabulary, not an invented execution sequence.

The observed timeline follows each generation's real step order. Selecting a
step shows its literal tool input/result, before/after draft hashes, technical
errors and requested source/node/wire/process changes. Literal source and splice
fragments have their own read-only disclosure. Source uses text nodes only; it
is never evaluated or inserted as HTML. The current selection survives progress
refreshes. Rejected edits, malformed replies and dispatched-but-unreceipted
attempts remain distinct, with unknown reply costs left null. An author's
`finish` receipt does **not** establish native execution, loss or adoption.

## Read-only journal projection

`progress.authoring_trace` uses `scienceutopia.authoring-chronicle.v15` with
`scope: observed-local-journals-not-independent-audit`. It contains ordered
`generations`, each with the exact author request SHA, status, optional definition
SHA and `steps`. Every step supplies its index, status, dispatch/completion
booleans, known tool or null, before/after draft SHA or null, errors, result,
literal authored output and known adapter seconds or null. Warnings are explicit.

The decoder rejects malformed hashes, duplicate/reordered steps, incompatible
pending reply fields and rejected edits that claim a changed draft. Unsupported
or absent journals produce no invented activity. Old V14 saved/audited evidence
continues to open without a V15 chronicle. This is an observed-journal display;
the independent audit remains a separate source of evidence and is not implied
by a valid JSON projection.

## Explicit staged service opt-in

Only a local session with `search_protocol: staged-v15` enables staged request
construction. The exact schema becomes `scienceutopia.native-search-request.v15`
and designer settings are `{model: qwen3:8b, max_steps, max_tokens}`. Defaults are
16 steps per generation and 2048 output tokens; supported bounds are 1–64 and
512–8192. Legacy sessions retain V14 request/settings unchanged. Progress schema
must agree with its request version; a mixed V14/V15 pair is rejected.

The console shows the maximum designer provider-attempt budget separately from
native slots: black-box generation count equals native slots; the established
nested 2→1→1 method has two free-author generations. Every edit invalidates exact
request validation and compute consent, including tool-cap edits. Original raw
SystemSpec/LossSpec numeric tokens survive validation and dispatch. No browser
inspection, journal import or step selection grants consent, dispatches work,
executes generated code or adopts a system.

## Software and browser checks

```sh
npm test
npm run typecheck
npm run build
node scripts/verify-native-search-browser.mjs
node scripts/verify-native-search-browser.mjs --staged-v15
node scripts/verify-staged-foundry-checks-v15.mjs --output=/absolute/fresh/directory
```

The browser harness intercepts **all** native API requests and visibly labels
every image SCRIPTED / NO INFERENCE / NOT NATIVE RESULTS. It exercises legacy
and staged request/consent paths, null and unknown reply states, tool selection,
literal edit categories, source XSS rejection, exact numeric wire, renewed
consent, duplicate suppression, desktop/mobile layout and zero browser errors.
It starts/stops only its own Vite and isolated Chrome processes. Screenshots and
receipts remain under system temporary directories. Actual captures require a
separate stopped-writer instruction and exact source/request/audit bindings;
none is fabricated by these tests.

The durable checker requires a committed UI tree and a fresh output directory.
It stores all six command logs plus commit/source-file hashes, and checks source
bytes again after execution. Browser receipts/captures are linked by their
printed temporary paths; they remain explicitly SCRIPTED, not actual results.

## Actual read-only snapshots

`scripts/capture-staged-foundry-readonly-v15.mjs` pins the pilot plan's exact
file hash, run plan, request SHA, experiment source and queue identity, then
reads only the loopback session/progress. Its isolated browser blocks every
non-GET or nonlocal request before navigation. It imports original response
bytes through the existing **unverified saved-progress** control; no independent
audit is implied. Captures distinguish snapshot versus terminal mode, preserve
exact downloaded bytes, and record served asset hashes and UI checkout source
separately from experiment source. Terminal mode additionally requires an
explicit stopped-writer notice and successful exited writer receipt. It never
validates, grants consent, queues work, executes code or adopts a system.

Following actual inspection of a long all-inspection failure trace, prospective
UI polish keeps the selected step inside its own scrollable list and explicitly
reports failed generation counts. This does not alter historical runtime,
screenshots, authored actions, observed native loss or experiment budget.
