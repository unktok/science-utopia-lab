# Game UI: Evidence Quay authoritative operations v2

Status: implemented and locally verified on
`track/game-ui-evidence-quay-v2`, based on research-arcology hub commit
`88078c6be1a5c8c4041f03a34a97f3db8a484a0d`.

## Outcome

The verified replay now has an in-world operations dock that makes one precise
relationship visible at replay time: the latest applied canonical event, the
exact authoritative frame produced after that event, the researchers named by
the event, and their frame-recorded resource state. A pixel route then stages
that evidence as research, manuscript, review, decision, funding, reporting,
or year-close work inside Evidence Quay.

The route is synchronized with the replay cursor. Review packets travel from a
lab berth to the review tower, manuscript packets to the submission pier, and
funding packets to or from the funding exchange. Researcher buttons expose the
canonical entity dossier and the event console opens the existing canonical
cause/frame inspector. `Q` focuses the current event for keyboard users.

## Truth boundary

`src/evidenceQuay.ts` deliberately has a smaller input boundary than the
existing cinematic renderer. Its evidence projection reads only:

- `metadata` to require an empirical, commit-pinned campaign source;
- `canonical.events` for actor, artifact, event kind, category, and outcome;
- `canonical.entities.researchers` to restrict actor identity;
- `projection.frames` for the exact post-event authoritative state.

It does not read choreography actions, flows, epistemic routes, interiors, or
ambient records. Each event must match frame `sequence + 1`, the frame must
repeat the event timestamp, and `state.applied_event_ids` must contain the
event. Missing, reordered, synthetic, or unknown activity inputs fail closed.

The following are not scientific state and are always declared
`truth_status: presentation_only`:

- researcher movement between visual facilities;
- facility names and route endpoints;
- courier and packet positions;
- interpolation and persistence between canonical event timestamps.

The operations dock repeats this boundary in the visible world and adds
`PRESENTATION-ONLY` to the truth legend. The browser never converts these
motions into a result, balance, paper status, or policy conclusion.

## Historical source and claim boundary

The standard source remains the completed seed-521 engineering campaign,
campaign revision `9a10029807d5`, source commit
`0b733df425405f5e2eeb953cff2a7288f13f5af9`. Its portable bundle SHA-256 is
`2097889201a675594b3ea13567c17017dcbc366a0526e982afce6829af777422`.

This is not the running metric-conditioned v1.1 result, a policy result, or an
optimality claim. The active v1.1 experiment worktree was not read or changed
for this slice.

## Accessibility and responsive behavior

- Native event and researcher buttons support inspection without canvas
  pointer interaction.
- `Q` focuses the current canonical event; existing replay and camera keys are
  unchanged.
- The semantic canvas help names the new keyboard target.
- Reduced motion removes courier transitions while retaining route position.
- At narrow widths the event evidence remains visible and the secondary worker
  roster collapses, avoiding horizontal overlap with the city.
- The synthetic replay keeps the shell but disables the layer with an explicit
  fail-closed message rather than showing verified activity.

## Verification evidence

- Evidence Quay contract tests: 5 passed.
- Complete Vitest suite: 59 passed.
- TypeScript typecheck and Vite production build: passed.
- Review capture at cursor 20,200 ms, two byte-identical runs:
  `d0a1aeec6f9d90b9e0a930f2e44011022c138a5e0e9106ccd378b9b18bd5d530`.
- Funding-application capture at cursor 36,500 ms, two byte-identical runs:
  `bb440d6db67ff7bac71811a0c8238dcbab889e5f510c6952610bd12cdf197ff6`.

Both captures use a 1440x1050 viewport, fixed replay cursor, verified campaign
source, and reduced motion. The canonical event, authoritative frame number,
researcher, balance, and presentation-only route boundary are visible together.
