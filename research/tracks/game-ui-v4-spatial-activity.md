# Game UI v4: spatial scientific activity

Status: implemented and locally browser-verified on
`track/game-ui-cyberworld-v4`.

## Purpose

This slice makes the scientific system read as an inhabited 2D cyberpunk world
rather than a dashboard with moving tokens. It closes a complete spatial loop:

```text
lab -> data and paper -> review exchange -> accepted paper -> publication spine
publication spine -> citation -> lab
funding bureau -> capacity -> lab
funding bureau -> policy -> review exchange
```

The deterministic contract fixture now contains four researchers, four
institutions, sixteen canonical events, seventeen derived actor actions, and
seven visible flow records spanning all six flow types.

Canonical stream hash:
`87a0cfac83d9a3377e5ca6cf83942f867ea8552447b23a4324bf19a72b025639`.

## Evidence boundary

The browser still performs no scientific state transition. Authoritative
balances and paper status come from `projection.frames`. Spatial paths and
researcher activities come only from validated `choreography.flows` and
`choreography.actions`, each of which cites canonical event IDs and a derivation
version. The renderer chooses pixels from those records; it does not infer that
someone is experimenting, reviewing, publishing, funded, or affected by policy.

Iren's publication action is explicitly derived from `paper.decided`. Removing
that source reference makes both Python export validation and TypeScript replay
validation fail. Real saved exports continue to emit no actions or flows unless
a derivation supplies them.

## Creative additions

- Publication Spine placed as a fourth district with a unique repository/page
  silhouette and an editor-researcher sprite.
- Two distinct paper journeys: submission to review and accepted publication to
  the repository.
- Citation now originates at the publication repository and returns to the lab.
- Evidence-driven workstation effects for experiments, writing/revision,
  review, publication, funding, citation, and policy.
- Four-researcher simultaneous scenes at review and publication/funding
  moments, with every active action opening its canonical evidence.

## Deterministic visual gate

The 1440x1050 Chromium capture at cursor 26,000 ms and reduced motion was
produced twice with separate profiles and was byte-identical:

`4516ddd36a8da5a295978ccdec13eb8c0417068abf45323de73f532dd4b585b1`

The checked screenshots and hash assertions are under `game-ui-v2/screenshots`
and `game-ui-v2/test/screenshots.test.ts`.

## Remaining work

- directional walking sheets and collision-aware paths;
- a second laboratory and explicit collaboration spaces;
- multiple simultaneous papers and queue aggregation;
- campaign/seed uncertainty overlays that remain separate from the world state;
- external art and accessibility review.
