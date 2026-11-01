# Open native integrated evidence viewer v7

`game-ui-v2/open-evidence.html` is a read-only English NOCTILUCA evidence
district for `scienceutopia.native-open-integrated-pilot.v7`. It does not run a
designer, researcher model, simulation, optimizer, worker, or adoption action.

## Evidence path

The pilot writes `evidence.json` with a semantic `content_sha256` over the
payload. After that artifact is tracked, export it with the approved local
Python rather than Apple/Xcode Python:

```sh
~/.local/bin/python3 scripts/export_native_open_evidence_ui.py /absolute/path/to/evidence.json
```

The exporter recomputes the exact Python canonical hash, rejects UI fixtures,
requires the negative scientific/derivative claims, and refuses incomplete
observations that contain numerical loss or complete-only endpoint evidence.
The browser then validates the versioned schema and the same truth contract
before rendering `game-ui-v2/public/data/native-open-integrated-v7.json`.
Without that export, the default page reports actual evidence unavailable.

The separately hashed
`game-ui-v2/public/data/native-open-evidence.synthetic.json` is available only
through `?fixture=open-v7`. It is visibly labelled `SYNTHETIC UI FIXTURE`, is
rejected by the actual-data parser, and exists solely for component and browser
tests.

## Visible evidence

For each generation and draw, the view keeps the generated vocabulary version,
selected strategy, factor assignment, bounded continuous latent and operation,
strategy state before/after, and update status. Complete actual observations
may expose loss, checkpoint, system, domain, events and derivative evidence.
Failed or null observations display `LOSS NULL` and never receive invented
checkpoint, system, domain, or derivative fields.

For a selected complete endpoint, the page exposes:

- persistent NativeOpenDomain participant and scientific-artifact records,
  including type, role/owner, revision, year and links;
- every exported `native.process.*` receipt, distinguishing real iterations,
  completion and explicit skip;
- the full SystemSpec mechanism/connection graph, port contract, parameters
  and generated source details when present;
- represented edge coverage, conditional gradient, finite-difference checks,
  checkpoint/source/campaign bindings and the selected raw evidence row.

## Claim boundary

The engineering count loss is not a scientific-value metric or held-out
evaluation. The conditional backward pass covers only the recorded represented
numeric model. It is not a derivative through researcher text, generated
Python source, arbitrary native reactions, or the full native world. A passing
local numerical check does not establish causal institutional benefit,
designer improvement, external author identity, or a generally better science
system. These labels remain visible beside the derivative panel and in the
source contract.

## Verification

`game-ui-v2/test/openEvidence.test.ts` checks fixture/actual separation,
content-hash verification for the fixture, null-loss preservation, derivative
claim boundaries, NativeOpenDomain records and process receipts. Production
verification is `npm test`, `npm run typecheck`, and `npm run build`. Browser
QA waited for the tracked compact pilot report; fixture screenshots were not
substituted for actual evidence.

## Completed actual a2 rendering

The independently audited compact a2 artifact is now exported byte-for-byte as
`game-ui-v2/public/data/native-open-integrated-v7.json` after exporter
validation. Its semantic content SHA256 is
`cce6b6b8af54f96bd5b68c00e938b218198ad6dae5cd1241f6427a1c7cabf4fe`.
It records four completed fresh native worlds, 342 physical fixed-Qwen replies,
and observed loss path `[-1.2,-0.2,-0.8,-0.2]` across two evolving vocabulary
generations. The UI also displays independently recomputed endpoint metrics and
native-effect counts. This path is not a best-design improvement claim.

Local Chrome QA used a clean temporary profile and the actual export. It
verified all four loss cards, the independent endpoint ledger, one custom actor,
two scientific artifacts, real process years, 19 nodes, 27 edges, two
represented tensor nodes, the negative gradient boundary, English-only copy,
zero browser errors, and no desktop/mobile overflow. It started no experiment,
model call, or worker. The owned preview and browser were stopped and their
temporary profile moved recoverably to Trash.

- `game-ui-v2/screenshots/noctiluca-open-native-v7-observations.png`
- `game-ui-v2/screenshots/noctiluca-open-native-v7-domain.png`
- `game-ui-v2/screenshots/noctiluca-open-native-v7-process.png`
- `game-ui-v2/screenshots/noctiluca-open-native-v7-system.png`
- `game-ui-v2/screenshots/noctiluca-open-native-v7-derivative-boundary.png`
- `game-ui-v2/screenshots/noctiluca-open-native-v7-actual-full.png`
- `game-ui-v2/screenshots/noctiluca-open-native-v7-qa.json`
