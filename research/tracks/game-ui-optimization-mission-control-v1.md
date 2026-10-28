# Optimization mission-control v1

## Scope

This slice turns the metric-conditioned v1.1 orchestration state into a
read-only research-operations screen. It answers four questions without
claiming an unfinished result:

1. What is this study trying to do?
2. Which LossSpec arm, candidate, and development seed is planned, running,
   complete, failed, or adopted?
3. How much work is logical registration versus a physical simulation?
4. Why are winner selection and held-out evaluation still locked?

The browser does not read simulator state, SQLite, prose status notes, metric
values, or loss reports. `utopia.optimization.mission_control` is the sole
projection boundary.

## Snapshot contract

The exporter reads the pinned campaign specs/snapshots/state files and opens
each registry with SQLite `mode=ro`. It copies the registry into memory before
selecting orchestration columns. Export is rejected if:

- the three arms do not share one clean source commit;
- a registry contains a protected/unknown seed;
- a candidate's 3-seed grid is incomplete;
- state and campaign snapshot revisions disagree;
- the state file changes during projection;
- a winner-freeze artifact or held-out registry already exists (v1 is an
  intentionally pre-freeze contract).

The portable bundle records the observation timestamp, source commit, source
file SHA-256 values, a canonical registry-projection hash, and a whole-bundle
SHA-256. The TypeScript reader recomputes the whole-bundle hash and repeats the
held-out firewall checks.

The verified fixture was captured at `2026-10-28T03:13:08.338710+00:00` from source
commit `1078279d1ce833afe9ffb6b7c262da15357b76ab`. It is a timestamped snapshot,
not a live feed. At that instant 27 of 45 possible logical development runs
were registered: 26 planned and 1 running. No winner was frozen and no
held-out registry existed. The screen must continue to say exactly that even
if the live experiment later advances.

## Claim boundary

- Candidate identifiers and run states are orchestration facts.
- `physical` means an actual attempt has started; `unmaterialized` is a
  logical row not yet executed; `adopted` means a logical row points to a
  separately verified physical artifact.
- The adapter omits objective values, metric values, observations, loss
  reports, and incumbent calculations.
- A running candidate is not a provisional winner.
- The held-out seeds are displayed only as locked identifiers.
- The separately served synthetic fixture invents mixed states solely for UI
  testing and carries `truth_status: synthetic` plus a visible disclosure.

## UX and accessibility

The NOCTILUCA city is organized as three rail yards (LossSpec arms), five
candidate towers per arm, and three seed windows per proposed tower. Empty
adaptive slots are visibly `NOT PROPOSED`; they are not rendered as pending
runs. Winner freeze and held-out evaluation occupy separate locked buildings.

Arm headings and candidate towers are native buttons. Keys `1`–`3` select an
arm and left/right arrows move through candidate slots when focus is outside a
control. Every colored seed window has a text alternative containing seed,
status, execution kind, and attempt. Layout collapses to one column on narrow
screens and respects reduced-motion preferences.

## Reproduction

```bash
/Users/shiro/unktok/dev/science-utopia-lab/.venv/bin/python \
  scripts/export_mission_control.py \
  --source-root /path/to/commit-pinned-study-worktree \
  --output game-ui-v2/public/data/optimization-mission.snapshot.json \
  --synthetic-output game-ui-v2/public/data/optimization-mission.synthetic.json

cd game-ui-v2
npm run typecheck
npm test
npm run build
```

For deterministic review, serve `game-ui-v2/dist`, open
`mission.html`, use a `1440×1050` viewport, disable animation, and capture the
full viewport after `SNAPSHOT HASH VERIFIED` appears.
