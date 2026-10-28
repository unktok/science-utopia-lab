# NOCTILUCA asset provenance

## Production runtime assets

Status: `production-grid-v0.6`. The runtime manifest loads thirty-four SVGs under
`production/`: four six-frame researcher sheets with 24x32 frames, four
institutions at 96x80, six flow packets at 8x8, and a 16x8 ambient courier.
They were hand-authored for this repository on 2026-10-27 and 2026-10-28 from
integer-aligned `rect` primitives using only the frozen
NOCTILUCA 24-colour palette. They declare `shape-rendering="crispEdges"` and
contain no curves, transforms, filters, opacity, gradients, or embedded raster
images.

Version 0.4 adds four 32x32 institutional relay nodes and five 10x10 epistemic
packets, hand-authored on 2026-10-28. Submission, review, publication, and
funding relays have different silhouettes rather than colour swaps. Manuscript,
review seal, decision, application, and grant packets likewise use distinct
paper, aperture, routing fork, form, and ledger/token geometry. These assets
only render evidence-linked Python-authored routes; they do not create events.

Version 0.5 adds five 32x24 cutaway workstations for manuscript synthesis,
anonymous review, funding applications, publication decisions, and grant
receipt. Each station has a task-specific silhouette and instrument layout.
They are attached only to evidence-linked interior activities. Console flicker
and break-room vapor are drawn separately by the ambient renderer and remain
explicitly cosmetic, with no canonical source IDs.

Version 0.6 adds five 48x40 science-system design glyphs for evaluation,
publication, funding, government, and communication. They are hand-authored
fixed-palette structure icons used only by the synthetic design console. They
do not represent simulated institutions, canonical campaign entities, or
experimental outcomes.

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

Each researcher sheet has paired idle, walk, and domain-work frames. Aya's work
frames carry an instrument probe and sample pulse; Sol's carry an allocation
ledger and policy broadcaster; Mino's carry an open manuscript and review seal.
Iren's carry stacked repository pages and a publication beacon.
The frames deliberately change posture and equipment rather than applying a
generic glow. The browser chooses frames from the replay cursor, so paused and
reduced-motion scenes are deterministic.

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
