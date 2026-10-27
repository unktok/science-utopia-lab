# Game UI vertical slice

Status: integrated in `main`; real-browser prototype verified on 2026-10-27

## Question

Can a player experience agents, artifacts, resources, and time as a small world
while retaining a direct, inspectable link to the canonical research record?

## Decision

The first slice is a read-only replay observatory. It consumes a generated
`scienceutopia.replay-view.v1` artifact containing canonical events and states
projected by the authoritative Python replay code. The browser owns playback
position and presentation only.

This deliberately precedes intervention. Editing a parameter or mechanism will
eventually create a new branch run through the experiment API; it must not
silently mutate an existing replay.

## Included

- play, pause, step, reset, scrub, and speed controls;
- a responsive pixel-art-style campus with researchers and institutions;
- resource, paper, review, decision, and year-completion visibility;
- canonical payload inspection and stream-hash visibility;
- keyboard access, focus indicators, semantic labels, and reduced-motion mode;
- deterministic Python export tests and dependency-free JavaScript model tests.

## Verification

The generated one-year fixture was loaded in a real browser, playback controls
and the read-only event-evidence panel were exercised, and the rendered screen
was captured for remote review. This validates the delivered vertical slice as
an executable UI rather than a static design mock.

## Not included

- simulator or LLM execution;
- `SystemSpec` editing or counterfactual branching;
- multi-run/seed comparison and uncertainty displays;
- a production streaming protocol;
- publication or remote hosting.

## Next boundary

The next useful UI slice should load a campaign manifest, compare two replay
streams on a shared time axis, and expose where metrics came from. A later
intervention slice can submit a versioned `SystemSpec` to the experiment
harness and attach the returned run identity to a new replay branch.
