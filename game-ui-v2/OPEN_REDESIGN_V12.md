# Institution Foundry V12

English, read-only view of **objective-conditioned executable institutional
redesign**, at `native-objective-redesign.html`.

The page is not an experiment launcher or a live game simulation. It does not
start models, submit jobs, execute source, or accept arbitrary remote URLs. Its
pixel city is explicitly schematic art. The circuit below it uses the actual
audited node IDs, source bodies, protocols, port-to-port connections and
schedules. Diagram positions are presentation, not measured geography or
scientific activity.

## Evidence flow

Independent read-only audit → explicit file hash + frozen source pin → guarded
export → availability manifest → browser payload hash verification → rendered
loss paths, system circuit, source/protocol/process/native receipt inspectors.

- Audit schema: `scienceutopia.native-objective-redesign-independent-audit.v12`.
- View schema: `scienceutopia.open-redesign-observatory.v12`.
- Export receipt: `scienceutopia.open-redesign-ui-export.v12`.
- Actual class: `actual-native-qwen-objective-redesign-development-v12`.
- Arms: `native-joint-v5-throughput`, then
  `native-joint-v5-net-reviewed-utility`.
- Budget: three generations × one recorded observation per arm, six attempts.
- Losses: `−A` and `3.25A − Q + 0.05R`. Lower is better on each own scale;
  different scales are not directly compared on a common y-axis.
- All observed systems, current own losses, running best and exact ties remain
  visible. No initial or historical system is silently scored.
- Cross-objective values reuse the same world. They are development
  cross-scores, **not held-out evaluations**, causal effect estimates or
  established scientific value. Missing scores stay null.
- Failure attempts remain visible with null loss, not zero or a penalty.
- Failed authoring has a null native observation ID, not a fabricated endpoint.
  A terminal zero-reply campaign can be displayed without claiming Qwen ran;
  configured model and actually observed replies are distinguished.
- Source comparison uses the generation request's recorded incumbent parent,
  not the previous chronological generation when that proposal was worse.
- Direct generated Python and one-layer `native.process.activity.v1` Python
  delegates are both inspected and checked against the executable source
  contract using the actual delegate ID. The outer process declaration remains
  visible; no recursive process delegate is unwrapped or executed by the UI.
- Source/protocol/node/wire/process freedoms have no fixed two-review-rule
  selector in this interface. The actual experiment can still exercise a
  narrower portion of the representation; view the literal records.

## Export actual data

Only export after the campaign is terminal and its independent audit is ready:

```sh
node scripts/export-open-redesign-v12.mjs \
  --audit=/absolute/path/to/independent-audit.json \
  --expected-source=FROZEN_40_CHARACTER_COMMIT \
  --expected-audit-sha256=EXACT_64_CHARACTER_FILE_HASH
```

The exporter compares both complete LossSpecs to canonical repository files,
rederives non-null cross-scores from native metrics, checks complete physical
endpoints and exact source-body hashes, rejects unsupported claims, and refuses
to write into the raw evidence root. It does not invoke Python, Docker, a model,
or the simulation. Expected hashes must come from an independently checked file,
not from an arbitrary URL supplied in the page.

The new executable-source contract's `source_sha256` hashes raw UTF-8 source
text. Historical native code receipts instead hash its canonical JSON string
value; those correspond to the contract's `source_value_sha256`. They must not
be compared as if the two hash definitions were identical.

### Exact large-integer identities

The Node exporter requires `JSON.parse` reviver `context.source` support. An
integer lexical token outside JavaScript's safe integer range (±(2^53−1)) is
encoded as its exact base-10 decimal **string**, never a rounded Number. The
payload and receipt both carry `numeric_encoding` with schema
`scienceutopia.json-unsafe-integer-decimal-strings.v1`,
`integer_encoding: base10-decimal-string`, and JSON-pointer `paths` identifying
only fields converted from integer tokens. Decode those paths as arbitrary
precision integers when comparing to the original audit. Existing quoted
strings, generated source text, decimal-float and exponent tokens are not
rewritten by this conversion. The source audit's exact file hash remains bound.
The raw observation inspector displays the exact decimal strings, including RNG
seeds and runtime hash probes. The browser validates encoding pointers and their
receipt; it never coerces these identity strings back to Number.

Before an actual export, the tracked availability file is
`awaiting-audited-export`. There is no public v12 fixture payload. Fixture
exports and screenshots require explicit flags and system-temporary paths.

## Browser verification

```sh
npm test
npm run build
node scripts/verify-open-redesign-browser.mjs --mode=actual
```

The harness starts a loopback-only Vite server and isolated headless Chrome,
checks payload binding, all six stations, generation switching, exact-wire
selection and all four inspector tabs, desktop and mobile layout, failed HTTP
responses, console exceptions and external/non-GET requests. It then stops only
the server and Chrome processes it created. Actual artifacts are under
`screenshots/open-redesign-v12-actual-qa/`, with receipt-bound screenshot and UI
source hashes. No researcher inference is performed.

Development-only browser checks:

```sh
node scripts/verify-open-redesign-browser.mjs --mode=unavailable
node scripts/verify-open-redesign-browser.mjs --mode=fixture
node scripts/verify-open-redesign-browser.mjs --mode=fixture --scenario=zero-replies
```

The fixture mode routes temporary synthetic bytes into the browser and adds a
large `SCRIPTED UI FIXTURE / NOT ACTUAL QWEN` watermark. These screenshots are
not actual experiment figures and must not be published as such.
