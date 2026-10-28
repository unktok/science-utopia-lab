# Game UI: epistemic flow layer v1

Status: implemented and locally verified on
`track/game-ui-epistemic-flow-v1`, based on cinematic replay commit `43db510`.

## Outcome

NOCTILUCA now exposes a separate epistemic layer over the verified seed-521
campaign. It shows how manuscripts, peer reviews, publication decisions,
funding applications, and grant awards traverse the city while researchers
perform the already evidence-linked cinematic actions.

The layer contains four derived institutional relay nodes and 20 routes:

- two manuscript routes: author → submission relay → canonical paper;
- four review routes: reviewer → review exchange → canonical paper;
- two decision routes: canonical paper → publication spine;
- ten application routes: researcher → funding ledger, grouped per actor from
  26 canonical `funding_application_cost` events;
- two award routes: funding ledger → researcher from canonical `grant_income`
  events.

The default bundle remains the completed campaign revision `9a10029807d5`,
seed 521, source commit
`0b733df425405f5e2eeb953cff2a7288f13f5af9`. It is 949,671 bytes with SHA-256
`bfa72a9f4ffab61850a46f87dd6d36f454631dcee4f97572f29529c0a26c75ee`.
The canonical stream hashes are unchanged:

- Python: `ba0bb641d99888246b349bcce153340beff7ab21a5a0c1ed0052c7f31a6ba540`
- browser: `c37b5e4d23fb2332641b545054bd2fda97836f1b9ecb29d9c252dd94a03fdc39`

## Projection and claim boundary

Python remains the only component that interprets campaign artifacts. Every
workflow node and route is a deterministic presentation record with canonical
event IDs. The browser renders declared paths and authoritative projection
snapshots; it does not infer a new scientific transition, institution, actor,
causal effect, or policy conclusion.

The relay names are interface vocabulary, not claims that the simulator had
additional stateful organizations. Their `truth_status` is `derived`, never
`canonical`. Opening a route shows its source payload and provenance plus the
authoritative projection immediately before and after each cited event.

The verified/synthetic distinction fails closed. A bundle marked empirical
must use the verified commit-pinned source kind and must contain evidence-linked
epistemic flows. A synthetic fixture cannot claim that verified source kind.
The visible header continues to label the two modes `VERIFIED REAL CAMPAIGN`
and `SYNTHETIC CONTRACT`.

## Semantic validation

Python and TypeScript independently reject a route when:

1. a canonical reference is missing;
2. its declared event type differs from any source event;
3. manuscript/review actor and paper endpoints differ from the source event;
4. a decision does not originate at its canonical paper;
5. an application cites anything except one actor's
   `funding_application_cost` events;
6. an award cites anything except one `grant_income` event for its recipient;
7. an endpoint is unknown or lacks a deterministic placement;
8. a path has fewer than two points, uses non-integer geometry, or does not
   begin and end at the declared entities.

The application layer deliberately aggregates only for legibility. Each route
retains all of its source IDs, and the status ribbon reports the number of
canonical events currently represented.

## Pixel-art extension

The repository-owned `noctiluca-production-v0.4` pack adds nine hand-authored
SVGs: four 32x32 workflow relays and five 10x10 epistemic packets. They use
integer-aligned rectangles, `crispEdges`, and only the frozen
`noctiluca-24-v0.1` palette. Submission, review, publication, and funding relay
silhouettes differ structurally. Manuscript, review seal, decision,
application, and grant packets use different visual grammars rather than
colour-only variants. Asset tests reject external colours, curves, transforms,
filters, antialias-prone geometry, missing keys, and dimension drift.

## Interaction and accessibility

Each of the five epistemic kinds can be toggled independently. The live status
ribbon names active kinds and cited-event count. Packet and label selection
open the evidence inspector, while the offscreen semantic mirror exposes every
workflow node and route to keyboard users. Reduced-motion mode fixes packets at
a deterministic route position; ordinary playback follows their authored
Manhattan paths.

## Verification evidence

- Python replay/adapter suite: 26 passed.
- Vitest UI/asset/screenshot suite: 28 passed.
- TypeScript and Vite production build: passed.
- Actual campaign re-export: byte-identical to the committed portable bundle.
- Review screenshot, 1440x1050, two byte-identical captures:
  `db48e5764458655d5dc4a9842642bd4b9e0ad710f82380de73390f92b1ef8b81`.
- Application-network screenshot, 1440x1050, two byte-identical captures:
  `33680042350acf333af329822976b05121c4da0ed514e9eb90398bd097147fe7`.
- Award screenshot, 1440x1050, two byte-identical captures:
  `f6d1e26f6e13ffb9deaa21f98457e6223808c46a3c204f1cc8899592ba20daf5`.

The frozen metric-conditioned v1.1 worktree was read only for the already
commit-pinned historical source artifacts and was not modified.
