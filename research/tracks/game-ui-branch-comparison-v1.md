# Game UI branch comparison v1

Status: implemented and browser-verified on
`track/game-ui-branch-compare` from base `f6b60c0`.

## Evidence-producing slice

NOCTILUCA can now place two futures side by side from the same canonical replay
origin. A synchronized cursor drives both Phaser worlds. Each panel exposes its
own canonical intervention event, complete stream hash, authoritative final
projection, evidence inspector, and branch-local choreography.

The checked-in fixture forks after `review.completed`:

- Future A declares an `open-synthesis` intervention and fixture outcomes of
  `accept` and an Aya balance of `120`;
- Future B declares a `sealed-panel` intervention and fixture outcomes of
  `revise` and an Aya balance of `105`.

These values are deliberately conspicuous renderer-contract fixtures. They are
not simulation estimates, optimization results, causal effects, or evidence
for either institution.

## Canonical boundary

`intervention-branches.manifest.json` binds the comparison to:

1. the SHA-256 and final event ID of the common six-event canonical prefix;
2. the complete canonical stream hash of each branch replay;
3. one `policy.changed` intervention event ID that must exist in that branch.

The browser recomputes all three hashes before it displays the verified state.
It refuses a forged origin, branch stream, or intervention pointer. Outcome
labels come from the authoritative Python replay projection; the renderer does
not derive paper status or balances from pixel activity. Ambient rain and
couriers remain outside scientific claims.

## Interaction and visual design

The two 480x270 worlds retain the v3 fixed-grid pixel art, role sprites, packet
trains, dense cyberpunk districts, and evidence-linked actions. Mint and
magenta branch frames, a gold split spine, common-origin header, and locked
transport make the fork legible without turning the worlds into generic
dashboard cards. Clicking either intervention, a researcher action, or a flow
opens its branch-local canonical evidence.

## Verification

- Python replay tests: 11 passed for branch and replay-view v2 scope;
- Vitest: 15 passed;
- TypeScript typecheck and two-entry production build passed;
- `npm audit --audit-level=high`: zero vulnerabilities;
- 1440x1000 headless Chromium visual review passed;
- two cursor-43,000 captures were byte-identical, SHA-256
  `1998000843e58adb04b3be4d2bcfaf0c42dfaee9e89fd29925d9b03fa117a70a`.

## Next boundary

Replace the synthetic fixture input with branch manifests emitted by real
commit-pinned campaigns. That adapter must preserve the same three-hash gate
and must not call alternatives “counterfactual effects” unless the research
design supports that causal claim. A later campaign comparison can add
optimization objective and held-out metric panels without mixing those objects
into the replay renderer.
