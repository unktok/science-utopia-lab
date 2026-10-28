# Game UI: cinematic canonical activity v1

Status: implemented and locally verified on
`track/game-ui-cinematic-activity`.

## Outcome

The verified seed-521 replay now reads as a 48-second research-world sequence,
not a dense event dump. Twelve canonical actors visibly walk between their
fixed home positions and work stations, write two papers, complete four peer
reviews, return home, and receive two grant transfers. Paper, review, and
funding handoffs remain spatial flows. The default fixture is the real
commit-pinned campaign; the synthetic contract remains available only through
the allowlisted `?replay=synthetic` alias and is visibly labelled
`SYNTHETIC CONTRACT` instead of `VERIFIED REAL CAMPAIGN`.

The portable bundle is 921,113 bytes with SHA-256
`5a14e9066c4c8ddf09342e46c38e83a69531a1e7bed9a146fb67898eb8783fcf`.
Its canonical Python and browser-normalized stream hashes did not change:

- Python: `ba0bb641d99888246b349bcce153340beff7ab21a5a0c1ed0052c7f31a6ba540`
- browser: `c37b5e4d23fb2332641b545054bd2fda97836f1b9ecb29d9c252dd94a03fdc39`

## Projection-only boundary

The browser still receives no raw simulator checkpoint and performs no
scientific-state inference. Python converts the verified artifacts to 71
canonical events, replays each prefix into 72 authoritative projection
frames, and assigns a deterministic presentation timestamp to each event.
Portable validation now also rejects a projection frame whose timestamp does
not equal its canonical fact timestamp.

The cinematic layer contains only evidence-linked presentation records:

- 20 actor actions: 12 `move`, two `write`, four `review`, two `receive`;
- eight paper/review/funding handoff flows;
- eight event-linked actor camera cues;
- nine stage chapters: assemble, submit, produce, review, decide, apply, fund,
  report, close.

Every route, work action, flow, camera cue, and chapter cites one or more
canonical event IDs. Selecting any of them opens the canonical payload and
provenance plus the authoritative projection immediately before and after the
source event. These are snapshots, not a JavaScript-computed causal claim.

## Deterministic time and space

The adapter allocates fixed stage windows instead of scaling all 71 events
uniformly. Events retain canonical order within each window. The browser may
play the result at 1x, 2x, 4x, or 8x, jump by canonical event, or jump by
chapter. It never invents an intermediate research state.

Actor paths are Python-authored Manhattan waypoint lists. Path interpolation,
camera centers, placements, and zoom changes use integer geometry. Camera
follow chooses only an explicit selected actor or an evidence-linked camera
cue. Pixel art continues to use the repository-owned NOCTILUCA asset pack and
its fixed `noctiluca-24-v0.1` palette; no external or generated asset was
introduced in this slice.

## Historical source and claim boundary

The default fixture remains the completed `first-closed-loop-engineering`
campaign, revision `9a10029807d5`, source commit
`0b733df425405f5e2eeb953cff2a7288f13f5af9`, suggestion
`s5aad19dd3da73bc8`, seed 521. It completed on 2026-10-27 and is an engineering
demonstration only. It is not the running metric-conditioned v1.1 result, a
policy result, or evidence of scientific optimality. This track only read the
historical source artifacts and did not modify the frozen experiment
worktree.

## Verification evidence

- Python replay/adapter suite: 24 passed.
- Vitest UI suite: 24 passed.
- TypeScript and Vite production build: passed.
- review choreography screenshot, 1440x1050, two byte-identical captures:
  `5a20b9df6775a814974cd9a4a428d1cbc9f870b71ff42c1a24d5d97dfe9551ea`.
- funding evidence screenshot, 1440x1050, two byte-identical captures:
  `f5fd5245077c45c503d16586038eba0a9623acb80c0e97b3714b5c3686d98cd1`.

The screenshots intentionally keep the inspector open: the world activity,
its source classification, canonical cause, provenance, and authoritative
before/after projections must be reviewable in the same frame.
