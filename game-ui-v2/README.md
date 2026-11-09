# NOCTILUCA // Research Arcology renderer

This directory contains the Phaser 3 vertical-slice renderer for the Science
Utopia game UI. It is an auditable presentation layer over replay-view v2. It
does not run scientific mechanisms or infer missing scientific activity in the
browser.

## Current status

The read-only `/pre-scale.html` observatory displays the new D/M journal snapshot
and prospective T/E search/evaluation stages. It distinguishes a consumed start
without an observation from a live process, preserves unknown losses as dashes,
and verifies the Python/browser content checksum. It starts no experiment.
Export a fresh timestamped observation without inference:

```sh
.venv/bin/python -m scripts.export_pre_scale_observatory \
  --information-run /absolute/path/to/frozen/information-run \
  --output game-ui-v2/public/data/pre-scale-observatory.actual.json
```

Run that module command from the repository root with its approved Python
environment, not from this subdirectory. Add `--search-run` only once an actual
new-source search plan exists. A copied readiness pass does not become a search
improvement, and the snapshot is not an independent original-source audit.

The completed actual v10 parameter/loss paths are now available in
`/method-observatory.html`, linked from the v8 structural switchyard. Read-only
charts keep current draws separate from the historical incumbent, and actual
native losses separate from represented gradients. See
[the method observatory contract and verification](METHOD_OBSERVATORY.md).

The separate `/native-open-estimators.html` v11 viewer defaults to a truthful
unavailable state until a completed actual audit is exported. It supports
black-box and expectation-gradient batches without inventing an initial score;
see [v11 export, provenance and browser QA](OPEN_ESTIMATORS_V11.md).

The v4 renderer is operational with a 48-second deterministic, synthetic
fixture containing four researchers, four institutions, sixteen canonical
events, seventeen evidence-linked actor actions, and seven visible flows across
all six information-flow types. Researchers walk to institution work areas and
use role-specific experiment, writing, review, publication, allocation,
citation, and policy poses. This
fixture validates the renderer and evidence interaction; it is not an
experiment or a claim about a real or simulated scientific system.

The runtime uses hand-authored, fixed-grid production SVGs: each researcher is
a six-frame 24x32 sheet, institutions are 96x80, flow packets are 8x8, and the
ambient courier is 16x8. Every sprite mark is an integer-aligned rectangle
using the frozen 24-colour palette; the browser rasterizes the SVGs with
nearest-neighbour settings. The earlier generated PNGs remain beside them as
**concept-only visual targets** and are not loaded.
See [asset provenance](public/assets/noctiluca/PROVENANCE.md) and the project
[art bible](../game-ui/ART_BIBLE.md).

The intervention-fork page at `/compare.html` adds two synchronized instances
of the same renderer. It loads a versioned branch manifest, recomputes the two
complete stream hashes and their common-prefix hash, and verifies each declared
`policy.changed` intervention before opening the comparison.

The v4 world closes the spatial publication loop. A paper travels from the lab
to review, the completed decision moves it into the Publication Spine, and a
citation returns from the repository to the lab. Explicit derived actions also
drive deterministic workstation effects: instrument readouts, manuscripts,
review terminals, repository pages, funding ledgers, citation brackets, and
policy broadcasts. No effect appears without an active choreography action.

## Research arcology hub

The native institution evidence/design view is at `/native.html`. Its English
Institution Foundry control room is original schematic pixel/vector art;
the adjacent counts, year and selected mechanism come from checksum-bound
original researcher-world records. Inspect source, tensor programs, wiring,
schedules, researchers/resources and real native loss lineage. Existing records
remain read only. An optional local design workbench now edits full SystemSpec
and explicit LossSpec JSON, validates it, and queues one explicitly authorized
fresh native branch. It does not migrate a live society or imply full-world
autograd. `/generative.html`
remains a separate numeric-miniature method viewer, not that native world.
See `research/tracks/native-design-ui-v1.md` and asset provenance for scope.

The audited v5 design lifecycle is at `/lifecycle.html`. This English
NOCTILUCA chronicle is generated from the tracked v5 result artifact and shows
both LossSpecs, all three observed systems in each arm, their actual loss paths,
the first-best tie rule, and code/protocol/wiring differences. It keeps the
external Codex designer distinct from the fixed local Qwen3:8B researcher
society. Persistent boundaries mark the result as development-only: not
held-out, not scientific value, not full-world differentiation and not an
executed same-society adoption. A separate continuity console can read a
configured loopback-only `NativeSocietyDesignSession`: it shows online interval
losses and exact staged request hashes, keeps confirmation pending while the
worker runs, and reports completion only after a matching backend-verified
durable migration receipt. With no society API it fails closed as unavailable;
`?society=fixture` is a labelled read-only UI fixture whose action controls are
disabled. The historical v5 candidate is never submitted through this live
console. See `research/tracks/native-design-lifecycle-ui-v6.md`.

The v7 open-native evidence viewer is at `/open-evidence.html`. It renders a
hash-bound exported `scienceutopia.native-open-integrated-pilot.v7` artifact:
evolving generated vocabularies, actual conditional draws, complete/null
observations, NativeOpenDomain actors and artifacts, process iteration/skip
receipts, the SystemSpec graph and represented conditional backward boundary.
It never starts work. With no exported actual artifact it fails closed as
unavailable. `?fixture=open-v7` opens a conspicuously labelled synthetic UI
fixture and is never accepted through the actual channel. See
`research/tracks/native-open-evidence-ui-v7.md`.

The current tracked actual export contains four completed fresh worlds, 342
physical Qwen3:8B replies, and observed engineering losses
`[-1.2, -0.2, -0.8, -0.2]`. These are development observations, not a claim of
best-system improvement, causal benefit, held-out performance, or scientific
value.

The v8 objective-conditioned structure viewer is at
`/objective-structure.html`. Its dual-line switchyard keeps both fixed
illustrative LossSpecs and every development path visible, including exact
ties, zero-draw generation failures, technical nulls, and unavailable
same-checkpoint cross-scores. Selecting a complete station opens the actual
candidate SystemSpec graph, literal node/edge/source/protocol/schedule diff,
and executable Python source bay. It distinguishes fixed Qwen3:8B researchers
from external Codex source authorship and permanently labels the evidence as
development—not held out, promoted, or guaranteed beneficial. Missing actual
data stays in a waiting state; `?fixture=objective-v8` is the only labelled
synthetic route. See `research/tracks/objective-structure-ui-v8.md`.

Regenerate the portable, hash-bound browser snapshot without running an
experiment:

```sh
node ../scripts/export_native_design_lifecycle_ui.mjs
```

For actual local submission, build first and use the loopback-only server from
a clean commit-pinned checkout (do not edit its source while a worker runs):

```sh
cd game-ui-v2
npm run build
cd ..
.venv/bin/python scripts/serve_native_lab.py --queue outputs/native-ui/queue
```

Open `http://127.0.0.1:4591/native.html`, expand DESIGN WORKBENCH, edit and
validate, then explicitly authorize and queue the run. Nothing executes merely
by viewing or validating. A separate one-writer process handles one pending job:

```sh
.venv/bin/python scripts/serve_native_lab.py --queue outputs/native-ui/queue \
  --worker-once --data-cache /absolute/path/to/compatible/native/cache
```

Completed results load into the same native viewer with checksum validation.
The worker uses the original fixed-Qwen researcher world, five independent
balanced authors and at most four native years for interactive jobs. Technical
failure yields no numeric penalty. This is a local development service, not a
public multi-user application; no command strings, request paths or credentials
are accepted, historical held-out seeds remain reserved, and generated code
executes only through the existing isolated container runtime.

Open `hub.html` for the shared in-world transit deck. Three pixel-art district
gates lead to the commit-pinned research city, the synthetic SystemSpec
foundry, and the timestamped optimization mission-control screen. A shared
truth rail remains visible after transit and labels both the intended
destination and the actual active source (including synthetic replay/UI test
query modes).

```text
http://localhost:4173/hub.html
```

The hub is deliberately presentation-only: it imports no replay, sandbox, or
mission data contract and fetches no scientific data. Optional session state
stores only the last visited district. Arrow keys select a gate, Enter opens
it, and Alt+H/R/S/M provides direct transit. See
`research/tracks/game-ui-research-arcology-hub-v1.md` for the boundary design.

## Run

Requires a current Node.js and npm.

```sh
cd game-ui-v2
npm ci
npm run dev
```

Open `http://localhost:4173/`. Production verification is:

```sh
npm test
npm run typecheck
npm run build
npm audit
```

Open `http://localhost:4173/compare.html?cursor=43000` for the side-by-side
branch slice. Add `&inspect=1` to open Future B's intervention evidence.
Regenerate its three deterministic JSON documents with:

```sh
~/.local/bin/python3 ../scripts/export_game_branch_comparison.py \
  --output-directory public/data
```

The asset tests enforce the production manifest, sprite-sheet dimensions,
required keys, frozen palette, integer geometry, crisp-edge declaration, and a
rect-only SVG vocabulary. Replay tests enforce that every actor action and
flow is derived from canonical evidence. Silhouette and semantic legibility
remain visual review gates.

## Synthetic science-system design console

Open `sandbox.html` to edit a structure-only five-node `SystemSpec`. The page
is deliberately separate from the verified replay and is always labelled
`SYNTHETIC SANDBOX`; it runs no simulation and displays no outcome. The
contract is generated and validated by Python, while browser fingerprint and
validator parity are checked against valid and invalid authoritative fixtures.

```text
http://localhost:4173/sandbox.html?motion=reduced
http://localhost:4173/sandbox.html?motion=reduced&preset=invalid-publication
```

- [valid synthetic SystemSpec](screenshots/noctiluca-system-sandbox-valid.png)
- [disconnected publication input](screenshots/noctiluca-system-sandbox-invalid-publication.png)

## Optimization mission control

Open `mission.html` for the read-only operations view of the three-arm metric-
conditioned v1.1 study. The default bundle is a timestamped, source-commit-
pinned projection of campaign state and SQLite registries. It displays only
orchestration facts: logical registration, physical/adopted execution, seed
state, winner-freeze state, and the held-out firewall. Objective values,
unfinished results, and inferred winners are not exported.

```text
http://localhost:4173/mission.html
http://localhost:4173/mission.html?source=synthetic
```

The second URL is a separately labelled UI-test fixture. Its invented mixed
states never share the verified source kind. See the full adapter and claim
boundary in `research/tracks/game-ui-optimization-mission-control-v1.md`.

- [verified optimization snapshot](screenshots/noctiluca-optimization-mission-verified.png)
- [synthetic state coverage](screenshots/noctiluca-optimization-mission-synthetic.png)

## Verified collaboration / evidence navigator

The verified city now exposes an evidence graph from the city, institutional
interior and researcher dossier. Press `G`, select an artifact or institution,
or use `OPEN EVIDENCE GRAPH` in a dossier/interior fact bar. Canonical
affiliation, authorship, coauthor, reviewer, funding activity, funder and
citation edges remain separate filterable types. Missing funder identity and
unobserved citation/coauthor events are reported directly; the browser never
substitutes one relation for another.

```text
http://localhost:4173/?replay=campaign&motion=reduced&cursor=47000&graph=https%3A%2F%2Farxiv.org%2Fabs%2F1606.04422
http://localhost:4173/?replay=campaign&motion=reduced&cursor=47000&graph=institution_0001_researcher_2
```

The graph's force layout, node placement, edge routes/animation, colour and
narrative labels have a typed `presentation_only` contract. Edge cards and the
lineage strip drill into the existing canonical event inspector; researcher
nodes drill back into dossiers. See
`research/tracks/game-ui-collaboration-evidence-v1.md`.

- [artifact authorship/reviewer graph](screenshots/noctiluca-evidence-graph-artifact-seed521-cursor-47000.png)
- [researcher funding-activity graph](screenshots/noctiluca-evidence-graph-funding-seed521-cursor-47000.png)

## Optimizer Observatory

Press `O` to open the optimization-to-city bridge. It verifies the existing
read-only mission snapshot, then renders each LossSpec arm as a conditioning
gate feeding system-design candidates, seed-run bays, a score array and a
winner-freeze vault. The status adapter exports no objective values, so score
cells remain `NOT OBSERVED`; the winner and report remain `NOT FROZEN` and
`LOCKED`. Snapshot time, source commit and provenance hashes stay visible.

```text
http://localhost:4173/?replay=campaign&motion=reduced&cursor=47000&observatory=on&loss=1
http://localhost:4173/?replay=campaign&motion=reduced&cursor=47000&observatory=synthetic&loss=2
```

The second URL is a conspicuously labelled synthetic UI fixture. Changing the
LossSpec rebinds the candidate/run rail and explains that system design is the
optimized variable. Because this snapshot's three arms still share their
initial candidate identities, cross-arm design divergence is truthfully shown
as `NOT OBSERVED`, not implied by the visual layout. See
`research/tracks/game-ui-optimizer-observatory-v1.md`.

- [verified result-blind observatory](screenshots/noctiluca-optimizer-observatory-verified.png)
- [synthetic status-coverage observatory](screenshots/noctiluca-optimizer-observatory-synthetic.png)

## Common-Split Relay

Open `heldout.html` for the result-blind held-out execution view. Three frozen
systems occupy separate habitats and share the same five seed stations. The
screen shows run status, current physical run, elapsed time, median-based ETA,
and technical failures, but deliberately contains no loss values, held-out
measurements, rankings, model output, or provisional winner.

```text
http://localhost:4173/heldout.html
```

The local slice joins two independently hashed, versioned files: an unchanged
`scienceutopia.held-out-progress.v1` snapshot from a synthetic UI-test
registry, and a conspicuously labelled synthetic 3 × 5 presentation grid. It
does not read the active registry, experiment worktree, or raw outputs. See
`research/tracks/game-ui-heldout-progress-v1.md` for the future verified
adapter boundary.

- [synthetic held-out relay](screenshots/noctiluca-heldout-relay-synthetic.png)

## Deterministic review scene

The review URLs fix replay time and motion state:

```text
http://localhost:4173/?cursor=14000&motion=reduced
http://localhost:4173/?cursor=20000&motion=reduced
http://localhost:4173/?cursor=26000&motion=reduced
http://localhost:4173/?cursor=43000&motion=reduced
```

To open the evidence trace for Aya's active writing action:

```text
http://localhost:4173/?cursor=14000&motion=reduced&select=action%3Aaya-write
```

At a 1440x1050 browser viewport this is the fixed visual-review scene. The
logical canvas remains 480x270 and only integer display scaling is used.

- [paper and researcher action](screenshots/noctiluca-v3-paper-action-cursor-14000.png)
- [derived action evidence](screenshots/noctiluca-v3-action-evidence-cursor-14000.png)
- [review network and four-district world](screenshots/noctiluca-v4-review-network-cursor-20000.png)
- [publication and funding activity](screenshots/noctiluca-v4-publication-funding-cursor-26000.png)
- [publication action evidence](screenshots/noctiluca-v4-publication-evidence-cursor-26000.png)
- [funding and allocation](screenshots/noctiluca-v3-funding-cursor-28000.png)
- [policy transmission](screenshots/noctiluca-v3-policy-cursor-43000.png)
- [intervention branch comparison](screenshots/noctiluca-branch-compare-cursor-43000.png)
- [branch intervention evidence](screenshots/noctiluca-branch-compare-intervention-evidence.png)
- [verified researcher writing interior](screenshots/noctiluca-life-writing-seed521-cursor-6200.png)
- [verified peer-review interior](screenshots/noctiluca-life-review-seed521-cursor-20200.png)
- [verified funding application interior](screenshots/noctiluca-life-application-seed521-cursor-36500.png)

## Evidence contract

The browser loads:

- `public/data/vertical-slice.replay.json`: replay-view v2 data;
- `public/assets/noctiluca/asset-pack.json`: stable asset identities and
  logical display sizes.

The comparison page additionally loads
`public/data/intervention-branches.manifest.json` and its two declared replay
documents. The manifest fixes the shared-origin event count/hash/terminal event,
each complete branch hash, and each canonical intervention event ID. A mismatch
blocks the verified state. Final paper status and balance labels are read from
authoritative `projection.frames`, never inferred in TypeScript.

Replay data separates four layers:

1. `canonical.events`: source event stream;
2. `projection.frames`: authoritative projected state;
3. `choreography`: deterministic, evidence-linked display instructions;
4. `ambient`: presentation with no scientific claim.

The client recursively canonicalizes and recomputes SHA-256 over
`canonical.events`. It displays `STREAM VERIFIED` only when that digest equals
the supplied `stream_hash`. Scientific flows and actor actions must be
`derived`, name at least one existing canonical event, and carry their
derivation version. Without an explicit action record, a researcher remains
idle; the browser does not infer work from role or outcome. Ambient records may
not claim canonical evidence. A missing replay or production asset
produces an explicit error; the renderer does not substitute emoji, text
glyphs, generic geometry, or invented events.

Truth status is redundant by design: label, line pattern, and colour distinguish
canonical, derived, and ambient presentation. Every entity, flow, and event is
also exposed through a keyboard-operable semantic DOM mirror.

## Controls

- drag, arrow keys, or `W A S D`: pan;
- wheel, `+`, or `-`: integer zoom;
- `F`: follow selected entity;
- Space: play or pause;
- `[` / `]`: step backward or forward;
- Escape: close evidence inspector;
- bottom filters: toggle the six flow layers;
- view controls: follow, high contrast, reduced motion, and atmosphere.

The minimap occupies the upper-right of the logical canvas. Canvas state is
mirrored to semantic buttons for keyboard and screen-reader navigation.

## Timestamped pre scale progress

`pre-scale.html?source=recorded` opens the committed historical snapshot.
`pre-scale.html?source=latest` explicitly selects a separate local journal
projection and checks that file every30 seconds. A missing/tampered file clears
the displayed outcomes; it never silently loads the older recorded file.
The page makes only same-origin read requests and starts no model or experiment.

The optional finite watcher reads the immutable M/O/E journals and publishes
only changed recorded facts. Its observation date does not refresh on unchanged
polls, and neither a dated projection nor a stage-start record proves that a
scientific process is live. Completed, stopped and started-without-terminal
stage records are displayed separately. Readiness receipts retain their own
source, distinct from the search source and its required fresh readiness.

From a clean pinned helper checkout, with explicit actual run paths:

```sh
/absolute/path/to/project/.venv/bin/python -m scripts.watch_pre_scale_observatory \
  --information-run /absolute/path/to/information-run \
  --search-run /absolute/path/to/search-run \
  --output /absolute/path/to/game-ui-v2/public/data/pre-scale-observatory.latest.json \
  --status-output /absolute/path/to/outputs/observer/last-status.json \
  --interval 30 --maximum-seconds 86400
```

Use the approved project interpreter, never Apple-provided Python. Both output
targets must be fresh and outside the scientific run directories. Keep the
status journal outside `public/` to avoid unnecessary development-server reloads.
The watcher stops on integrity errors, three consecutive incomplete file
publications, the finite deadline, or both scientific completion records;
completion records are not full audits. It leaves scientific writers untouched.
The local projection/lock are ignored by Git. Treat them as local observation
files, not reviewed release artifacts; static builds can copy public files.

## Replay architecture boundary

`src/replay.ts` validates and joins canonical entities with versioned visual
placements, actions, and flows. `src/ArcologyScene.ts` renders only validated
entities and choreography. Frame selection, actor position, workstation
activity, rain, courier position, and packet position are functions of replay
cursor and reduced-motion state; a paused cursor is a stable frame. `src/main.ts` owns transport, evidence
inspection, accessibility, hash verification, and deterministic review
parameters. Adding a new scientific browser animation must not duplicate
simulator logic: add a canonical event or a versioned deterministic derivation
first.
