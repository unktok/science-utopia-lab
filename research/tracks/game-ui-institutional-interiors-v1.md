# Game UI: institutional life cutaway v1

Status: implemented and locally verified on
`track/game-ui-institutional-interiors-v1`, based on Evidence Quay integration
commit `b9680dea603854a6153543e80b34c848d4f2b09d`.

## Outcome

Evidence Quay now opens an institutional interior deck without replacing the
verified research city. The cutaway keeps four simultaneous rooms visible:

- a research laboratory with sample tank, instrument scope, and bench;
- a manuscript room with terminal, archive stack, and paper desk;
- a sealed review room with anonymity booth, score seal, and decision dais;
- a funding assembly with application table, council rail, and ledger vault.

The room selected by the current canonical event lights up and receives a
hand-authored pixel researcher sprite. The sprite changes pose for arrival,
research, writing, review, conference, application, or reporting. A pneumatic
grid moves paper, review, funding, or knowledge packets in sync with the replay
cursor. These visual motions make researchers and institutions feel occupied,
but do not claim simulator facts.

The deck is opened with the `INTERIOR DECK` control, the `I` shortcut, or
`interior=on`. Its evidence action opens the existing canonical event and
authoritative before/after frame inspector.

## Authoritative projection boundary

`src/institutionInterior.ts` builds on the verified Evidence Quay projection
and consumes only:

- canonical event identity, kind, actor IDs, artifact IDs, and payload facts;
- the exact post-event authoritative frame;
- actor state and artifact state selected directly from that frame.

It does not consume choreography actions, routes, interior activities,
epistemic flows, or ambient records. A test deletes all such records and
confirms that every interior scene remains identical. The inherited Evidence
Quay gate requires an empirical, commit-pinned campaign, one frame per event,
matching event ID and timestamp, and an applied-event record. Synthetic or
mismatched sources fail closed.

Every spatial or theatrical choice is typed as
`truth_status: presentation_only`:

- room choice, position, props, furniture, and facility names;
- researcher sprite variant, pose, and walking route;
- packet type rendering, tube path, interpolation, and persistence;
- light, grid, scanline, and institutional ambience.

The deck repeats this boundary above and below the rooms. The visible fact bar
is separately labeled canonical/authoritative and contains only the event,
frame number, actor balance, and artifact status already present in the source
event/frame.

## Pixel-art and interaction design

The interior art uses the established NOCTILUCA fixed palette and integer CSS
geometry. Room silhouettes differ by structure rather than colour alone. Four
deterministic researcher variants use distinct coats, while pose-specific
equipment marks distinguish writing, review, funding, research, conference,
and reporting states.

Reduced-motion mode disables packet transitions while keeping the packet at
its cursor-derived position. The deck uses native buttons, an explicit close
control, a polite authoritative fact status, and keyboard shortcut `I`. At
narrow widths it occupies the available canvas and hides the redundant lower
Evidence Quay card, retaining the truth boundary and fact action.

## Historical source and claim boundary

The source remains the completed seed-521 engineering campaign, revision
`9a10029807d5`, source commit
`0b733df425405f5e2eeb953cff2a7288f13f5af9`. This is not the running
metric-conditioned v1.1 result, a policy result, or evidence of scientific
optimality. The active v1.1 experiment worktree was not modified.

## Verification evidence

- Institutional projection tests: 5 passed.
- Complete Vitest suite: 67 passed.
- TypeScript typecheck and Vite production build: passed.
- Writing room capture, two byte-identical runs:
  `386e32d44b3c94bbe99a5343f0ae0968e0eceb5386ccd0d5e5858f29e47368a6`.
- Review room capture, two byte-identical runs:
  `8a5c715a3dddaebd0b71b2cf4c02a75dc31a747f92fa860c413a2d7c42a5a236`.
- Funding assembly capture, two byte-identical runs:
  `b952e4e69f74fe08d1880de6de7bc68209d7e3461cc477031f11e73ab8e52d94`.

All captures use 1440x1050, verified campaign data, fixed replay cursor,
`interior=on`, and reduced motion.
