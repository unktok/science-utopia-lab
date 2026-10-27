# Game UI v2 — creative direction and production plan

Status: creative preproduction started on 2026-10-27

## Decision

The existing UI remains useful as an auditable replay-viewer prototype, but it
is not the visual target for the game. The next slice will replace its CSS
campus with an original cyberpunk scientific city while preserving the
authoritative replay/projector boundary.

The working world name is **NOCTILUCA // Research Arcology**. The interaction
loop is not “maximize one score.” It is:

```text
observe → trace evidence → form a hypothesis → change a SystemSpec
        → run a new branch → compare seeds and outcomes → explain side effects
```

## Evidence from the prototype audit

The first slice already supplies playback, scrubbing, canonical payload
inspection, a stream identity, keyboard access, and deterministic Python replay
projection. Those are foundations to retain.

The game layer is still missing: there are no production pixel assets; the map
contains four hard-coded rectangular buildings; the single character shape
moves directly between coarse destinations; there is no camera, pathfinding,
interior, information-flow layer, knowledge map, or intervention loop. The
current event vocabulary also cannot honestly show writing, collaboration,
citation, or government action. New native events and truth-status-aware visual
choreography must therefore be developed with the renderer.

## Tooling choice

The first production spike should use **Phaser 3 + TypeScript/Vite + Tiled**,
with Aseprite sources for hand-finished assets. Phaser provides web-native
scenes, cameras, animations, tilemaps, batching, and input while remaining easy
to integrate with the existing browser evidence inspector. Tiled custom
properties can encode institution type, event ports, navigation zones, and
interior anchors.

PixiJS remains a fallback if the work becomes primarily custom visualization;
Godot should be reconsidered if Science Utopia becomes a standalone game
product. Direct Canvas is suitable for sketches but would require rebuilding
camera, animation, tilemap, culling, particle, and scene systems.

Primary production references:

- [Phaser scenes](https://docs.phaser.io/phaser/concepts/scenes),
  [cameras](https://docs.phaser.io/phaser/concepts/cameras),
  [animations](https://docs.phaser.io/phaser/concepts/animations), and
  [tilemaps](https://docs.phaser.io/api-documentation/class/tilemaps-tilemap)
- [Tiled custom properties](https://doc.mapeditor.org/en/stable/manual/custom-properties/)
- [Aseprite animation](https://www.aseprite.org/docs/animation) and
  [sprite-sheet export](https://www.aseprite.org/docs/sprite-sheet/)
- [MDN crisp pixel art](https://developer.mozilla.org/en-US/docs/Games/Techniques/Crisp_pixel_art_look)
  and [Canvas optimization](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Optimizing_canvas)

## Design references and extracted principles

Existing games are used to study principles, not to copy assets or a house
style. RimWorld's public design talks motivate treating agent events as a story
generator; city-simulation work motivates spatial agents and inspectable causal
flows; Factorio's logistics clarify that moving packets and network coverage can
be the world rather than decoration. A smaller workplace view can imply a large
city, so the camera should travel between macro networks and researchers' desks.

- [RimWorld: Contrarian, Ridiculous, and Impossible Game Design Methods](https://media.gdcvault.com/gdc2017/Presentations/Sylvester_Tynan_RimWorld_Contrarian_Ridiculous.pdf)
- [GDC city-simulation presentation](https://media.gdcvault.com/gdc2024/Slides/GDC%2Bslide%2Bpresentations/GDC24_GuillaumePierre_CitySimulation_SimCity_Cityscapes.pdf)
- [Factorio logistic network](https://wiki.factorio.com/Logistic_network)
- [Cities: Skylines II economy development diary](https://www.paradoxinteractive.com/games/cities-skylines-ii/news/dev-diary-economy-part-one)

The code-and-art feedback loop follows the documented pattern of setting a
visual target, implementing, capturing the same scene, comparing, and iterating
with an independent review context:

- [Claude Code best practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [OpenAI harness engineering](https://openai.com/index/harness-engineering/)

## Runtime and replay architecture

The browser remains presentation-only for scientific state. A replay-view v2
should separate:

1. canonical facts and event identity;
2. authoritative projected state;
3. deterministic visual choreography;
4. ambient presentation with no scientific meaning.

Choreography records its source event IDs, derivation version, truth status,
logical timestamps, duration, and causal parent. The browser recomputes the
canonical JSON hash and compares it with the export manifest before displaying
“verified.”

World rendering uses a fixed simulation tick, deterministic layout seed,
integer coordinates, texture atlases, and semantic zoom. A DOM overlay mirrors
selected canvas entities for accessibility and evidence inspection.

## Production stages

### Stage 0 — creative preproduction

- freeze the art bible and asset manifest;
- compare three original visual directions;
- finish one researcher action sheet, three institution concepts, and all six
  flow packets;
- approve one fixed replay/camera/time screenshot as the visual regression
  scene.

### Stage 1 — Observatory v2

- Phaser viewport, pan/zoom/follow, minimap, and Tiled map;
- three custom institutions and three researcher characters;
- canonical/derived/ambient truth labels and browser hash verification;
- evidence inspector retained from the existing prototype.

### Stage 2 — living ecosystem

- deterministic action state machines, pathfinding, interior cutaways;
- paper, data, review, funding, citation, and policy flow layers;
- native event expansion for activities the UI currently cannot claim;
- knowledge graph overlay and high-density aggregation.

### Stage 3 — policy architect

- SystemSpec mechanism graph editor;
- branch submission without mutating an existing replay;
- shared-timeline and ghost-trail comparison across systems and seeds;
- separate loss, technical validity, held-out metrics, and policy displays.

### Stage 4 — polish and scale

- 1,000+ agent LOD and performance budgets;
- atmosphere, audio, accessibility, and localization;
- Playwright, axe, deterministic screenshot/video, visual regression, and
  scale tests.

## First completion gate

The next milestone is complete only when a real 30–60 second replay shows at
least three distinct researchers, three institutions, and six semantic flows;
all scientific actions are evidence-linked; the same replay/cursor/camera gives
the same screenshot; the world supports pan/zoom/follow and reduced motion; and
no borrowed game asset, Unicode substitute, or unedited generated sprite is
present.
