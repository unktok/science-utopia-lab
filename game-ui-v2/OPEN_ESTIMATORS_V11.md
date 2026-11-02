# Open native estimator evidence viewer

`native-open-estimators.html` is a read-only, English v11 evidence view, separate
from the guarded historical v10 observatory. Its initial tracked availability
manifest truthfully says **awaiting audited export**. There is no public fixture,
provisional outcome, initial score or historical baseline. No job starts here.

## Export a completed actual audit

Run from `game-ui-v2` (equals-form arguments):

```sh
node scripts/export-open-estimators-v11.mjs \
  --audit=/absolute/path/to/completed-v11-audit.json \
  --expected-audit-sha256=EXACT_AUDIT_FILE_SHA256 \
  --expected-source=EXACT_EXPERIMENT_COMMIT
npm run build
npm test
node scripts/verify-open-estimators-browser.mjs --mode=actual
```

The explicit expected **file** checksum binds the already independently audited
JSON bytes. The exporter does not attempt a second Python-content-digest
calculation in JavaScript, where JSON numeric serialization differs. The export
receipt retains both the independently supplied file identity and the audit's
content identity. Actual source-replay, objective, complete eight-world counts,
physical/logical/wire count consistency, no response reuse, attribution and
claim boundaries are required. The exporter joins every cutoff to its recorded
candidate coordinate path and continuous operation. It never writes raw evidence.

The browser verifies payload bytes and the matching source receipt. It shows
all four per-arm observations and running best, algorithm choice, actual cutoff,
sampled latent, installed source and literal wires. G0 plain-LR and G1 prior-only
control-variate updates show exact current and preceding own-arm observation
IDs. Neither initial nor historical baselines are invented. The final G1 update
is displayed as a computed batch update, not as a subsequently evaluated policy.

## No-data and explicitly synthetic QA

```sh
node scripts/verify-open-estimators-browser.mjs --mode=unavailable
node scripts/verify-open-estimators-browser.mjs --mode=fixture
```

The second command creates only temporary, prominently watermarked scripted
schema fixtures. Browser fetch interception serves them only to its isolated QA
browser. Neither fixture payload nor screenshots enter `public/data` or the
tracked actual screenshot directory. Fixture mode also requires explicit
`?fixture=scripted-v11` attribution; default mode rejects fixture data.

The verification script uses the project's existing headless Chrome/CDP approach.
It verifies desktop/mobile rendering, all eight station controls, G0/G1 detail
selection, no horizontal overflow, console errors, failed responses, non-GET
dispatch or external requests. Its receipt binds screenshots, UI source and, when
available, the precise export payload/source receipt. No inference is involved.

## Limits

The pilot's external author installs a new source/protocol/wiring family but
deliberately preserves that family for generation 1 so a prior-only control fit
has compatible semantics. This is not autonomous code invention each generation.
The score gradient concerns a conditional design distribution, not an exact
source-generation or original-world pathwise derivative. Two samples per batch
do not demonstrate variance reduction or optimizer superiority. The objective
is a declared engineering preference, not a validated law of scientific quality.
