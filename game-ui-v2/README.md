# NOCTILUCA // Research Arcology renderer

This directory contains the Phaser 3 vertical-slice renderer for the Science
Utopia game UI. It is an auditable presentation layer over replay-view v2. It
does not run scientific mechanisms or infer missing scientific activity in the
browser.

## Current status

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

## Architecture boundary

`src/replay.ts` validates and joins canonical entities with versioned visual
placements, actions, and flows. `src/ArcologyScene.ts` renders only validated
entities and choreography. Frame selection, actor position, workstation
activity, rain, courier position, and packet position are functions of replay
cursor and reduced-motion state; a paused cursor is a stable frame. `src/main.ts` owns transport, evidence
inspection, accessibility, hash verification, and deterministic review
parameters. Adding a new scientific browser animation must not duplicate
simulator logic: add a canonical event or a versioned deterministic derivation
first.
