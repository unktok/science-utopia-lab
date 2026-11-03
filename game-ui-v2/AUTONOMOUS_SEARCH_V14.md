# Autonomous Institution Foundry V14

`native.html` extends the existing English pixel-city Foundry workbench with an
autonomous search console. The graph editor and exact SystemSpec/LossSpec remain
the inputs; the original manual-run mission is separately available below.
No existing V12/V13 payload, receipt, availability file or screenshot is changed.

The autonomous console creates exactly
`scienceutopia.native-search-request.v14`: `initial_system`, `loss_spec`, `seed`,
`years`, `method`, `native_budget`, and the fixed `qwen3:8b` designer settings.
Black-box search accepts 1–8 native slots. Nested LR requires exactly four slots
and the established 2→1→1 schedule. Designer attempts are 1–3 and output token
limits are 512–8192. Authoritative compilation and validation remain server-side.

The workbench first reads the existing same-origin token session. Validation
uses `POST /native-api/search-validate`; source, method and native budget must
match. Compute consent is enabled only after validation, bound to the exact
request and source receipt, and consumed by
`POST /native-api/searches` with `{request, confirmed_request_sha256}`. Any input
edit invalidates validation and consent. Concurrent duplicate submission and
late validation from an edited draft are blocked. Viewing, editing, validating,
loading saved evidence and downloading receipts do not dispatch inference.

`GET /native-api/searches/{id}` polls recorded progress. The terminal evidence
endpoint supplies the same projection with its immutable plan. The console
keeps charged slots separate from physical native observations, current loss
separate from best own loss, technical/null endpoints visible, and exact stage
records available. Source, protocol, weights, graphs and observation objects
are inspectable only as supplied by the runtime; missing activity is not
interpolated into a simulated city or invented researcher animation. Designer
and researcher physical reply counters are shown separately when provided.
The source commit, exact request hash and full loss remain visible.

Optional `scienceutopia.native-search-live-progress.v14` receipts add a compact
live band: durable phase, maximum observed checkpoint year, completed designer
receipt files versus dispatch-intent files, and known researcher cache rows.
The display labels these provisional observed files, not final audited physical
calls. Missing or unreadable counts remain unavailable, including cache-binding
warnings. A checkpoint filename does not establish world completion; durable
status and final loss continue to come from the separate recorded projection.

Saved evidence opens as read-only, with source identifiers explicitly described
as unauthenticated unless bound to the live validated request. It cannot create
consent, execution or adoption. The download preserves exact API/file bytes.
Unsafe integer lexical tokens are converted to decimal strings plus escaped
JSON pointers for display only, before JavaScript can round them. Quoted source
and floating lexical tokens are retained. Unsafe integer request drafts fail
closed; no rounded SystemSpec or LossSpec is dispatched. Copying an existing
SystemSpec into the shared workbench now uses that same exact-draft decoder.

Verification:

```sh
npm test
npm run build
node scripts/verify-native-search-browser.mjs
```

The browser harness intercepts every native API request with prominently labelled
SCRIPTED fixtures. Its evidence and desktop/mobile captures remain under a
system temporary directory; they are not actual results. It verifies editing
invalidation, renewed consent, exact dispatch shape, duplicate prevention,
null failures, charged-versus-physical slots, unsafe integer display, separate
reply counters, terminal evidence access, no overflow and zero browser errors.
It starts/stops only its own Vite and isolated headless Chrome, with no native
worker or model calls. Current regression result: 269 tests and production build
pass. Actual screenshots require terminal audited actual evidence and are not
claimed by this implementation receipt.

## Terminal independent audit bridge

The existing mission panel also opens the three-request aggregate
`scienceutopia.native-autonomous-search-audit.v14`. The user supplies the exact
audit **file** SHA256 and experiment source commit. The importer checks original
bytes, terminal classification, independent replay/source assertions and each
runtime projection against the audit's full request, plan, records and pending
state. File SHA256 is distinct from the audit's Python canonical content hash;
the UI does not claim to recompute that differently serialized content hash.
UI report code may be committed after the frozen experiment source.

The request chooser preserves each loss and method. Every original designer
attempt, dispatch prompt, diagnostic, parsed authored operation/source, raw
assistant message and transport object remains inspectable, including invalid
or unparsed drafts. Interrupted unknown attempts remain null. A failed
generation does not create a candidate graph, world, loss or adoption. Changing
the displayed audited request clears any pending browser consent and stops
progress polling; it does not cancel a server job or dispatch new work.

```sh
node scripts/export-native-search-audit-v14.mjs \
  --audit=/absolute/path/to/terminal-audit.json \
  --expected-audit-sha256=EXACT_64_HEX_FILE_HASH \
  --expected-source=EXACT_40_HEX_EXPERIMENT_SOURCE
```

The exporter copies original bytes unchanged and writes a separate file receipt
under `public/data`. Open `native.html?audited-search=v14` for the published
read-only import, or select a local audit with the exact expected identities.
The old saved-progress picker remains explicitly unauthenticated. Audit integrity
does not establish externally authenticated provider authorship or scientific
benefit. No audit, actual export or actual screenshot is invented before the
independent writer closes.

SCRIPTED tests require explicit fixture opt-in. Browser fixture import is
restricted to loopback `?scripted-audit=v14`, always labelled as SCRIPTED, and
fixture exports require `--allow-scripted-temp-only` with temporary input/output.
Current regression: 274 tests, typecheck and build pass; scripted browser QA
also verifies all three audited requests, exact failed raw source inspection,
zero candidate graph on generation failure and no additional dispatch.

## Separately authorized two-slot engineering operator

`scripts/submit-native-search-operator-v14.mjs` is an actual-only fixed operator
for the separate bounded engineering QA. It has no fixture interception, starts
only isolated Chrome, and never starts a worker, model or service. It refuses
to run without `--start-authorized-ui-search` plus exact prospective request,
operator provider file, experiment source, server canonical request SHA, fixed
loopback port and output directory. Root authorization and a pinned running
service are prerequisites; preparing the harness does not authorize running it.

The fixed contract is throughput loss, black-box two native slots, seed42,
two years and Qwen3:8b with two drafts per generation /4096 output tokens. The
operator loads the exact shared editors, confirms old consent is invalidated,
clicks validation once, checks source/request/budget/provider bindings and four
maximum designer attempts, captures the pre-consent view, then explicitly checks
compute consent and clicks the queue button once. It captures the queued view
and retains request/response bodies, HTTP statuses, separate byte hashes, canonical
request SHA and search ID. Session tokens are omitted. Any failure produces a
receipt and forbids automatic submission retry. No adoption endpoint is used.
An exclusive permanent output-directory lock prevents invoking the same operator
receipt directory twice, including after an uncertain failure.

```sh
node --test scripts/test-native-search-operator-v14.mjs
```

Six pure guard tests run without network, Chrome or inference. The actual
operator remains unrun until the root operator supplies its exact frozen pins,
service and explicit start instruction. This engineering QA is separate from
the original a1 negative result and cannot rewrite it.

### Exact numeric request wire

Runtime validation binds `request_json`, including the original validated
SystemSpec and LossSpec editor JSON substrings. Validation sends that raw JSON;
dispatch embeds the identical bound substring with its confirmed server hash.
Consequently `1.0`, `-1.0`, `0.0` and integer tokens retain their distinct Python
canonical types. Parsed JavaScript Number objects are used for structural
checks, never to regenerate those two wire fields. Code body strings are not
edited. Any raw editor drift, including a programmatic change without an input
event, revokes validation and consent when checked or submitted.

The actual operator probes `context.source` and `JSON.rawJSON` before opening
Chrome. It formats editor JSON from the input file with original numeric tokens
intact, then lets the server validate its original canonical request identity.
No request normalization, fingerprint approximation or objective replacement is
performed. Unsafe integer request tokens still fail closed. Regression evidence
includes actual loopback HTTP request bodies checked with approved Python's
canonical JSON digest, 277 UI tests, seven pure operator tests, and scripted
Chrome numeric-wire / no-event consent-drift checks. No native inference is
started by these checks.

## Actual a1 read-only publication

The closed independent a1 audit is published byte-identically at
`public/data/native-autonomous-search-v14.audit.json` with its separate UI
receipt. Experiment source:
`54a7d92dad5221f83f25f81d62aa225ab38cef25`. Exact audit file SHA256:
`88520eef09fc36c8ad904a2c19bcb6607ea208f11734d8577e66cd39256de0c8`.
Audit content hash:
`c8b5d713bd383ddc2feafebe67398af0e10fab44d2d1cd4d3605f9b5282fbb79`.

All three audited requests remain visible in the original workbench at
`native.html?audited-search=v14`. The result is **budget complete with failures**:
eight charged slots, six authoring generations, 12 recorded designer responses,
zero valid candidates, zero native world directories and zero scientist replies.
The actual captured source is an invalid original designer draft, not an
executed institution. Draft inspection exposes original values, literal-address
diagnostics and source comparisons without repairing or adopting them.

`screenshots/autonomous-search-v14-a1-actual-qa/actual-browser-qa.json` binds the
exact audit/source and UI source-file hashes to five reviewed desktop/mobile
captures. It verifies all three requests, all 12 attempt records, failure/null
states, zero candidate graphs and original authored source inspection. It records
only local GETs, zero POSTs, zero new inference, zero adoption, zero browser
errors, zero failed HTTP responses and no horizontal overflow. Source/export
bytes are checked before and after. The browser harness starts and stops only
its own Vite and isolated Chrome; it never opens mutable raw evidence.

```sh
node scripts/verify-native-search-audit-browser.mjs \
  --audit=/absolute/path/to/closed-independent-audit.json \
  --expected-audit-sha256=88520eef09fc36c8ad904a2c19bcb6607ea208f11734d8577e66cd39256de0c8 \
  --expected-source=54a7d92dad5221f83f25f81d62aa225ab38cef25
```

These failed development requests are the original a1 result. The separately
authorized stable-ID engineering QA cannot replace or retroactively repair them.

## Separate stable-ID QA terminal queue display

The original single-submit operator already queued
`search-6f65de5f1e834096bc3aa7ca46385156` under frozen source
`fdb694d0adee759470d9c4ff41c4d8c75e490d19`. It must never be submitted again.
The GET-only `capture-native-search-queue-readonly-v14.mjs` reads its session
token privately, verifies the exact manifest/source/request/plan bindings and
original raw queued response, and imports the original response bytes through
the existing **unverified saved-progress** control. It never validates, consents,
queues, adopts, starts a worker or calls a model. Terminal mode requires both
root's stopped-writer instruction and the closed successful worker receipt.

`screenshots/native-authoring-ir-v14-qa-actual-qa/` contains the exact terminal
GET `/evidence` response, four reviewed terminal desktop/mobile captures, and
byte-identical original pre-consent/queued PNGs. The terminal raw snapshot hash
is `4dee176d8d2373cafc00e5d94fb7442d7b4078fc54f8943c8ec1cff640258a6c`.
The manifest's request hash is
`1015e4dc0ef95ae826f826fa6917a0f1e0518330edde68837c09f482b5c2c7f5`;
its plan hash is
`27e7d916ee26c64e384bf3dadf4cb9c6b12ab13cd83a6e2547dde68ada2af77e`.
The worker closed at `2026-11-03T01:32:51.504126+00:00` with exit0.

The display states **BUDGET TERMINAL / 0 RECORDED NATIVE OBSERVATIONS / SUCCESS
NOT IMPLIED**, with null/unobserved loss and no current candidate graph. The
three completed designer receipt files and four dispatch intents remain
separate; the interrupted unknown response is not converted to a reply or zero
cost. Report-only captions explicitly distinguish this engineering QA from a1
and from an independent audit. The raw progress bytes stay unchanged. The
receipt records every served code/CSS/HTML response hash, original capture
hashes, closed-worker/manifest/operator hashes, and the precise display-only
captions. It verifies GET-only traffic, zero browser errors, failed HTTP responses
or overflow. These captures do not claim source usefulness or native success.

Durable local software logs can be generated from the final report branch with:

```sh
node scripts/verify-native-search-ui-checks-v14.mjs --output=/absolute/check-log-directory
```

This records the report commit and source-file hashes alongside the 277-test,
typecheck, production-build and eight pure operator-guard command logs. It does
not contact the native API or run inference.
