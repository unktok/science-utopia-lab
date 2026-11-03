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

```sh
node --test scripts/test-native-search-operator-v14.mjs
```

Six pure guard tests run without network, Chrome or inference. The actual
operator remains unrun until the root operator supplies its exact frozen pins,
service and explicit start instruction. This engineering QA is separate from
the original a1 negative result and cannot rewrite it.
