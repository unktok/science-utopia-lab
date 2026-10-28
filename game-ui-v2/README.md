# NOCTILUCA // Research Arcology renderer

This directory contains the Phaser 3 vertical-slice renderer for the Science
Utopia game UI. It is an auditable presentation layer over replay-view v2. It
does not run scientific mechanisms or infer missing scientific activity in the
browser.

## Current status

The v3 renderer is operational with a 48-second deterministic, synthetic
fixture containing three researchers, three institutions, fourteen canonical
events, fifteen evidence-linked actor actions, and all six information-flow
types. Researchers walk to institution work areas and use role-specific
experiment, writing, review, allocation, citation, and policy poses. This
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

The asset tests enforce the production manifest, sprite-sheet dimensions,
required keys, frozen palette, integer geometry, crisp-edge declaration, and a
rect-only SVG vocabulary. Replay tests enforce that every actor action and
flow is derived from canonical evidence. Silhouette and semantic legibility
remain visual review gates.

## Deterministic review scene

The review URLs fix replay time and motion state:

```text
http://localhost:4173/?cursor=14000&motion=reduced
http://localhost:4173/?cursor=28000&motion=reduced
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
- [funding and allocation](screenshots/noctiluca-v3-funding-cursor-28000.png)
- [policy transmission](screenshots/noctiluca-v3-policy-cursor-43000.png)

## Evidence contract

The browser loads:

- `public/data/vertical-slice.replay.json`: replay-view v2 data;
- `public/assets/noctiluca/asset-pack.json`: stable asset identities and
  logical display sizes.

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
entities and choreography. Frame selection, actor position, rain, courier
position, and packet position are functions of replay cursor and reduced-motion
state; a paused cursor is a stable frame. `src/main.ts` owns transport, evidence
inspection, accessibility, hash verification, and deterministic review
parameters. Adding a new scientific browser animation must not duplicate
simulator logic: add a canonical event or a versioned deterministic derivation
first.
