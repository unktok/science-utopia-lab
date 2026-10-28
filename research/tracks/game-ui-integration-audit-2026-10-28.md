# Game UI integration audit — 2026-10-28

Status: integrated and locally verified on
`integration/game-ui-complete-20261028`, based on main commit `9138ab3`.

## Commit audit and integration order

1. Branch-comparison source commit `111ba185` was audited against main's
   replayed commit `f46c900`. All relevant game UI, replay adapter, fixture,
   test, script and track-document trees are identical, so the source commit
   was not cherry-picked a second time.
2. Collaboration Evidence Navigator `6f681f0` was cherry-picked first as
   integration commit `955e121`.
3. Optimizer Observatory `03eac30`, whose parent is `6f681f0`, was
   cherry-picked second as integration commit `60f7d93`.

Both cherry-picks applied without textual conflicts. This order preserves the
parent-child UI history and avoids duplicating branch-comparison fixtures.

## Runtime visual reconciliation

The first integration capture correctly detected two stale visual baselines:

- the Evidence Navigator footer changed because the Observatory toggle is now
  part of the integrated command deck;
- branch comparison had inherited later renderer improvements since its
  original branch-local capture.

The three affected PNG contracts were regenerated from the integrated runtime,
each repeated with a separate empty Chrome profile and compared byte-for-byte.
Branch comparison screenshots are now also covered by the automated screenshot
hash suite with their native 1440x1000 dimensions.

## Verification

- Vitest: 92 passed across 12 files, including branch compare, evidence graph,
  observatory and deterministic image contracts.
- TypeScript typecheck: passed.
- Vite production build: passed, including `index.html`, `compare.html`,
  `hub.html`, `sandbox.html` and `mission.html`.
- `npm audit --audit-level=high`: zero vulnerabilities.
- Integrated Evidence Navigator capture:
  `aa90b4af0ade0d5c06a552d1201f0602c2140d50426d67e906694c61c738f0a3`.
- Integrated Optimizer Observatory capture remained byte-identical to its
  source branch:
  `3cb506556f1e9e8d7096db867126931e51c9cb528fab34bc417ca579909e29e8`.
- Integrated branch comparison and evidence captures:
  `e9770f5e2642e42be1ea6fe6113c3b332e9df70cec68c74d58fa772f7cc34045`
  and `8cf89a226221ac617f6e54d5fc24e31ce08eb5dc1d9b1a000a393236e4d5d89b`.

## Safety and remaining risk

No active v1.1 experiment worktree, held-out registry, or raw output was read or
modified. Main was not merged or pushed.

The production build continues to warn that the Phaser replay chunk is larger
than 500 kB. This is a performance/code-splitting risk, not a correctness or
truth-boundary failure. The integration adds no live experiment reader; the
Optimizer Observatory remains bound to its timestamped verified snapshot or an
explicitly synthetic fixture.

The branch-comparison Python replay test was not rerun in this integration
worktree because neither a project virtual environment nor `pytest` in the
approved user Python was available. Its source and fixtures are byte-identical
to main's already integrated `f46c900`; the browser-side branch test and both
runtime comparison views passed here.
