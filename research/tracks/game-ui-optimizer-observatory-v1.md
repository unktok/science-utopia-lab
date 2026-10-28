# Game UI: Optimizer Observatory v1

Status: implemented and locally verified on
`track/game-ui-optimizer-observatory-v1`, based on collaboration-evidence
navigator commit `6f681f0`.

## Outcome

The verified research city now contains an optimization observatory that makes
the closed-loop structure legible without claiming unfinished results:

```text
LossSpec arm → candidate system design → seed run → score observation → winner freeze → report
```

The observatory loads the existing machine-readable mission-control snapshot,
parses and hash-verifies it with the shared adapter, and projects three arms,
nine registered candidates and 27 logical seed runs. `O` toggles the deck;
keys 1–3 switch LossSpec arms and Left/Right switch registered candidates.

## What changes under optimization

The UI deliberately distinguishes the conditioning target from the optimized
variable:

- LossSpec says what the optimizer will minimize;
- system design is the candidate variable being searched;
- seeds are repeated evaluations of one design under one LossSpec arm;
- score would rank designs only after it is actually exported;
- winner freeze is a later explicit state transition, never a visual guess.

The current snapshot registers the same three initial candidate identities in
all arms. The observatory therefore says metric-conditioned design divergence
is `NOT OBSERVED` at this timestamp. Switching metrics still rebinds the arm,
campaign, interpretation, candidate/run state and provenance, but does not use
layout or colour to pretend that distinct designs have already emerged.

## Result and provenance boundary

The shared mission contract requires a clean source commit, three LossSpec
arms, a locked held-out registry and zero frozen winners. SHA-256 verification
runs before rendering. The verified source is timestamped
`2026-10-28T03:13:08.338710+00:00`; it is a snapshot, not a live read of the
active experiment.

The contract contains no objective score field. Every seed therefore receives
the typed state `{ status: "not_observed", value: null }`, including seeds
whose execution status is complete in the synthetic fixture. Complete execution
is not silently converted into a score. Winner remains `not_frozen` and report
follows the exported locked workflow stage.

`?observatory=synthetic` loads the separately hashed UI-test fixture. The panel
border and badge visibly change to `SYNTHETIC DEMO FIXTURE`; its mixed run
states never become verified findings.

## Presentation boundary

The adapter types these fields as `presentation_only`:

- district layout and facility shapes;
- packet routes and packet animation;
- colour and narrative labels.

They cannot create candidates, runs, scores, winner state, workflow state or
provenance. Reduced motion collapses packet animation through the existing
global contract.

## Accessibility and responsive behavior

- LossSpec tabs and candidate towers are native buttons with pressed state.
- Text labels redundantly encode every run, execution, score and freeze state.
- `O`, 1–3, Left/Right and Escape are supported without stealing keys while
  the observatory is closed.
- At widths below 900px the observatory becomes a truth-rail-safe, full-screen
  scrolling terminal with a linear objective→design→run→score→freeze flow.
- A 720x900 Chromium review passed.

## Historical source and active-run safety

The verified fixture is the already tracked read-only mission snapshot. No
active metric-conditioned v1.1 file, registry, process or worktree was changed.
The UI does not imply that the active study has completed, has a winner, or has
produced held-out/report results.

## Verification evidence

- Observatory contract/UI tests: 5 passed.
- Complete Vitest suite: 90 passed.
- Verified observatory, two byte-identical 1440x1050 captures:
  `3cb506556f1e9e8d7096db867126931e51c9cb528fab34bc417ca579909e29e8`.
- Synthetic observatory, two byte-identical 1440x1050 captures:
  `aab0d3d7c930a235d6d7bd4680715efbd3c91ad66b6fbabf39d88ee317a58892`.
- TypeScript typecheck and Vite production build: passed.
- Dependency audit: zero vulnerabilities.
