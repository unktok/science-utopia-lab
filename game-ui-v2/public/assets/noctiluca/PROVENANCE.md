# NOCTILUCA asset provenance

## Production runtime assets

Status: `production-grid-v0.1`. The runtime manifest loads the thirteen SVGs
under `production/`: three researchers at 24x32, four institutions at 96x80,
and six flow packets at 8x8. They were hand-authored for this repository on
2026-10-27 from integer-aligned `rect` primitives using only the frozen
NOCTILUCA 24-colour palette. They declare `shape-rendering="crispEdges"` and
contain no curves, transforms, filters, opacity, gradients, or embedded raster
images.

The institution silhouettes are purpose-specific rather than recoloured
shells:

- the laboratory has an asymmetric sample tower, external service pipes,
  greenhouse stair-step roof, wet-lab benches, and living samples;
- the peer-review exchange has mirrored anonymous booths around an elevated
  routing eye, queue columns, and decision lamps;
- the funding authority is a heavy stepped ledger vault with application
  intake, a visible allocation ledger, and outward resource ports;
- the publication spine uses offset page towers, open repository racks, a
  publication conveyor, and citation beacon.

`test/assets.test.ts` enforces palette membership, exact grid dimensions,
integer rectangle geometry, required manifest keys, and common antialias-risk
constructs. Semantic silhouette recognition and accessibility are reviewed in
the deterministic browser capture.

## Concept references

Status: `visual_target_only`. These images are integrated to test composition,
silhouettes, and the six-flow visual grammar. They are not fixed-grid
production sprites and are not loaded by `asset-pack.json`.

All thirteen PNGs were created with OpenAI's built-in image generation tool on
2026-10-27 for this repository. The generated source images have transparent
backgrounds. The runtime manifest scales them to their intended logical sizes.

## Prompt set

- Researchers: three separate prompts for an early-career scientist, a
  principal investigator, and a peer reviewer, each as a full-body cyberpunk
  pixel-art character with a distinct silhouette, observable work props, no
  text or logos, and the NOCTILUCA indigo/cyan/magenta/ivory palette.
- Institutions: four separate prompts for a laboratory arcology, peer-review
  exchange, publication/archive spine, and funding authority, each as a
  readable cutaway cyberpunk pixel-art building with a unique silhouette,
  visible institutional activity, no labels, and transparent surroundings.
- Flows: six separate prompts for data, paper, review, funding, citation, and
  policy packets. Each requested a materially different silhouette and motion
  language matching the flow grammar in the art bible, with no text and a
  transparent background.

The PNG filenames are stable archival identities for concept references only;
the runtime identities in `asset-pack.json` point to the production SVGs. Raw
generator execution identifiers are intentionally not part of the application
contract.
