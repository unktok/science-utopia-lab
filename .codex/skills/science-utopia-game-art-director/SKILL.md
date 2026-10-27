---
name: science-utopia-game-art-director
description: Direct and review Science Utopia game visuals when creating pixel art, world scenes, information-flow animation, or replay UI; enforce the project art bible and evidence integrity.
---

# Science Utopia game art director

Use this skill for work that changes the Science Utopia game's visual world,
pixel assets, animation, camera, HUD, or institutional information flows. Do not
invoke it for simulator-only or ordinary research-document changes.

## Required context

Before proposing or editing game visuals, read:

- `game-ui/ART_BIBLE.md`
- `game-ui/ASSET_MANIFEST.yaml`
- `research/tracks/game-ui-v2-creative-direction.md`
- the fixed replay fixture and the most recent deterministic screenshot

Inspect the current rendered screen before changing it. Treat generated concept
art as a target or source of ideas, never as a production sprite sheet.

## Outcome

Produce a coherent, original cyberpunk scientific city in which researchers,
institutions, and information flows are legible at native pixel scale. Preserve
the authoritative replay boundary: every scientific action must be canonical or
deterministically derived and link back to evidence; atmosphere must be marked
ambient.

## Working loop

1. Define one scene goal and the exact replay/cursor/camera/viewport used to
   judge it.
2. Identify the smallest missing asset and event vocabulary needed for that
   scene.
3. Create or revise grid-aligned assets under the frozen palette and manifest.
4. Implement deterministic choreography without duplicating simulation logic
   in the browser.
5. Capture the fixed scene at 1× and display scale.
6. Review composition, silhouette, pixel grid, palette, motion, institutional
   storytelling, data legibility, evidence links, and accessibility.
7. Iterate on the largest visible failure; do not expand the asset set until the
   vertical slice passes.

## Non-negotiable checks

- no antialiased or smoothed production pixels;
- integer coordinates and integer display scale;
- no generic Unicode, emoji, CSS clip-art, or borrowed game assets;
- roles, buildings, and flow types recognizable without color alone;
- no invented scientific activity or inferred emotion;
- canonical, derived, and ambient motion visibly distinguishable;
- deterministic screen capture for the same replay state;
- reduced-motion, high-contrast, keyboard, and semantic DOM paths retained;
- generated images redrawn and reviewed before becoming game assets;
- prompt, source, authoring revision, license, and acceptance decision recorded.

Report the final scene path, screenshot path, replay position, asset-manifest
changes, evidence coverage, and remaining quality failures.
